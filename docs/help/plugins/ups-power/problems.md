# UPS and power: Problems
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Find what is wrong with UPS and power, then follow the numbered answer.

```flow
title: Find your answer
start: UPS and power is not working as it should
q: What does its card say?
  Cannot read it or Last reading failed -> q2
  On battery or Low battery -> 3
  Needs setting up -> 4
  On mains power, but I expected an alert -> 5
q2: What does it say after NUT or PeaNUT?
  Nothing is listening at that address and port -> 1
  It could not be reached -> 1
  It did not answer in time -> 1
  It refused the user name or password -> 2
  NUT has no UPS called -> 6
1: Check the address #check-the-address
2: Check the sign-in #check-the-sign-in
3: Read what the UPS says #read-what-the-ups-says
4: Enter the address #enter-the-address
5: Check the alerts #check-the-alerts
6: Check the UPS name #check-the-ups-name
```

## Check the address

1. For NUT, check the address and port (3493 unless you changed it) from another computer: `upsc ups@192.0.2.10` lists the variables when it works.
2. NUT must listen on an address other computers can reach: in `upsd.conf`, `LISTEN 0.0.0.0 3493` (or your server's address), then restart `upsd`. Where Starboard and NUT run on the same computer, use the computer's own address on your network, not `localhost`. UPS and power runs in its own container.
3. For PeaNUT, open its address in a browser on another computer. It shows its page.
4. Check **Read the UPS through** matches the program at that address.

## Check the sign-in

PeaNUT only. In UPS and power's settings, enter the user name and password again and select **Save**. The password is never shown again, so enter it afresh. Select **Check now**.

## Read what the UPS says

1. On battery means the UPS says the mains power is gone. Check the plug, the socket and the breaker.
2. The alert clears by itself when the UPS reports mains power again.
3. A UPS that is charging after a cut shows **On mains power** at once, with a battery under 100%.

## Enter the address

Open UPS and power's tab, choose how to read the UPS, enter its address and select **Save**, then **Activate**.

## Check the alerts

1. Alerts are on by default: check **Send alerts through Starboard** is activated.
2. Check Starboard's own alerts are on in **Settings**, then **Alerts**. UPS and power uses the same place.
3. It asks once a minute: a cut shorter than a minute may pass unseen.
4. Starboard before 0.26.0 does not take alerts from plug-ins: the card then says so, and updating Starboard fixes it.

## Check the UPS name

NUT lists each UPS by the name in `ups.conf`. Leave **UPS name** empty to use the first one, or enter the name exactly as `upsc -l` shows it.

## Things this version does not do

- **Pause heavy jobs on battery:** not possible yet. A plug-in cannot pause Starboard's own jobs. The card and the alert tell you; NUT's `upsmon` shuts the server down.
- **Tried against a real UPS:** not yet. We tested this version with a made-up NUT server that follows NUT's text protocol, and with recorded PeaNUT answers that follow its README. If your setup answers differently, the card says "Cannot read it" or shows no figures. Tell us on the Discord support server or in an issue.

## Find out more

- [Settings](../ups-power/settings.md)
- [Dashboard card](../ups-power/dashboard-card.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
