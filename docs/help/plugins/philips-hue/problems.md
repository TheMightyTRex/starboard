# Philips Hue: Problems
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Find what is wrong with Philips Hue from what its tab or its cards say, then follow the numbered answer.

```flow
title: Find your answer
start: Philips Hue is not working as it should
q: What does its tab say?
  Failed or Needs an update -> 1
  Active, but something is wrong -> q2
q2: What is wrong?
  Pairing does not find the bridge -> 2
  The link button was not pressed in time -> 3
  The bridge did not answer -> 4
  A different certificate -> 5
  The bridge no longer knows this plug-in -> 6
  A light says Not reachable -> 7
  A schedule will not add -> 8
  The scene does not run when something plays -> 9
1: Start it again #start-it-again
2: Give the bridge's address #give-the-bridges-address
3: Pair again #pair-again
4: Check the bridge is on the network #check-the-bridge-is-on-the-network
5: Check the bridge's address #check-the-bridges-address
6: Remove the bridge and pair again #remove-the-bridge-and-pair-again
7: Check the light #check-the-light
8: Write the schedule again #write-the-schedule-again
9: Check When something plays #check-when-something-plays
```

## Start it again

1. On its tab, read the message under its state: it says why it stopped.
2. Select **Try again**.
3. If it says **Needs an update**, your Starboard's plug-in API is older than 1.16: update Starboard. Read [Update Starboard](../../topics/update-starboard.md).
4. Still failing: go to **System**, then **Logs**, and find its name.

## Give the bridge's address

The **Bridge** tab asks your network for Hue bridges. Inside Docker's own network that question often reaches nothing, so **Found on your network** can stay empty. Hue's own discovery website is never used: it is part of the Hue cloud.

1. In the Hue app, go to **Settings**, then **My Hue system**, then your bridge, and find **IP address**.
2. Enter it in **Pair with a bridge**, such as `192.168.1.20`, and select **Pair with a bridge**.
3. If it says "What answered at" the address "is not a Hue bridge", the address belongs to something else: check it in the Hue app.

## Pair again

The page waits 90 seconds for the link button. If it was not pressed in time:

1. Select **Activate** beside the bridge under **Not paired yet**.
2. Within 90 seconds, press the round link button on top of the bridge once. The page pairs as soon as it is pressed.

## Check the bridge is on the network

Its tab and cards say "The bridge at" its address "did not answer".

1. Check the bridge's light shows it is on and connected, and that the Hue app reaches it.
2. Check the address in the Hue app: a router can give the bridge a new address. If it changed, remove the bridge on **Bridge** and pair again with the new one. To stop it changing, reserve the address for the bridge in your router.
3. Check Starboard's server and the bridge are on the same home network.
4. If it says "The bridge is busy", wait a moment and try again.

## Check the bridge's address

It says "Something at" the address "answered with a different certificate from the bridge you paired". The plug-in keeps the certificate of the bridge it paired with and refuses anything else, so nothing on your network can pose as the bridge.

1. If you replaced or reset the bridge, or its address now belongs to another device, select **Remove** in the bridge's **More** menu on **Bridge**.
2. Pair again with the right address. Read [Install](../philips-hue/install.md).

## Remove the bridge and pair again

It says "The bridge no longer knows this plug-in". Someone removed its key from the bridge, for example in the Hue app or by a reset.

1. On **Bridge**, select **Remove** in the bridge's **More** menu.
2. Pair again and press the link button. Read [Install](../philips-hue/install.md).

The schedules it made stay on the bridge and are listed again once it is paired, unless the bridge was reset.

## Check the light

A light says **Not reachable** when the bridge cannot reach it.

1. Check the light has power, such as from its wall switch: a light with no power cannot be reached.
2. Check the Hue app: if it says the same, the light is too far from the bridge or another light, or it has lost power.
3. Its switch stays on the tab: a change you make waits until the bridge reaches the light again.

## Write the schedule again

**Add a schedule** says what it could not read. For example: "Give the time as hours and minutes, such as 07:00 or 18:30, or say sunrise or sunset". Write it as when, at what time, then what: `Every weekday at 07:00, Kitchen to 80%`. Read [Settings](../philips-hue/settings.md) for every part.

- **Sunrise and sunset:** "Your bridge does not know sunrise and sunset yet" means your location is not set in the Hue app. Set it there, then try again. Sunrise and sunset work only with a schedule that repeats.
- **A scene** can be shown only in a room or a zone, and only by a scene's name in that room or zone.
- **Two with the same name:** rename one in the Hue app.

## Check When something plays

1. Check one scene is activated on **When something plays**.
2. **Only after sunset** is active: the scene runs only when the bridge's daylight sensor says it is dark. Deactivate it to run at any time.
3. **Only when playing in these apps** is not empty: the app must have one of those names. Leave it empty for any app.
4. Starboard checks what is playing every 5 minutes, so the lights can change up to 5 minutes after something starts.
5. The intro on **When something plays** says when it last ran, and for what.

## Report a problem

If none of these helps, tell its maker, with what its tab and the cards say: [the plug-ins' issues on GitHub](https://github.com/TheMightyTRex/starboard-plugins/issues).

## Find out more

- [Settings](../philips-hue/settings.md)
- [Updates](../philips-hue/updates.md)
- [If a plug-in will not add, in Starboard's help](../../topics/add-a-plugin.md#if-it-does-not-work)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
