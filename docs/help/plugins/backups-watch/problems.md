# Backups watch: Problems
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Find what is wrong with Backups watch, then follow the numbered answer.

```flow
title: Find your answer
start: Backups watch is not working as it should
q: What does its card say?
  Cannot check or Last check failed -> q2
  Needs attention -> 3
  Needs setting up -> 4
  OK, but I expected an alert -> 5
q2: What does it say after the tool's name?
  It refused the user name or password -> 1
  The address does not answer like this tool -> 2
  It could not be reached -> 2
  Its certificate is not trusted -> 6
1: Check the sign-in #check-the-sign-in
2: Check the address #check-the-address
3: Read which backup #read-which-backup
4: Enter the address #enter-the-address
5: Check the alerts #check-the-alerts
6: Accept the certificate #accept-the-certificate
```

## Check the sign-in

1. Open your backup tool in a browser and sign in with the same user name and password.
2. In Backups watch's settings, enter them again and select **Save**. The password is never shown again, so enter it afresh.
3. Select **Check now** on its tab.

## Check the address

1. Open the address in a browser on another computer. Backrest answers with its page, and the Kopia server with its sign-in.
2. Check **Backup tool** matches the program at that address. Backrest's address is the one you open its page at, with no path after it.
3. Where Starboard and the tool run on the same computer, use the computer's own address on your network, not `localhost`. Backups watch runs in its own container.

## Read which backup

1. Open the **Backup runs** card. The backup that needs attention says **Overdue** or **Last run failed** first.
2. Overdue means no good run for longer than **Overdue after**. Open your backup tool to find out why it did not run.
3. When the next check finds a good run, the alert clears by itself.

## Enter the address

Open Backups watch's tab, choose the tool, enter its address and select **Save**, then **Activate**.

## Check the alerts

1. Alerts are on by default: check **Send alerts through Starboard** is activated.
2. Check Starboard's own alerts are on in **Settings**, then **Alerts**. Backups watch uses the same place.
3. A backup is only overdue after **Overdue after** hours with no good run. A failed run alerts at the next hourly check.
4. Starboard before 0.26.0 does not take alerts from plug-ins: the card then says so, and updating Starboard fixes it.

## Accept the certificate

The Kopia server makes its own certificate unless you gave it one. On your own network, activate **Accept a self-signed certificate** and select **Save**.

## Things this version does not do

- **Duplicati:** not supported. Its server API could not be checked from its documentation.
- **Tried against the real program:** not yet. This version was tested with recorded sample answers that follow each tool's published API. If your tool answers differently, the card says "Cannot check" or shows no runs: tell us on the Discord support server or in an issue.

## Find out more

- [Settings](../backups-watch/settings.md)
- [Dashboard card](../backups-watch/dashboard-card.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
