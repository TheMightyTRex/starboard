[Help centre](../README.md) · The basics

# The terminal: typing commands

The terminal is a window where you type instructions to your computer instead of choosing them from menus. It
is like sending a written note to the computer rather than pointing at things: you write exactly what you want,
press Enter, and it does it.

Installing Starboard needs a few commands. You do not have to type them: you copy them from this help and paste
them in.

## Open a terminal

On most Linux computers, press **Ctrl**, **Alt** and **T** together. A window opens with a line of text that ends
in `$`. If that does not work, use the menu instead:

- **Ubuntu:** open **Show Apps**, type `terminal`, then select **Terminal**.
- **Linux Mint:** open the **Menu**, type `terminal`, then select **Terminal**.
- **Raspberry Pi OS with a desktop:** open the Raspberry menu, then **Accessories**, then **Terminal**.
- **Raspberry Pi OS Lite, with no desktop:** there is no window to open. When you sign in, you are already at the
  terminal.

If your server has no monitor, you can use its terminal from another computer. Read
[Connect to your server from another computer](../topics/connect-with-ssh.md).

## The prompt

The line that ends in `$` is the prompt. It means "ready, type a command". It usually shows your user name, the
computer's name and the folder you are in, like this:

```
sam@homeserver:~$
```

Here `sam` is the user, `homeserver` is the computer and `~` means your home folder.

## Copy and paste a command

1. In this help, select the copy button on the command, or highlight the command and press **Ctrl** and **C**.
2. In the terminal, press **Ctrl**, **Shift** and **V** together to paste it. In a terminal, **Ctrl** and **V** on
   its own does not paste.
3. Press **Enter** to run it.

You can also paste with the right mouse button: press it inside the terminal and choose **Paste**.

To copy text out of the terminal, highlight it and press **Ctrl**, **Shift** and **C**. Plain **Ctrl** and **C**
does something else in a terminal: it stops the command that is running.

## Capital letters matter

Linux treats capital and small letters as different: `Run-first.sh` and `run-first.sh` are two different files, and
`Docker` is not the `docker` command. Type commands, file names and folder names exactly as the help shows them, with
the same capitals, hyphens `-` and underscores `_`.

Web addresses are partly the same. The website's name, such as `github.com`, can be in any case, but the rest of the
address often cannot: in `https://raw.githubusercontent.com/TheMightyTRex/starboard/main/run-first.sh`, `main` and
`run-first.sh` must be in small letters. A wrong capital usually gives "404", which means "not found".

## Symbols that are in different places on different keyboards

Copying and pasting a command avoids this altogether. If you type a command, some symbols are not where the key
says, and they move between keyboards. These are the ones Starboard's commands use. **AltGr** is the key to the
right of the space bar.

| Symbol | Name | US | UK and Ireland | German | French | Spanish |
|---|---|---|---|---|---|---|
| `\|` | Vertical bar, or pipe | **Shift** and `\` (above or beside **Enter**) | **Shift** and `\` (the key between the left **Shift** and **Z**) | **AltGr** and `<` (the key between the left **Shift** and **Y**) | **AltGr** and **6** | **AltGr** and **1** |
| `~` | Tilde | **Shift** and the key to the left of **1** | **Shift** and `#` (the key to the left of **Enter**) | **AltGr** and `+` | **AltGr** and **2**, then **Space** | **AltGr** and **4** |
| `\` | Backslash | The key above or beside **Enter** | The key between the left **Shift** and **Z** | **AltGr** and `ß` | **AltGr** and **8** | **AltGr** and the key to the left of **1** |
| `"` | Double quote | **Shift** and `'` | **Shift** and **2** | **Shift** and **2** | The **3** key, without **Shift** | **Shift** and **2** |
| `@` | At sign | **Shift** and **2** | **Shift** and `'` (next to the `#` key) | **AltGr** and **Q** | **AltGr** and **0** | **AltGr** and **2** |
| `$` | Dollar | **Shift** and **4** | **Shift** and **4** | **Shift** and **4** | Its own key, to the left of **Enter** | **Shift** and **4** |
| `&` | Ampersand | **Shift** and **7** | **Shift** and **7** | **Shift** and **6** | The **1** key, without **Shift** | **Shift** and **6** |

Things to note:

- **On a UK keyboard,** the key to the left of **1** shows a broken bar `¦`. That is a different character, and a
  command with it in does not work. The vertical bar is **Shift** and the `\` key next to the left **Shift**.
- **When the symbol does not appear,** your computer may be set to a different keyboard from the one in front of
  you. Check the keyboard layout in the computer's settings, or copy and paste the command instead.
- **Over SSH,** the keyboard that counts is the one on the computer you are typing on, not the server's.

## When a command asks for your password

Commands that change the computer as a whole start with `sudo`, which means "do this as the administrator". The
first time, the terminal asks for your password:

```
[sudo] password for sam:
```

On Ubuntu 26.04, it looks like this instead:

```
[sudo: authenticate] Password:
```

Type the password you use to sign in to the computer, then press Enter. On most systems **nothing appears while
you type**, not even dots or stars. That is normal: the terminal hides it so nobody can count the letters. On
Ubuntu 26.04, a star appears for each letter instead. If you make a mistake, it says so ("Sorry, try again", or on
Ubuntu 26.04 "Authentication failed, try again") and asks once more.

For a few minutes after that, other `sudo` commands do not ask again.

## Folders and the cd command

The terminal always works inside one folder at a time, like being in one room of a house. When you open it, you
are in your home folder, shown as `~`.

`cd` means "change directory", which is another word for folder. This command moves you into the folder called
`starboard` inside the one you are in:

```bash
cd starboard
```

This one takes you back to your home folder from anywhere:

```bash
cd ~
```

Two more commands help you find your way. `pwd` shows which folder you are in, and `ls` lists what is in it.

Many Starboard commands, such as `./update.sh`, only work in the Starboard folder. If one says "No such file or
directory", you are probably in the wrong folder: run `cd ~/starboard` first.

## How to tell a command has finished

A command has finished when the prompt, ending in `$`, comes back on a new line. While a command is still
working, there is no prompt, and you may see progress messages scrolling past.

Some commands take a few minutes, especially ones that download things. Wait for the prompt before you run the
next command.

If a command seems stuck for a long time, press **Ctrl** and **C** to stop it. Then read the last few lines it
printed: they usually say what went wrong.

## Messages that look alarming

Commands often print a lot of text. Most of it is progress, and you can ignore it. What matters is the last few
lines. Words such as "Stopped", "error" or "permission denied" mean something went wrong, and the help for that
step says what to do.

## What this means for Starboard

You use the terminal to install Docker, install Starboard, find the setup code and, later, to update Starboard.
After that, you do almost everything in Starboard's own pages, in your browser.

## Find out more

- [Install Docker](../topics/install-docker.md)
- [Install Starboard with the installer](../topics/install-with-the-installer.md)
- [Connect to your server from another computer](../topics/connect-with-ssh.md)
- [What Docker is](what-is-docker.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
