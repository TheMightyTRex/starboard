[Help centre](../README.md) · Install and update · how-to

# Set up Starboard in the terminal, with no browser

For a server with no desktop, and no phone or other computer to finish on. The installer asks every set-up question
in the terminal instead of the browser: your password, the apps for your media server and your download hours. It
takes about 10 minutes, plus the time to download the apps.

## Before you begin

- Everything in [Install Starboard with the installer](install-with-the-installer.md), up to the step that starts
  the installer.
- For the apps to start by themselves, answer yes to the installer's question about Docker access. Otherwise the
  terminal shows one command to start them.
- If you want a VPN: your VPN provider's details for WireGuard or OpenVPN, from the provider's website.

## Steps

1. In the Starboard folder, start the installer with `--terminal`:

   ```bash
   ./install.sh --terminal
   ```

2. Answer the installer's usual questions. When Starboard is running, the set-up questions follow in the same
   terminal.
3. Choose a password, at least 10 characters, and type it again. Nothing shows as you type. You do not need the setup
   code: you are on the server itself.
4. Choose what you want, such as Movies, TV and Watching, by typing their numbers separated by commas. Press Enter to
   take the recommended ones.
5. Check the apps it lists, then type the media folder and the settings folder, or press Enter to take the ones shown.
6. If you chose VPN, choose your provider and type its details. The password or key does not show as you type.
7. Read the list of what will change, then type `y` to write the apps' files and start them. Downloading them can
   take several minutes.
8. Choose when downloads run. Set hours are recommended, because downloading slows the internet for everyone else.
9. When it finishes, it prints the addresses to open Starboard from any device later.

## How to answer

- Type a number and press Enter. Press Enter on its own to take the answer in the brackets, which is the recommended
  one.
- Type `b` and press Enter to go back a step. Your last answers are in the brackets, so Enter keeps each one. A
  password or key you typed before is kept too, if you press Enter. Once the apps are written, you cannot go back
  past the check: change them later in **Settings**, **Install apps**.
- Type `?` and press Enter for help with any question. Help opens in a box over the step. Press Enter to close it.
- Type `q` and press Enter to stop. Nothing else changes, and you can finish in a browser later.
- Each step starts on an empty terminal window. The keys you can use are always on the bottom line.
- Headings have a border and a bar that shows how far through you are. Recommended answers are marked with a dot
  and say "recommended" too, so nothing depends on colour.
- If you use software that reads text aloud, such as Orca, start it with `STARBOARD_PLAIN=1 ./install.sh --terminal`.
  It then prints plain lines with no borders or colour, and never empties the window or draws over it. It does the
  same by itself in a window narrower than 60 characters or shorter than 20 lines.

## Things to note

- To run the set-up questions again later, go to the Starboard folder and run
  `python3 -m starboard.terminal_setup --port 8095`. It asks for your password first.
- Your answers are checked by Starboard exactly as the browser checks them, and saved in the same place.
- VPN details are saved in `data/stack/.env`, which only you can read.
- Starboard's help suggests some VPN providers. Some of them have affiliate links: if you sign up through one, the
  provider pays a small amount towards Starboard's development, at no extra cost to you.

## If it does not work

- **"Stopped: --terminal needs a terminal to type in":** the installer was not started in a terminal, for example
  from a script. Run it in a terminal, or leave out `--terminal` and finish in a browser.
- **"Starboard said: ..."**: Starboard refused an answer and says why. Type the answer again.
- **"Starboard cannot start apps itself":** Starboard has no Docker access. Run the command it shows, or run
  `./install.sh` again and answer yes to Docker access.
- **"The apps did not all start":** the lines below it are Docker's own. Read [An app is not responding](app-not-responding.md).

## Find out more

- [Install Starboard with the installer](install-with-the-installer.md)
- [Create your password and sign in](create-your-password.md)
- [Connect to your server with SSH](connect-with-ssh.md)
- [The terminal: typing commands](../basics/the-terminal.md)
