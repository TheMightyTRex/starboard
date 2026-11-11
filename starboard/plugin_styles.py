"""Styles from plug-ins: colours and shape, never code (DASH-284).

A plug-in may offer styles in its manifest: for each, a light and a dark set of colours, a corner radius, a font
from Starboard's own list and a shadow. Starboard checks every style for accessibility before it can be added or
chosen (WCAG 2.2 contrast: 4.5:1 for text, 3:1 for borders and the focus ring, in both light and dark), and writes
the CSS itself from the checked values. A plug-in never sends CSS, fonts, pictures or scripts to the page.

What a style cannot change, whatever it says: the layout and the order of things, the text size, spacing,
underlined links, reduced motion and high contrast (the Display panel's choices always win over a style), the
size of buttons and other controls, and anything on another computer.
"""
import re

# The colours a style sets, and the CSS variable each fills (web/css/tokens.css).
TOKENS = {
    "bg": "--color-bg", "header": "--color-header", "surface": "--color-surface", "surface_raised": "--color-surface-raised",
    "surface_sunken": "--color-surface-sunken", "text": "--color-text", "text_muted": "--color-text-muted",
    "border": "--color-border", "divider": "--color-divider", "accent": "--color-accent", "accent_text": "--color-accent-text",
    "accent_soft": "--color-accent-soft", "focus": "--color-focus",
}
# Fonts: only what is already on the person's device or shipped with Starboard; nothing is downloaded.
FONTS = {
    "hyperlegible": '"Atkinson Hyperlegible Next", system-ui, sans-serif',
    "system": 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
    "rounded": 'ui-rounded, "SF Pro Rounded", "Nunito", system-ui, sans-serif',
    "serif": 'ui-serif, Georgia, "Iowan Old Style", serif',
    "mono": 'ui-monospace, "SF Mono", "Cascadia Code", Menlo, monospace',
}
SHADOWS = {"none": "none", "soft": "0 6px 24px rgb(16 24 40 / 0.12)", "strong": "4px 4px 0 var(--color-text)",
           # 11 November 2026: a layered lift, and a soft glow in the accent colour
           "layered": "0 1px 2px rgb(16 24 40 / 0.06), 0 4px 8px rgb(16 24 40 / 0.06), 0 12px 32px rgb(16 24 40 / 0.10)",
           "glow": "0 0 0 1px color-mix(in srgb, var(--color-accent) 25%, transparent), 0 8px 28px color-mix(in srgb, var(--color-accent) 22%, transparent)"}
# Optional colours a style may also set (11 November 2026), each into the design system's own variable. A style that
# leaves one out keeps Starboard's.
EXTRA = {
    "rail": "--color-rail", "panel_header": "--color-panel-header", "slide_header": "--color-slide-header",
    "control_active": "--color-control-active", "count": "--color-count", "count_text": "--color-count-text",
    "logo_tile": "--color-logo-tile", "logo_star": "--color-logo-star", "scrollbar": "--color-scrollbar",
    "success_fg": "--status-success-fg", "success_bg": "--status-success-bg", "warning_fg": "--status-warning-fg",
    "warning_bg": "--status-warning-bg", "danger_fg": "--status-danger-fg", "danger_bg": "--status-danger-bg",
    "info_fg": "--status-info-fg", "info_bg": "--status-info-bg",
    "chart_1": "--chart-1", "chart_2": "--chart-2", **{f"series_{n}": f"--series-{n}" for n in range(1, 8)},
}
# Their pairs, checked only when the style sets the colours in them (or a base colour stands in).
EXTRA_PAIRS = [
    ("text", ("rail",), 4.5, "the side menu's words"),
    ("text", ("panel_header", "slide_header"), 4.5, "headings in panels"),
    ("accent", ("control_active",), 4.5, "the chosen button in a group"),
    ("count_text", ("count",), 4.5, "the number on a count badge"),
    ("logo_tile", ("header", "rail"), 3.0, "the logo"), ("logo_star", ("header", "rail"), 3.0, "the logo's star"),
    ("scrollbar", ("bg",), 3.0, "scroll bars"),
    ("success_fg", ("success_bg",), 4.5, "success messages"), ("warning_fg", ("warning_bg",), 4.5, "warnings"),
    ("danger_fg", ("danger_bg",), 4.5, "problems"), ("info_fg", ("info_bg",), 4.5, "information"),
    *[(f"chart_{n}", ("surface",), 3.0, "chart lines and bars") for n in (1, 2)],
    *[(f"series_{n}", ("surface",), 3.0, "chart series") for n in range(1, 8)],
]
HEADING_WEIGHTS = (600, 700, 800)
# The page behind the panels (11 November 2026). Each mode may set bg_to (a second page colour) and glow_1, glow_2
# (soft lights for "mesh"); all are checked with the page's text.
GRADIENTS = ("none", "linear", "radial", "mesh")
TEXTURES = {  # drawn by CSS from the text colour at 5%, nothing downloaded
    "none": None,
    "dots": "radial-gradient({c} 1px, transparent 1.4px) 0 0 / 18px 18px",
    "grid": "linear-gradient({c} 1px, transparent 1px) 0 0 / 28px 28px, linear-gradient(90deg, {c} 1px, transparent 1px) 0 0 / 28px 28px",
    "lines": "repeating-linear-gradient(135deg, {c} 0 1px, transparent 1px 9px)",
    "grain": "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.06'/%3E%3C/svg%3E\")",
}
GLASS_OPACITY = 0.74  # panels let 26% of the page through
# The parts that turn to glass: the header, the side menu, panels, slide-outs, menus and messages.
GLASS_PARTS = ".site-header, .rail, .panel, .side-panel, .phone-menu, .menu, .toast, .app-card, .notice"
# Rounded controls: buttons, fields, choices and chips become pills.
PILL_PARTS = ".btn, .input, .select, .textarea, .chip, .filter-chip, .segmented, .search-field .input"
PAGE_COLOURS = {"bg_to", "glow_1", "glow_2"}


