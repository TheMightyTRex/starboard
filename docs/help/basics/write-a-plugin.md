[Help centre](../README.md) · The basics

# Write a plug-in

A plug-in is a folder with one file Starboard reads, `starboard-plugin.json`, called the manifest. It says what the
plug-in is, what it adds and what it may do. You do not change Starboard's code, and Starboard draws everything a
person sees. What a plug-in can and cannot do is in [What a plug-in can change](what-plugins-can-change.md).

## What a plug-in can add

- **Styles** for **Display**: colours, corners, shadows and a font. No container needed.
- **Dashboard cards** that show a number, a short list or a status from your plug-in.
- **Settings and buttons** in its own section of **Settings**, then **Plug-ins**.
- **Containers**: small apps Starboard runs for it, each in its own locked-down space.

## The manifest

Every manifest has these fields:

```json
{
  "manifest_version": 1,
  "id": "hello-card",
  "name": "Hello card",
  "version": "0.1.0",
  "description": "Shows one number on your dashboard.",
  "author": "Your public name",
  "licence": "MIT",
  "homepage": "https://example.invalid/hello",
  "support_url": "https://example.invalid/hello/issues",
  "starboard_api": ">=1.0 <2.0",
  "permissions": ["apps:read"]
}
```

`id` uses lower case letters, numbers and hyphens. `permissions` lists what it may do; people read each one, with
its risk level, before they add it. The full list is in [What a plug-in can change](what-plugins-can-change.md).

## Styles

Add `"appearance:styles"` to `permissions` and a `styles` list. Each style has a light and a dark set of 13
colours, written as `#rrggbb`:

`bg`, `header`, `surface`, `surface_raised`, `surface_sunken`, `text`, `text_muted`, `border`, `divider`, `accent`,
`accent_text`, `accent_soft` and `focus`.

It can also set `radius` (0 to 24), `font` (`hyperlegible`, `system`, `rounded`, `serif` or `mono`) and `shadow`
(`none`, `soft` or `strong`). Starboard checks every style in light and dark before it can be added: text needs a
contrast of at least 4.5 to 1 with what is behind it, and borders and the focus ring 3 to 1 (WCAG 2.2). The Styles
plug-in in [The plug-in collection](plugin-collection.md) is a full example to copy.

## Dashboard cards

### What cards are for

A card puts one small piece of your plug-in on the dashboard, next to Starboard's own cards: how many titles it has,
the last few things it did, or whether it is working. People add your card with **Edit dashboard**, choose its
size and move it. Use a card for something worth seeing at a glance. Long lists, settings and anything people act
on belong in the plug-in's own section of **Settings**, then **Plug-ins**. Read
[Use and change the dashboard](../topics/use-the-dashboard.md) for how people add cards.

### A folder setting

A setting of type `folder` lets people choose a folder for your plug-in with Browse, as they do everywhere else in
Starboard. It needs plug-in API 1.3 (`"starboard_api": ">=1.3 <2.0"`) and a container that mounts the media folder,
`media:ro`, or one folder in it, `media/<folder>`. The folder is always inside what you mount, and your plug-in reads
it as it sees it, such as `/media/music`. Nothing outside the media folder can be chosen.

### The three kinds

| Kind | Shows | Use it for |
|---|---|---|
| `stat` | One number, with a label and a short note | A count, a size, a percentage, a time |
| `list` | Up to 10 rows, each a title, a detail and an optional link | The latest few items |
| `status` | OK, Warning or Problem, with one sentence | Whether something is working |

### How to write one

1. Add the card to the manifest. `path` is a page on your plug-in's first container that answers with JSON.
   `example` is what that page answers; the tester checks it.

   ```json
   "cards": [
     {"id": "count", "title": "Hello", "type": "stat", "path": "/card", "format": "number",
      "example": {"value": 42, "label": "hellos", "note": "3 today"}}
   ]
   ```

2. Make the path answer in the shape for its kind:

   - `stat`: `{"value": 42, "label": "hellos", "note": "3 today"}`. `value` is a number. `format` says how to show it:
     `number`, `bytes`, `percent`, `duration` (seconds) or `date` (seconds since 1970).
   - `list`: `{"items": [{"title": "Dune", "detail": "Added today", "link": "https://example.invalid/dune"}]}`.
   - `status`: `{"state": "ok", "text": "Up to date"}`. `state` is `ok`, `warning` or `problem`.

3. Test the plug-in. Read [Test your plug-in](#test-your-plug-in).

### What Starboard does with your answer

- It asks your path at most once a minute, and only while someone has a dashboard with your card open.
- It waits 3 seconds at most and reads 64 KB at most.
- It shows your text as text, never as HTML, and cuts it to length: labels 40 characters, notes 80, list titles 80,
  details 120 and status text 160.
- Links must start with `http://` or `https://`, and open in a new tab.
- If your page does not answer, or answers the wrong shape, the card says "No answer from" your plug-in.

## Test your plug-in

In **Settings**, then **Plug-ins**, under **Test a plug-in**, choose your `starboard-plugin.json` and select **Test it**.
On a computer with Starboard's files, run `python3 -m starboard.plugin_tester path/to/your-plugin`. Each issue says
where it is, what is wrong and how to fix it:

- **Errors** stop the plug-in being added.
- **Warnings** should be fixed.
- **Tips** are worth reading.

Accessibility is always tested. It covers every style in light and dark, the names, labels and hints people read,
and every card.

## Use AI to write a plug-in

An AI assistant, such as Claude, can write a plug-in for you if you give it the rules. Copy this into the assistant,
and change the first line to what you want:

```text
Write a Starboard plug-in that [say what it should do].
Rules:
- One file, starboard-plugin.json, with manifest_version 1, id, name, version, description, author, licence,
  homepage, support_url, starboard_api ">=1.0 <2.0" and permissions.
- Styles: permission "appearance:styles"; each style has id, name, description, radius 0 to 24,
  font (hyperlegible, system, rounded, serif or mono), shadow (none, soft or strong), and light and dark sets of
  bg, header, surface, surface_raised, surface_sunken, text, text_muted, border, divider, accent, accent_text,
  accent_soft and focus as #rrggbb.
- Contrast, in light and dark: text on bg, header, all three surfaces and accent_soft at least 4.5:1;
  text_muted and accent on bg and surfaces at least 4.5:1; accent_text on accent at least 4.5:1;
  border and focus on bg and surfaces at least 3:1. Show me each ratio.
- Cards: type stat, list or status, a path, and an example answer in the right shape.
- No CSS, HTML, scripts, fonts or pictures. Only the fields in this list.
```

Then test what it writes. Read [Test your plug-in](#test-your-plug-in). Fix each error, or paste the tester's issues back into the
assistant and ask it to fix them. Check the result yourself before you share it: the tester checks the rules, not
whether you like the colours.

## Share it

Put the folder somewhere people can reach, such as a Git repository, and give them the `https` address of its
`starboard-plugin.json`. To add a one-step installer like the Styles plug-in has, copy its `install.py`.

## Find out more

- [What a plug-in can change](what-plugins-can-change.md)
- [Add a plug-in](../topics/add-a-plugin.md)
- [The plug-in collection](plugin-collection.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
