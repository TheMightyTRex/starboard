[Help centre](../README.md) · Before you install · how-to

# Install Docker

Install Docker, the program that runs Starboard in its own sealed box, by copying a few commands into the terminal.
At the end, `docker compose version` prints a version number and you are ready to install Starboard.

## Before you begin

- A Linux computer: Ubuntu, Linux Mint, Debian, Fedora or Raspberry Pi OS. Read
  [What you need to run Starboard](what-you-need.md).
- The password you use to sign in to that computer. The terminal asks for it.
- A terminal open on that computer. Read [The terminal: typing commands](../basics/the-terminal.md).
- Not sure what Docker is? Read [What Docker is](../basics/what-is-docker.md).

## Steps for Ubuntu, Debian, Fedora and Raspberry Pi OS

1. Download and run Docker's own install script. It asks for your password and takes a few minutes:

   ```bash
   curl -fsSL https://get.docker.com | sh
   ```

2. Let your user run Docker without typing `sudo` every time:

   ```bash
   sudo usermod -aG docker $USER
   ```

3. **Fedora only:** start Docker now and every time the computer starts:

   ```bash
   sudo systemctl enable --now docker
   ```

4. Sign out of the computer and sign back in. On a computer you reach over SSH (secure shell), close the
   connection and connect again. This is what makes Step 2 take effect.
5. Open a terminal again and check that Docker works:

   ```bash
   docker compose version
   ```

   It prints a line such as "Docker Compose version" and a number. Docker is ready.

## Steps for Linux Mint

Docker's install script does not support Linux Mint, so install Docker from Mint's own software instead.

1. Install Docker and Docker Compose. It asks for your password:

   ```bash
   sudo apt install docker.io docker-compose-v2
   ```

   When it asks "Do you want to continue?", type `y` and press Enter.

2. Let your user run Docker without typing `sudo` every time:

   ```bash
   sudo usermod -aG docker $USER
   ```

3. Sign out of the computer and sign back in.
4. Open a terminal again and check that Docker works:

   ```bash
   docker compose version
   ```

   It prints a line such as "Docker Compose version" and a number. Docker is ready.

## Things to note

- Adding your user to the `docker` group gives it full control of Docker, which is the same as administrator control
  of the computer. Only do this for your own user account.
- You only install Docker once. Updates to Docker come with the computer's normal software updates.

## If it does not work

- **"curl: command not found":** the computer does not have curl, the tool that downloads the script. Install it,
  then run Step 1 again. On Ubuntu, Debian and Raspberry Pi OS:

  ```bash
  sudo apt install curl
  ```

  On Fedora:

  ```bash
  sudo dnf install curl
  ```

- **"permission denied" when you run a docker command:** you have not signed out and back in since Step 2. Sign out,
  sign in, and try again. If it still happens, restart the computer.
- **"docker: 'compose' is not a docker command":** the Compose part of Docker is missing. On Linux Mint, run the
  install command in Step 1 again. On the others, run Docker's install script again.
- **On Linux Mint, "Unable to locate package docker-compose-v2":** your copy of Mint is probably an older version.
  Update Mint to the newest version, then try again.

## Find out more

- [Install Starboard with the installer](install-with-the-installer.md)
- [Install Starboard from the ready-made image](install-from-the-ready-made-image.md)
- [Install Starboard on a Linux computer](../guides/install-on-a-linux-computer.md)
- [What Docker is](../basics/what-is-docker.md)