def _mix(a, b, t):
    """a with t of b mixed in (both #rrggbb)."""
    x = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    y = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(p + (q - p) * t):02x}" for p, q in zip(x, y))
MAX_RADIUS = 24
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

# (foreground, backgrounds, ratio needed, why): the pairs Starboard draws, checked in both light and dark.
PAIRS = [
    ("text", ("bg", "header", "surface", "surface_raised", "surface_sunken", "accent_soft"), 4.5, "text"),
    ("text_muted", ("bg", "surface", "surface_raised"), 4.5, "secondary text"),
    ("accent", ("bg", "surface", "surface_raised"), 4.5, "links and selected items"),
    ("accent_text", ("accent",), 4.5, "text on main buttons"),
    ("border", ("bg", "surface", "surface_raised"), 3.0, "the edges of fields and buttons"),
    ("focus", ("bg", "surface", "surface_raised"), 3.0, "the focus ring"),
]


def _lum(hex_colour):
    r, g, b = (int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5))
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    """The WCAG contrast ratio of two opaque colours, such as 4.62."""
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def check_style(style, where="style"):
    """Every problem with one style: [{severity, where, what, fix}]. Accessibility problems are errors, so a style
    that fails can never be added or chosen."""
    out = []

    def add(severity, what, fix, at=where):
        out.append({"severity": severity, "where": at, "what": what, "fix": fix})

    if not isinstance(style, dict):
        return [{"severity": "error", "where": where, "what": "A style must be an object", "fix": "See the manifest reference"}]
    allowed = {"id", "name", "description", "light", "dark", "radius", "font", "shadow", "heading_font", "heading_weight", "focus_width",
               "gradient", "gradient_angle", "texture", "glass", "rounded_controls"}
    if style.get("gradient", "none") not in GRADIENTS:
        add("error", f"gradient must be one of {', '.join(GRADIENTS)}", "Pick a gradient from the list")
    ang = style.get("gradient_angle", 160)
    if not isinstance(ang, int) or isinstance(ang, bool) or not 0 <= ang <= 360:
        add("error", "gradient_angle must be a whole number from 0 to 360", "Degrees, as in CSS")
    if style.get("texture", "none") not in TEXTURES:
        add("error", f"texture must be one of {', '.join(TEXTURES)}", "Textures are drawn by Starboard, never downloaded")
    for flag in ("glass", "rounded_controls"):
        if flag in style and not isinstance(style[flag], bool):
            add("error", f"{flag} must be true or false", "Leave it out for no")
    for k in sorted(set(style) - allowed):
        add("error", f"Unknown field {k}", "Styles may set colours, radius, fonts, heading weight, focus ring width and shadow")
    if style.get("heading_font") is not None and style["heading_font"] not in FONTS:
        add("error", f"heading_font must be one of {', '.join(FONTS)}", "Starboard never downloads a font")
    elif style.get("heading_font") == "mono":
        add("warning", "Monospace headings are harder to read", "Use it for a retro look only")
    if style.get("heading_weight") is not None and style["heading_weight"] not in HEADING_WEIGHTS:
        add("error", "heading_weight must be 600, 700 or 800", "Lighter headings do not stand out from the text")
    fw = style.get("focus_width")
    if fw is not None and (not isinstance(fw, int) or isinstance(fw, bool) or not 3 <= fw <= 5):
        add("error", "focus_width must be 3, 4 or 5 (pixels)", "A thinner focus ring is hard to see (WCAG 2.2 focus appearance)")
    if not re.match(r"^[a-z0-9][a-z0-9-]{1,30}$", str(style.get("id", ""))):
        add("error", "id must be 2 to 31 lower case letters, numbers and hyphens", "Give the style a short id such as midnight")
    if not (isinstance(style.get("name"), str) and 0 < len(style["name"]) <= 30):
        add("error", "name must be text of up to 30 characters", "Name it as people will see it in Display")
    if style.get("description") is not None and not (isinstance(style["description"], str) and len(style["description"]) <= 120):
        add("error", "description must be up to 120 characters", "Keep it to one short sentence")
    radius = style.get("radius", 0)
    if not isinstance(radius, int) or isinstance(radius, bool) or not 0 <= radius <= MAX_RADIUS:
        add("error", f"radius must be a whole number from 0 to {MAX_RADIUS}", "Larger corners clip focus rings and text")
    if style.get("font", "hyperlegible") not in FONTS:
        add("error", f"font must be one of {', '.join(FONTS)}", "Starboard never downloads a font")
    elif style.get("font") == "mono":
        add("warning", "A monospace font is harder to read in long text", "Use it for a retro look only; people can still choose bigger text")
    if style.get("shadow", "none") not in SHADOWS:
        add("error", f"shadow must be one of {', '.join(SHADOWS)}", "Pick a shadow from the list")
    for mode in ("light", "dark"):
        colours = style.get(mode)
        at = f"{where}.{mode}"
        if not isinstance(colours, dict):
            add("error", f"No {mode} colours", "Every style has a light and a dark set, so it follows the person's choice", at)
            continue
        for k in sorted(set(colours) - set(TOKENS) - set(EXTRA) - PAGE_COLOURS):
            add("error", f"Unknown colour {k}", f"Colours are: {', '.join(list(TOKENS) + list(EXTRA) + sorted(PAGE_COLOURS))}", at)
        missing = [k for k in TOKENS if k not in colours]
        if missing:
            add("error", f"Missing colours: {', '.join(missing)}", "Set every colour, so nothing falls back to a clash", at)
        bad = [k for k in list(TOKENS) + list(EXTRA) + sorted(PAGE_COLOURS) if k in colours and not (isinstance(colours[k], str) and HEX.match(colours[k]))]
        if bad:
            add("error", f"Not a solid colour: {', '.join(bad)}", "Use #rrggbb. See-through colours change contrast with whatever is behind them", at)
        if missing or bad:
            continue
        for fg, backs, need, why in PAIRS:
            for bk in backs:
                ratio = contrast(colours[fg], colours[bk])
                if ratio < need:
                    add("error", f"{fg} on {bk} is {ratio:.2f}:1; {why} need {need:g}:1 (WCAG 2.2)",
                        f"Make {fg} {'darker' if mode == 'light' else 'lighter'} or {bk} {'lighter' if mode == 'light' else 'darker'}", at)
        # The optional colours: a pair is checked when the style sets one of its colours; the other side falls back
        # to the base colour that stands in for it (the side menu to the header, a panel header to the raised surface).
        stand_in = {"rail": "header", "panel_header": "surface_raised", "slide_header": "bg", "control_active": "surface"}
        for fg, backs, need, why in EXTRA_PAIRS:
            for bk in backs:
                if not any(k in EXTRA and k in colours for k in (fg, bk)):
                    continue  # neither optional colour is set: Starboard's own pair, already checked
                a, b = colours.get(fg) or colours.get(stand_in.get(fg, "")), colours.get(bk) or colours.get(stand_in.get(bk, ""))
                if not (a and b):
                    add("error", f"{fg} and {bk} must be set together", f"Set both, so {why} can be checked", at)
                    continue
                ratio = contrast(a, b)
                if ratio < need:
                    add("error", f"{fg} on {bk} is {ratio:.2f}:1; {why} need {need:g}:1 (WCAG 2.2)",
                        f"Make {fg} {'darker' if mode == 'light' else 'lighter'} or {bk} {'lighter' if mode == 'light' else 'darker'}", at)
        # Every colour the page can show behind text: the page, the gradient's other end, the glows, and the texture's
        # lines over each (the text colour at 5%).
        g = style.get("gradient", "none")
        need_page = {"linear": ["bg_to"], "radial": ["bg_to"], "mesh": ["glow_1", "glow_2"]}.get(g, [])
        for k in need_page:
            if k not in colours:
                add("error", f"A {g} gradient needs {k}", f"Set {k} in the {mode} colours", at)
        page = [colours["bg"]] + [colours[k] for k in need_page if k in colours]
        if style.get("texture", "none") != "none":
            page += [_mix(p, colours["text"], 0.05) for p in page]
        for p in page[1:]:
            for fg, need, why in (("text", 4.5, "text on the page"), ("text_muted", 4.5, "secondary text on the page"),
                                  ("accent", 4.5, "links on the page")):
                ratio = contrast(colours[fg], p)
                if ratio < need:
                    add("error", f"{fg} on the page's {p} is {ratio:.2f}:1; {why} needs {need:g}:1 (WCAG 2.2)",
                        "Keep the gradient and its glows close to the page colour", at)
        if style.get("glass"):  # a glass panel over each page colour behind it
            for base in ("surface_raised", "header", "surface"):
                for p in page:
                    seen = _mix(colours[base], p, 1 - GLASS_OPACITY)
                    for fg in ("text", "text_muted", "accent"):
                        ratio = contrast(colours[fg], seen)
                        if ratio < 4.5:
                            add("error", f"{fg} on glass ({base} over {p}) is {ratio:.2f}:1; needs 4.5:1 (WCAG 2.2)",
                                "Bring the page colours nearer the panels, or leave glass out", at)
        if mode == "light" and _lum(colours["bg"]) < 0.4:
            add("warning", "The light background is dark", "People who choose Light expect a light page", at)
        if mode == "dark" and _lum(colours["bg"]) > 0.1:
            add("warning", "The dark background is light", "People who choose Dark expect a dark page", at)
    return out


