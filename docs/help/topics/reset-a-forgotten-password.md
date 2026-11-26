[Help centre](../README.md) · Security · how-to
<!-- help: use / security -->

# Reset a forgotten password

If you have forgotten Starboard's password, remove it on the server and choose a new one. Everyone is signed
out, and your apps and settings stay as they are.

## Before you begin

- You can enter commands on the server, at its keyboard or over SSH (secure shell). Read
  [The terminal: entering commands](../basics/the-terminal.md) and
  [Connect to your server from another computer](connect-with-ssh.md).
- You know how you installed Starboard: with the installer, or from the ready-made image. Follow the steps
  for your way.

## Steps

### If you used the installer

1. On the server, go to the folder you installed Starboard in. If you installed it in your home folder, this
   command takes you there:

   ```bash
   cd ~/starboard
   ```

2. Run the reset script. It removes the password, signs everyone out and restarts Starboard:

   ```bash
   ./reset-password.sh
   ```

   It ends with "The password is removed and everyone is signed out", then shows a new set-up code.
3. Open Starboard in your browser. It shows **Create your password**.
4. In **Set-up code**, enter the code the script showed.
5. In **Choose a password** and **Enter it again**, enter your new password. It must have at least 10
   characters.
6. Select **Save password and continue**.

### If you used the ready-made image

1. On the server, go to the folder that holds `compose.image.yaml`. For example:

   ```bash
   cd ~/starboard
   ```

2. Leave a file that asks Starboard to remove the password when it next starts:

   ```bash
   touch data/reset-password
   ```

3. Restart Starboard:

   ```bash
   docker restart starboard
   ```

4. Show Starboard's log, which holds the new set-up code:

   ```bash
   docker logs starboard
   ```

   Find the last line that says "Open the dashboard and enter this set-up code", and copy the code at its
   end.
5. Open Starboard in your browser and follow steps 3 to 6 of [If you used the installer](#if-you-used-the-installer).

## Things to note

- The two-step code and single sign-on are deactivated too, so you are not locked out by a lost phone. Set them up
  again afterwards in **Settings**, then **Security**, then **Sign-in methods**.
- Only the password and sign-ins change. Your apps, API keys, categories and settings stay as they are.
- The dashboard name is filled in for you on the **Create your password** page. Change it there if you want to.
- If you still know the password, [change your password](change-your-password.md) instead. If the two-step code or
  single sign-on is the problem, read [Get back in when sign-in is locked](get-back-in-when-sign-in-is-locked.md).

## If it does not work

- **"Stopped: no data folder here":** you are in the wrong folder. Go to the folder you installed Starboard
  in and run the script again.
- **"Stopped: Starboard did not restart":** Starboard did not start again within 30 seconds. Read its log
  with this command, from the same folder:

  ```bash
  docker compose logs starboard
  ```

  Then read [Starboard does not open](starboard-does-not-open.md).
- **"The set-up code is not right":** copy the code again, from the newest line of the log. An older code
  from before the reset no longer works.

## Find out more

- [Find the set-up code](find-the-setup-code.md)
- [Create your password and sign in](create-your-password.md)
- [Change your password](change-your-password.md)
- [What Docker is](../basics/what-is-docker.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
