# Line speed: Problems
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Find what is wrong with Line speed from what its tab or its cards say, then follow the numbered answer.

```flow
title: Find your answer
start: Line speed is not working as it should
q: What does its tab say?
  Failed or Not answering -> 1
  Needs an update -> 2
  Active -> q2
q2: What does the card say?
  Not tested yet -> 3
  Problem on the card -> 4
  Did not answer after Test now -> 5
  A slower speed than expected -> 6
1: Start it again #start-it-again
2: Update it or update Starboard #update-it-or-update-starboard
3: Wait for the first test #wait-for-the-first-test
4: Check the internet connection #check-the-internet-connection
5: Wait for the test to finish #wait-for-the-test-to-finish
6: Make the test fairer #make-the-test-fairer
```

## Start it again

1. On Line speed's tab, read the message under its state: it says why it stopped.
2. Select **Try again**.
3. If it stopped soon after an update, select **Roll back to** and the version you had. Read [Updates](../line-speed/updates.md).
4. Still failing: go to **System**, then **Logs**, and find its name.

## Update it or update Starboard

Your Starboard's plug-in API is outside what this version of Line speed works with, so Starboard stopped it.

1. Select **Check for an update** on its tab.
2. If there is none, update Starboard. Read [Update Starboard](../../topics/update-starboard.md).

## Wait for the first test

The cards say "Not tested yet" and "Next test at" with the hour from **Test at**. Nothing is wrong: Line speed tests once a night, so the first result comes at that hour.

To get a result now:

1. Go to **Settings**, then **Plug-ins**, then **Line speed**.
2. In **Actions**, select **Test now**, then **Test now** in the box that asks first.

## Check the internet connection

The **Line speed** card says **Problem** and the reason, such as a time-out: the last test could not download its test file. This is shown only until the first test works.

1. Check this computer can reach the internet.
2. Check nothing on your network blocks `speed.cloudflare.com`, where the test file comes from.
3. Select **Test now** to try again.

## Wait for the test to finish

Starboard waits 10 seconds for a button. A test on a slower line can take longer, so Starboard says "Line speed did not answer", but the test carries on.

1. Wait a minute or two.
2. Open the dashboard: the **Line speed** card shows the new result when the test is done.
3. If tests often take this long, choose a smaller **Test size**.

## Make the test fairer

Line speed times one download of **Test size**, so anything else using the line at the same time slows it.

- Choose a **Test at** hour when nothing is downloading or streaming.
- On a fast line, choose a larger **Test size**: a small file finishes before the line reaches full speed.
- It measures download speed only, not upload.

## Report a problem

If none of these helps, tell its maker, with what its tab and the cards say: [the plug-ins' issues on GitHub](https://github.com/TheMightyTRex/starboard-plugins/issues).

## Find out more

- [Settings](../line-speed/settings.md)
- [Updates](../line-speed/updates.md)
- [If a plug-in will not add, in Starboard's help](../../topics/add-a-plugin.md#if-it-does-not-work)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
