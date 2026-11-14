"""A plug-in's logo (plug-in API 1.14, DASH-428): a small SVG or PNG file inside the plug-in, named in its manifest
as "logo": {"file": "logo.svg", "alt": "A play symbol on a screen"}. Starboard fetches it from beside the manifest
when the plug-in is added or updated (or reads it from the plug-in's folder for one built into Starboard), checks it,
keeps a cleaned copy in the plug-in's folder and serves that copy itself. A catalogue entry may carry the same logo
as a data address ("logo": "data:image/svg+xml;base64,...", "logo_alt"), cleaned the same way.

The checks, so a logo can never run anything or load anything from elsewhere:
  SVG  at most 16 KB, no DOCTYPE or entities, a viewBox, only drawing elements (no script, foreignObject, image,
       animation or style elements), no event handlers (on...), no links but to its own parts (#id), no url() but
       url(#id). Starboard draws it again from what it allows, so anything else is left out even if it slipped by.
  PNG  at most 32 KB, a real PNG, square, from 32 to 256 pixels a side.
A plug-in without a logo, or with one that fails, is drawn with its initials on a neutral tile instead.
"""
import base64
import hashlib
import re
import struct
import urllib.parse
import xml.etree.ElementTree as ET  # nosec B405: the text is refused before parsing if it has a DOCTYPE or entities

SVG_MAX, PNG_MAX = 16 * 1024, 32 * 1024
PNG_MIN_SIDE, PNG_MAX_SIDE = 32, 256
DATA_MAX = 24 * 1024  # a catalogue's data address, base64 included
FILE = r"^(?:[a-z0-9][a-z0-9_-]{0,29}/)?[A-Za-z0-9][A-Za-z0-9._-]{0,60}\.(svg|png)$"
ALT_MIN, ALT_MAX = 3, 80
SVG_NS = "http://www.w3.org/2000/svg"
XLINK = "http://www.w3.org/1999/xlink"
ELEMENTS = {"svg", "g", "path", "rect", "circle", "ellipse", "line", "polyline", "polygon", "title", "desc", "defs",
            "linearGradient", "radialGradient", "stop", "clipPath", "mask", "use", "symbol", "text", "tspan"}
REFUSED = {"script", "foreignObject", "image", "style", "animate", "animateTransform", "animateMotion", "set",
           "iframe", "a", "feImage", "handler", "listener"}
ATTRS = {"viewBox", "width", "height", "x", "y", "x1", "y1", "x2", "y2", "cx", "cy", "r", "rx", "ry", "d", "points",
         "fill", "fill-opacity", "fill-rule", "clip-rule", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin",
         "stroke-miterlimit", "stroke-dasharray", "stroke-dashoffset", "stroke-opacity", "opacity", "transform", "id",
         "offset", "stop-color", "stop-opacity", "gradientUnits", "gradientTransform", "spreadMethod", "fx", "fy",
         "clip-path", "mask", "maskUnits", "clipPathUnits", "preserveAspectRatio", "href", "font-size", "font-weight",
         "font-family", "text-anchor", "dominant-baseline", "color", "vector-effect", "paint-order", "role", "aria-hidden",
         "focusable", "version"}
URL_OK = re.compile(r"url\(\s*['\"]?#[A-Za-z0-9_-]{1,60}['\"]?\s*\)")


def check_entry(logo):
    """Problems with the manifest's logo field, as plain sentences."""
    if not isinstance(logo, dict) or set(logo) - {"file", "alt"}:
        return ["logo must be an object with file and alt, such as {\"file\": \"logo.svg\", \"alt\": \"A play symbol\"}"]
    out = []
    f = logo.get("file")
    if not (isinstance(f, str) and re.match(FILE, f)) or ".." in str(f):
        out.append("logo.file must be an .svg or .png file beside the manifest (or in one folder under it), such as logo.svg")
    alt = logo.get("alt")
    if not (isinstance(alt, str) and ALT_MIN <= len(alt.strip()) <= ALT_MAX):
        out.append(f"logo.alt must say what the logo shows, in {ALT_MIN} to {ALT_MAX} characters")
    return out


def _local(tag):
    return tag.split("}", 1)[1] if tag.startswith("{") else tag


