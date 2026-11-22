# Ad blocking: Problems
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Find what is wrong with Ad blocking from what its tab or its card says, then follow the numbered answer.

```flow
title: Find your answer
start: Ad blocking is not working as it should
q: What does its tab say?
  Failed or Not answering -> 1
  Not supported -> 2
  Active, but the card is wrong -> q2
q2: What does the card say?
  Needs setting up -> 3
  No answer from Ad blocking -> 4
  Protected, but 0 blocked -> 5
1: Start it again #start-it-again
2: Update it or update Starboard #update-it-or-update-starboard
3: Add the address #add-the-address
4: Check the address and password #check-the-address-and-password
5: Check what is counted #check-what-is-counted
```

## Start it again

1. On Ad blocking's tab, read the message under its state: it says why it stopped.
2. Select **Try again**.
3. If it stopped soon after an update, select **Roll back to** and the version you had. Read [Updates](../dns-blocking/updates.md).
4. Still failing: go to **System**, then **Logs**, and find its name.

## Update it or update Starboard

Your Starboard's plug-in API is outside what this version of Ad blocking works with, so Starboard stopped it.

1. Select **Check for an update** on its tab.
2. If there is none, update Starboard. Read [Update Starboard](../../topics/update-starboard.md).

## Add the address

The card says "Add the address in the plug-in's settings": **Its address** is empty.

1. Go to **Settings**, then **Plug-ins**, then **Ad blocking**.
2. Enter **Its address** and **Password**, and for AdGuard Home the **User name**.
3. Select **Save**.
4. Wait a minute for the card to ask again.

## Check the address and password

Ad blocking asked Pi-hole or AdGuard Home and got no numbers back, or did not answer Starboard within 3 seconds.

1. Open the address in **Its address** in your browser. If it does not open, Pi-hole or AdGuard Home is not running at that address.
2. Check **Which one** matches what you run.
3. Enter the password again and select **Save**. A saved password is never shown, so entering it again is the only way to be sure.
4. For Pi-hole, check it is Pi-hole 6. Ad blocking uses the way Pi-hole 6 answers, and an older Pi-hole gives it no numbers.
5. For AdGuard Home, check **User name**, and that the address includes its port, such as `http://192.0.2.2:3000`.
6. Wait a minute for the card to ask again.

## Check what is counted

The card shows 0 blocked with "no lookups yet": Pi-hole or AdGuard Home answered, but has counted no lookups today.

- Check your router or your devices use Pi-hole or AdGuard Home for their lookups (DNS). If none does, there is nothing to count.
- Open Pi-hole or AdGuard Home itself and compare its own count for today.

## Report a problem

If none of these helps, tell its maker, with what its tab and the card say: [the plug-ins' issues on GitHub](https://github.com/TheMightyTRex/starboard-plugins/issues).

## Find out more

- [Settings](../dns-blocking/settings.md)
- [Updates](../dns-blocking/updates.md)
- [If a plug-in will not add, in Starboard's help](../../topics/add-a-plugin.md#if-it-does-not-work)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
