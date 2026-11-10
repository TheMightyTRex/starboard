[Help centre](../README.md) · The basics

# What a plug-in can change

A plug-in adds something to Starboard without changing Starboard itself. Think of Starboard as a building and a
plug-in as a tenant. A tenant can decorate their own flat and use the shared front door, but cannot move walls,
open other people's post or change the locks. Starboard is the landlord who checks each tenant before they move
in, and can ask them to leave at any time.

## What a plug-in can do

A plug-in can only do what it says in its manifest, and only after you have read the list and agreed. Starboard
shows each permission in plain words with a risk level (low, medium or high) before you add it.

- **Add styles to Display.** Colours, corner shapes, shadows and a font from those already on your device. Starboard
  writes the styles itself from the plug-in's colours, after checking them. You choose a style in **Display**.
- **Run its own small apps, called containers.** Each one is limited to its own folder, a set amount of memory and
  processor, and its own network.
- **Read from Starboard, if you allow it.** Your apps and whether they answer, what is downloading, your films,
  series and books, or processor, memory and disks. It uses its own key, which only reads, and stops working when
  the plug-in is removed.
- **Reach your home network or run inside your VPN,** only when it asks for this and you agree.
- **Show settings and buttons** in its own section of **Settings**, then **Plug-ins**, drawn by Starboard.
- **Add cards to the dashboard** that show a number, a short list or a status. You choose to add them with
  **Edit dashboard**. Starboard asks the plug-in at most once a minute and shows its answer as plain text. Read
  [Use and change the dashboard](../topics/use-the-dashboard.md#add-a-plug-ins-card).

## What a plug-in can never do

These are refused whatever a plug-in asks for. Starboard does not offer them, so no plug-in can be given them.

- **Add code to Starboard's pages.** A plug-in sends data, never scripts or CSS. Starboard draws everything on the page.
- **Change how Starboard works for you:** the layout and order of pages, the size of buttons, text size, spacing,
  underlined links, reduced motion and **High contrast**. Your **Display** choices always win over a style.
- **Use a style that fails accessibility.** Every style is checked in light and dark: text needs a contrast of at
  least 4.5 to 1 with what is behind it, and edges and the focus ring 3 to 1, as WCAG 2.2 asks. A style that fails
  cannot be added or chosen.
- **Control Docker or the computer.** No plug-in gets the Docker socket, administrator rights, the computer's own
  network, its devices, or any folder but its own.
- **Read or change other apps' settings, keys or passwords,** or Starboard's own data and password.
- **Change your install, your VPN, your downloads or your accounts.** The keys plug-ins get today only read.
- **Download fonts, pictures or code from the internet** into Starboard's pages.
- **Stay if you do not want it.** **Deactivate** stops it, **Remove** takes it away and stops its key, and
  **Deactivate all plug-ins** stops every one at once. Read [Add a plug-in](../topics/add-a-plugin.md#things-to-note).

## How Starboard checks a plug-in

Before a plug-in is added, Starboard runs the same tester that plug-in makers use:

1. The manifest is checked against Starboard's rules. Anything unknown is refused, so a mistake cannot slip through.
2. Each permission is listed for you, with its risk level.
3. Accessibility is always tested: every style in light and dark, and the names, labels and hints you will read.
4. Containers must be pinned to an exact version, so what you approved is what runs.

A plug-in with errors cannot be added. Warnings and tips are shown so you can decide.

## Find out more

- [Write a plug-in](write-a-plugin.md)
- [Add a plug-in](../topics/add-a-plugin.md)
- [The plug-in collection](plugin-collection.md)
- [How Starboard keeps your server safe](how-starboard-keeps-you-safe.md)
- [What an API key is](what-is-an-api-key.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
