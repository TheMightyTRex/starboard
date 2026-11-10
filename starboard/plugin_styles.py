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
SHADOWS = {"none": "none", "soft": "0 6px 24px rgb(16 24 40 / 0.12)", "strong": "4px 4px 0 var(--color-text)"}
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
    allowed = {"id", "name", "description", "light", "dark", "radius", "font", "shadow"}
    for k in sorted(set(style) - allowed):
        add("error", f"Unknown field {k}", "Styles may set only colours, radius, font and shadow")
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
        for k in sorted(set(colours) - set(TOKENS)):
            add("error", f"Unknown colour {k}", f"Colours are: {', '.join(TOKENS)}", at)
        missing = [k for k in TOKENS if k not in colours]
        if missing:
            add("error", f"Missing colours: {', '.join(missing)}", "Set every colour, so nothing falls back to a clash", at)
        bad = [k for k in TOKENS if k in colours and not (isinstance(colours[k], str) and HEX.match(colours[k]))]
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
        for mode, sel in (("light", ":not(.is-dark)"), ("dark", ".is-dark")):
            colours = [f"{TOKENS[k]}: {s[mode][k]}" for k in TOKENS] + [f"--color-panel-header: {s[mode]['surface_raised']}"]
            rules.append(f':root[data-style="{name}"]{sel}:not(.pref-contrast) {{ {"; ".join(colours + shape)}; }}')
    return "\n".join(rules) + ("\n" if rules else "")