def css(plugin_id, styles):
    """The CSS for a plug-in's checked styles. Only checked values reach it, so nothing can break out of a rule.
    High contrast (the Display panel) always wins: the rules leave out :root.pref-contrast."""
    rules = []
    for s in styles:
        if any(i["severity"] == "error" for i in check_style(s)):
            continue
        name = f"{plugin_id}.{s['id']}"
        shape = [f"--radius: {int(s.get('radius', 0))}px", f"--font: {FONTS[s.get('font', 'hyperlegible')]}",
                 f"--shadow-raised: {SHADOWS[s.get('shadow', 'none')]}"]
        if s.get("heading_font"):
            shape.append(f"--font-heading: {FONTS[s['heading_font']]}")
        if s.get("heading_weight"):
            shape.append(f"--weight-heading: {int(s['heading_weight'])}")
        if s.get("focus_width"):
            shape.append(f"--focus-w: {int(s['focus_width'])}px")
        root = f':root[data-style="{name}"]'
        for mode, sel in (("light", ":not(.is-dark)"), ("dark", ".is-dark")):
            c = s[mode]
            layers = []
            tex = TEXTURES.get(s.get("texture", "none"))
            if tex:
                layers.append(tex.format(c="color-mix(in srgb, var(--color-text) 5%, transparent)"))
            g, ang = s.get("gradient", "none"), int(s.get("gradient_angle", 160))
            if g == "linear":
                layers.append(f"linear-gradient({ang}deg, {c['bg']} 0%, {c['bg_to']} 100%)")
            elif g == "radial":
                layers.append(f"radial-gradient(130% 130% at 0% 0%, {c['bg_to']} 0%, {c['bg']} 65%)")
            elif g == "mesh":
                layers += [f"radial-gradient(55% 45% at 12% 8%, {c['glow_1']} 0%, transparent 72%)",
                           f"radial-gradient(50% 45% at 88% 92%, {c['glow_2']} 0%, transparent 72%)"]
            if layers:
                rules.append(f'{root}{sel}:not(.pref-contrast) body {{ background: {", ".join(layers)}, {c["bg"]}; background-attachment: fixed; }}')
        if s.get("glass"):
            rules.append(f"{root}:not(.pref-contrast) :is({GLASS_PARTS}) {{ background-color: color-mix(in srgb, var(--color-surface-raised) {round(GLASS_OPACITY * 100)}%, transparent); "
                         "-webkit-backdrop-filter: blur(18px) saturate(1.4); backdrop-filter: blur(18px) saturate(1.4); }")
            rules.append(f"@media (prefers-reduced-transparency: reduce) {{ {root} :is({GLASS_PARTS}) {{ background-color: var(--color-surface-raised); "
                         "-webkit-backdrop-filter: none; backdrop-filter: none; } }")
        if s.get("rounded_controls"):
            rules.append(f"{root}:not(.pref-contrast) :is({PILL_PARTS}) {{ border-radius: 999px; }}")
        for mode, sel in (("light", ":not(.is-dark)"), ("dark", ".is-dark")):
            colours = [f"{TOKENS[k]}: {s[mode][k]}" for k in TOKENS]
            if "panel_header" not in s[mode]:
                colours.append(f"--color-panel-header: {s[mode]['surface_raised']}")
            colours += [f"{EXTRA[k]}: {s[mode][k]}" for k in EXTRA if k in s[mode]]
            rules.append(f':root[data-style="{name}"]{sel}:not(.pref-contrast) {{ {"; ".join(colours + shape)}; }}')
    return "\n".join(rules) + ("\n" if rules else "")
