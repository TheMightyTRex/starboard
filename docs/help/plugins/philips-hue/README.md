# Philips Hue
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Your Hue lights in Starboard, by room, by zone and by device type: on and off, brightness, a colour or a white,
scenes and schedules. It talks only to the Hue bridge on your home network. Nothing goes to the Hue cloud, and it
needs no Hue account.

A Starboard plug-in by TheMightyTRexUK, MIT licence. Needs Starboard with plug-in API 1.16 or later (Starboard 0.23.0).

## Set it up

1. Add it from **Settings**, **Plug-ins**, **Catalogue**, under **Home**.
2. On its **Bridge** tab, give the bridge's address, such as `192.168.1.20`, and select **Pair with a bridge**. The
   address is in the Hue app: **Settings**, **My Hue system**, your bridge, **IP address**. A bridge found on your
   network is listed too: select **Turn on** beside it.
3. Press the round link button on top of the bridge. The page waits 90 seconds and says when it is paired.

## Its tabs

| Tab | What it does |
|---|---|
| Bridge | Pairs with the bridge, checks it answers (**Test**), or forgets it (**Remove**). |
| Rooms, Zones, Device types | The same lights grouped three ways. Open one to turn on or off each light, choose its brightness, and choose its colour or white from a list of names. A switch turns on or turns off every light in it, and two lists set the brightness and colour of them all at once. |
| Scenes | Each room's and zone's scenes. **Turn on** shows a scene; **Turn off** turns that room's lights off. |
| Schedules | Timed actions written in words, kept on the bridge. |
| When something plays | A scene to run when someone starts playing something in Jellyfin, after sunset if you like. |

A light's colour is always said in words, such as "On at 80%, warm white", never by colour alone. A light the bridge
cannot reach says **Not reachable**.

## Schedules in words

Write when, at what time, then what. The list shows each schedule in the same words, so you change one by changing its words with **Change**:

- `Every weekday at 07:00, Kitchen to 80%`
- `Every Monday, Wednesday and Friday at sunset, Lounge to Relax` (a scene)
- `Every weekend at 09:00, Bedroom to warm white at 40%`
- `Every day at 23:30, every light off`
- `Once on 24 December at 18:00, Hall on`, or `Tomorrow at 06:30, Porch on`

Days can be every day, weekday or weekend, or days by name. Times are hours and minutes, or sunrise or sunset. The
name after the comma is a room, a zone, a light or every light. Each schedule is on and turned off with
**Turn on** and **Turn off**, and removed from the row's **More** menu.

Schedules are kept on the bridge, so they run while Starboard or this plug-in rests. The bridge's newer API (CLIP v2) has no schedules. So these use its version 1 schedules, and rules on its daylight sensor for sunrise and sunset.
Sunrise and sunset need your location set in the Hue app. A one-off schedule is removed by the bridge once it has
run. Schedules made in the Hue app or another app are listed under **Made in another app**, to read only.

## When something plays

On the **When something plays** tab, turn on one scene. When Starboard finds something has started playing in Jellyfin, the
plug-in runs that scene. Starboard checks what is playing every 5 minutes, so the lights can change up to 5 minutes
after it starts. **Only after sunset** (on when added) runs it only when the bridge's daylight sensor says it is dark.
**Only when playing in these apps** limits it to apps you name, such as Jellyfin Android TV.

## On the dashboard

- **Rooms**: a list card of your rooms and their lights, such as "Kitchen: On at 80%, 2 of 3 lights".
- **Lights on**: a status card, such as "Lights on in Kitchen and Lounge".

Plug-in cards cannot hold buttons. For a quick on and off, use **Turn every light off** and **Turn every light on** under **Actions** on the plug-in's page.

## What it may do

- `network:lan` (medium risk): your home network, to reach the bridge. It talks to nothing else.
- `media:read` (medium risk): only so Starboard sends it the `playback.started` event. Its key can read your library,
  and it never asks for it.
- It keeps the bridge's key, its address and the bridge's certificate fingerprint in its own folder. It refuses a
  bridge whose certificate is not the one it paired with, so nothing else on the network can pose as the bridge.
- It runs one small container: 48 MB of memory and a quarter of a processor at most. It rests when not used
  (`"start": "when_needed"`), and Starboard starts it again when you open its page, a card asks or an event comes.
- Memory, measured 20 November 2026 against a made-up bridge with 8 lights in 4 rooms and 2 zones, locked down as Starboard runs it. It used 15.4 MB at start, 16.6 MB after 160 screens, schedules and switches, and 15.6 MB a minute later. It uses 0% of a processor at rest, and nothing while it rests.

## Finding the bridge

The **Bridge** tab asks your network for Hue bridges by mDNS (multicast DNS). Inside Docker's own network that question
often reaches nothing, so giving the bridge's address is the dependable way. Hue's own discovery website is never
used: it is part of the Hue cloud.

## Add it

Needs Starboard with plug-in API 1.16 or later. In Starboard, go to **Settings**, then **Plug-ins**, then **Catalogue**,
and find it under **Home**. Or, under **Add one from elsewhere**, give this address:

`https://raw.githubusercontent.com/TheMightyTRex/starboard-plugins/main/philips-hue/starboard-plugin.json`

Or run `python3 install.py` in this folder.

## For developers

- `app.py`: the screens Starboard draws, the cards, the buttons and the event.
- `hue.py`: the bridge: HTTPS with its pinned certificate, pairing, CLIP v2 and the version 1 schedules and rules,
  and mDNS discovery.
- `words.py`: colours in words, and schedules written and read in one sentence.
- Tests: `python3 -m unittest tests.test_philips_hue`, against `tests/hue_mock_bridge.py`, a made-up bridge over
  HTTPS (needs `openssl` to make its certificate).
- Pictures and the accessibility check of its pages in Starboard: `tools/hue_screens/run.sh`.

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
