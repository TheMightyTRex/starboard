[Help centre](../README.md) · When something is wrong · reference

# Run first error numbers

When the Run first script stops, it shows an error number, such as `Error RF-11`, with a link to this page. Find
the number below to see what it means and how to put it right. Then run the script again: it carries on from what
is missing, and nothing that already worked is done twice.

If you ask for help or report a problem, give the error number. The script's log has it too: the message gives
where the log is, a file called `run-first.log` in a `starboard-run-first` folder in `/tmp`.

## Before it starts

### RF-01

**An option the script does not know.** The command has a word after `bash` that the script does not use, often a
typing mistake. Run it with no options, or with one of `--browser`, `--terminal`, `--plain`, `--yes`, `--dir` or
`--check`. To see what each does, run it with `--help`.

### RF-02

**No terminal to type in.** The script was started somewhere it cannot ask questions, such as from another
program or a scheduled job. Run it in a terminal window, or add `--yes` to accept every safe answer without being
asked.

### RF-03

**Run as root or with sudo.** Run it as your normal user, without `sudo` in front. It asks for your password
itself when it needs to install something.

### RF-04

**No temporary folder.** The script could not make a folder in `/tmp`. Usually the disk is full: free some
space, then run it again.

### RF-05

**A version of Linux the script does not know.** It knows Debian, Ubuntu, Linux Mint, Fedora and Raspberry Pi OS.
Install Docker by hand with [Install Docker](install-docker.md), then run the script again.

## Installing what is missing

These happen while the script installs Docker and the other things Starboard needs. Each time, the script offers
**Try again**, **Show the details** or **Stop**.

### RF-10

**curl is installed as a snap.** The snap version of curl is sandboxed and cannot save Docker's installer where
the script needs it. Choose **Stop**, then install the usual curl and run the script again:

```bash
sudo apt install curl
```

### RF-11

**No internet.** This computer could not reach the internet to download something. Check the network cable or
Wi-Fi, then choose **Try again**.

### RF-12

**Another program is installing updates.** This often happens just after Linux is installed, when it updates
itself. Wait a few minutes, then choose **Try again**.

### RF-13

**A software source has a signing key Linux no longer accepts.** The list of software could not be updated.
Choose **Show the details** to see which source. Install that source's new key, or turn the source off, then
choose **Try again**.

### RF-14

**The disk is full.** Free some space, then choose **Try again**.

### RF-15

**This version of Linux does not offer something the script installs.** Update Linux to its newest version, or
install Docker by hand with [Install Docker](install-docker.md).

### RF-16

**Your user is not allowed to install software.** Run the script as the user you made when installing Linux, or
ask whoever looks after this computer to add you to the `sudo` group.

### RF-17

**sudo did not accept the password.** Type the password you use to sign in to this computer. Nothing shows as
you type on most systems. Then choose **Try again**.

### RF-19

**Something else went wrong.** Choose **Try again**. If it happens again, choose **Show the details**, and give
the last lines when you ask for help.

### RF-20

**Still missing after installing.** The jobs finished, but Docker, or your permission to use it, is still not in
place. Run the script again. If it stops here again, restart the computer, then run it once more.

## Downloading Starboard

### RF-30

**A folder called starboard is in the way.** A `starboard` folder is already in your home folder, and it is not a
Starboard download. Move or rename it, or choose another folder with `--dir`, then run the script again.

### RF-31

**The Starboard folder cannot be opened.** It was downloaded but cannot be entered, usually because its
permissions were changed. Move it aside, then run the script again to download a fresh copy.

## Installing Starboard and starting the apps

### RF-40

**Starboard's installer stopped.** The installer says why on the lines just above the error number, often on a
line that starts with `Stopped`. Put that right, then run the script again.

If the line above says `sg: command not found`, your copy of the script is from before 7 November 2026. Run the
script again: the current one works without `sg`.

### RF-50

**The apps did not start.** The set-up in the browser asked this window to download and start your apps, and
that did not finish. The line just above the error number says why. Most often this computer could not reach the
internet, or the disk is full. Put that right, then select **Try again** in the browser.

## Find out more

- [Set up everything with the Run first script](run-first.md)
- [Install Docker](install-docker.md)
- [Read the log and report a problem](read-the-log.md)
- [Starboard does not open](starboard-does-not-open.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