def clean_svg(raw):
    """The SVG drawn again from what Starboard allows, as bytes; ValueError in plain words when it is refused."""
    if len(raw) > SVG_MAX:
        raise ValueError(f"The SVG logo is larger than {SVG_MAX // 1024} KB")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("The SVG logo is not UTF-8 text") from None
    if re.search(r"<!DOCTYPE|<!ENTITY", text, re.I):
        raise ValueError("The SVG logo has a DOCTYPE or entities, which Starboard does not accept")
    try:
        root = ET.fromstring(text)  # nosec B314: no DOCTYPE or entities, checked above
    except ET.ParseError as e:
        raise ValueError(f"The SVG logo is not well-formed: {e}") from None
    if _local(root.tag) != "svg":
        raise ValueError("The logo file is not an SVG")
    if not root.get("viewBox"):
        raise ValueError("The SVG logo needs a viewBox, so it scales to any size")
    problems = []

    def walk(node):
        name = _local(node.tag)
        if name in REFUSED or name not in ELEMENTS:
            problems.append(f"<{name}> is not allowed" + (" (scripts, pictures, styles and animation never are)" if name in REFUSED else ""))
            return None
        out = ET.Element(name)
        for k, v in node.attrib.items():
            key = _local(k)
            if key.lower().startswith("on"):
                problems.append(f"the event handler {key} is not allowed")
                continue
            if key == "style":
                problems.append("style attributes are not allowed; use fill and stroke")
                continue
            if key not in ATTRS:
                continue  # left out quietly: such as data-* or inkscape:*, which draw nothing
            if key == "href" and not re.match(r"^#[A-Za-z0-9_-]{1,60}$", v):
                problems.append(f"the link {v[:60]} goes outside the logo; only #id links to its own parts are allowed")
                continue
            if "url(" in v.lower() and URL_OK.sub("", v).lower().count("url(") > 0:
                problems.append("url() may point only to the logo's own parts, such as url(#shade)")
                continue
            if re.search(r"javascript:|data:|https?:", v, re.I):
                problems.append(f"{key} points outside the logo")
                continue
            out.set(key, v)
        out.text = node.text if name in ("title", "desc", "text", "tspan") else None
        out.tail = None
        for child in node:
            c = walk(child)
            if c is not None:
                out.append(c)
        return out

    clean = walk(root)
    if problems:
        raise ValueError("The SVG logo was refused: " + "; ".join(dict.fromkeys(problems)))
    clean.set("xmlns", SVG_NS)
    return ET.tostring(clean, encoding="utf-8", xml_declaration=False)


def check_png(raw):
    """The PNG as given, after its checks; ValueError in plain words when it is refused."""
    if len(raw) > PNG_MAX:
        raise ValueError(f"The PNG logo is larger than {PNG_MAX // 1024} KB")
    if raw[:8] != b"\x89PNG\r\n\x1a\n" or raw[12:16] != b"IHDR" or len(raw) < 33:
        raise ValueError("The logo file is not a PNG")
    w, h = struct.unpack(">II", raw[16:24])
    if w != h or not PNG_MIN_SIDE <= w <= PNG_MAX_SIDE:
        raise ValueError(f"The PNG logo must be square, from {PNG_MIN_SIDE} to {PNG_MAX_SIDE} pixels a side; this one is {w} by {h}")
    return raw


def clean(raw, name):
    """(bytes, content type) for a logo file called `name`, checked and cleaned."""
    if str(name).lower().endswith(".svg"):
        return clean_svg(raw), "image/svg+xml"
    if str(name).lower().endswith(".png"):
        return check_png(raw), "image/png"
    raise ValueError("A logo is an .svg or .png file")


def as_data(data, ctype):
    return f"data:{ctype};base64,{base64.b64encode(data).decode()}"


def from_data(uri):
    """A catalogue's data address checked and cleaned: a data address again, or None when it is unusable."""
    m = re.match(r"^data:(image/svg\+xml|image/png);base64,([A-Za-z0-9+/=]+)$", str(uri or ""))
    if not m or len(uri) > DATA_MAX:
        return None
    try:
        raw = base64.b64decode(m.group(2), validate=True)
        data, ctype = clean(raw, "logo.svg" if m.group(1) == "image/svg+xml" else "logo.png")
    except (ValueError, TypeError):
        return None
    return as_data(data, ctype)


def address_beside(manifest_url, file):
    """The logo's address: the file beside the manifest at `manifest_url` (never above it)."""
    if not re.match(FILE, str(file)) or ".." in str(file):
        raise ValueError("logo.file must be a file beside the manifest")
    return urllib.parse.urljoin(manifest_url, file)


def fetch(manifest_url, file, opener=None):
    """(bytes, content type) for a logo beside a manifest at an https address, checked like any outside address."""
    import urllib.request
    from . import outside
    url = address_beside(manifest_url, file)
    if not url.startswith("https://"):
        raise ValueError("The logo must be at an https address, beside the manifest")
    outside.check_url(url)
    req = urllib.request.Request(url, headers={"User-Agent": "Starboard", "Accept": "image/svg+xml, image/png"})
    with (opener or urllib.request.build_opener()).open(req, timeout=5) as r:  # checked above  # nosec B310
        raw = r.read(PNG_MAX + 1)
    return clean(raw, file)


def save(folder, data, ctype):
    """Keeps the cleaned logo in the plug-in's folder as logo.svg or logo.png (the other one is cleared)."""
    import os
    ext = "svg" if ctype == "image/svg+xml" else "png"
    for other in ("svg", "png"):
        p = os.path.join(folder, f"logo.{other}")
        if other != ext and os.path.exists(p):
            os.replace(p, p + ".old")
    path = os.path.join(folder, f"logo.{ext}")
    with open(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644), "wb") as f:
        f.write(data)
    return path


def kept(folder):
    """(path, content type, short hash) of the logo kept in a plug-in's folder, or None."""
    import os
    for ext, ctype in (("svg", "image/svg+xml"), ("png", "image/png")):
        p = os.path.join(folder, f"logo.{ext}")
        try:
            with open(p, "rb") as f:
                data = f.read(PNG_MAX + 1)
        except OSError:
            continue
        return p, ctype, hashlib.sha256(data).hexdigest()[:12]
    return None


def initials(name):
    """The fallback: up to two letters from the name, such as DP for Direct play."""
    words = [w for w in re.split(r"[^A-Za-z0-9]+", str(name or "")) if w]
    if not words:
        return "?"
    return (words[0][0] + (words[1][0] if len(words) > 1 else words[0][1:2])).upper()
