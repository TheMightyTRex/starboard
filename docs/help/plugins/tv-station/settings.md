# Create your own TV channel: Settings
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Create your own TV channel's settings are on its tab in **Settings**, then **Plug-ins**. Choices save as soon as you make them. Its pages, **Channels**, **Guide**, **Schedule grid**, **Idents and clips** and **Broadcast pack**, open from the same tab.

## Channels

**Channels** lists your channels, each with its number, its name and what is on now. Select a channel to open it.

### Add a channel

1. In **Add a channel**, enter its name, such as Comedy, and select **Add**.
2. Open it. Under **What it shows**, select **Add a series**, **Add a film**, **Add a collection**, **Add a playlist**, **Add a genre** or **Add a decade**.
3. Enter the name, or the start of it, and select **Add**. Create your own TV channel finds it in Jellyfin and says what it added, and any other matches.

Its line-up is read from Jellyfin straight away. The programmes for today and tomorrow are listed at the end of the channel's page, under **Today and tomorrow**.

### Each channel's settings

| Section | Setting | What it does |
|---|---|---|
| Channel | **On air** | Turn on to put it in Jellyfin's Live TV. **Up** and **Down** move it in the list, which sets its number. **Remove** takes it off; its settings are kept in the plug-in's folder |
| Channel | **Name** | Select **Rename**. Shown in Jellyfin, in the guide and on the television |
| Channel | **Number** | Select **Change number**. Leave it empty to number it by its place in the list |
| Channel | **Colour** | On its Coming up next cards and its made logo |
| Channel | **Broadcast pack** | **The station's pack**, **Its own pack** or **No pack**. The pack gives the on-screen logo, idents, the logo with music, transitions, the Coming up next card and promos |
| Channel | **Its own pack** | Select **Upload its own pack** and choose a zip made from the template. Then choose **Its own pack** |
| Channel | **Logo** | Select **Add logo** and choose a PNG with a clear background. It is used in place of the pack's logo. With neither, a logo with its number and name is made |
| What it shows | Each series, film or collection | **Up** and **Down** set the order; **Remove** takes it off |
| Order and times | **Order** | **In order** plays each series in aired order, taking turns. **Shuffled** plays them in a new order each time round |
| Order and times | **Episodes of a series in a row** | From 1 to 6 |
| Order and times | **Programmes start** | **Back to back**, or on the quarter, half or whole hour, with a break filling the time to it |
| Order and times | **Break between programmes** | Up to 5 minutes after each programme |
| Breaks | **Idents** | This channel's, the station's, both, or none |
| Breaks | **Idents play** | In order, or in a random order. A broadcast pack's idents always play in a random order |
| Breaks | **Trailers** | Jellyfin's own trailers of the films on this channel |
| Breaks | **Your clips** | This channel's, the station's, both, or none |
| Breaks | **Add an ident**, **Add a clip** | Choose a video of up to 60 MB, or enter the name of a Jellyfin collection or folder of them. A clip can be up to 10 minutes |
| On-screen logo and straps | Every on-screen logo setting | **Station default** uses the station's choice, which the option names |
| On-screen logo and straps | **Preview a frame** | Opens a frame of what is on now, drawn with the settings, in a new tab |
| On-screen logo and straps | **Preview a Coming up next card** | Opens the next card, in a new tab |

A change to what a channel shows, its order or its times starts after the programme on air ends, so nobody watching meets a jump.

## Guide

**Guide** has a table for each channel: what is on in the next 24 hours, with the time, the programme, the episode, New or Repeat, and what it is about. Jellyfin's own guide has 7 days.

## Schedule grid

**Schedule grid** lists your channels, each with a link that opens its grid in a new tab: a week, Monday to Sunday, in 15 minute steps. Films and series placed on it play at those times every week; the time between them keeps the channel's automatic line-up, whole programmes only, and the rest is a break. A channel with nothing on its grid is as it was. The guide in Jellyfin follows the grid.

| On the grid | What it does |
|---|---|
| **Channel**, **Show** and **Day** | Which channel, and the whole week or one day |
| **Add a programme**, or an empty time | Search Jellyfin, choose a film or series, its day and time and, for a series, where it starts: from the first episode, from the next episode not watched, or from a series and episode |
| Drag a programme to an empty time | Moves it. Everything a drag does can also be done without one: select a programme for **Move 15 minutes earlier**, **Move 15 minutes later**, **Move to** a day and time, or **Pick it up, then choose a time** and select an empty time |
| **Stripe across the week** | On a series: the same time on the weekdays you choose, 1 to 4 episodes each day, Saturday and Sunday too if you choose. Each slot plays the next episode in order, and the next week carries on |
| **Where the series starts** | The first episode, the next episode not watched, or an episode you choose, from this week |
| **Copy a day** | Copies one day to the days you choose, in place of what was on them |
| **Suggest a schedule** | Proposes a week from watch history: the series people watch most, on weekdays at the time they watch them, and films on Saturday and Sunday evenings. Nothing is saved until you select **Save the suggestion**; **Discard the suggestion** keeps the grid as it was |
| **Undo** | Takes back the last change |

A programme takes the time of its longest episode, rounded up to 15 minutes, so programmes never run into each other. A change that would overlap another programme is refused, and the message names it. In the grid, the arrow keys move between times and days, Page Up and Page Down by an hour, and Enter opens a programme's actions or adds one at an empty time.

## Idents and clips

The station's own idents and clips, for every channel that chooses **The station's** or **Both**. Add a video of up to 60 MB, or the name of a Jellyfin collection or folder of them.

## Broadcast pack

Your own branding for every channel: the on-screen logo, the logo with its music, idents, transitions, and backgrounds for the Coming up next card and the promos, with music for the promos. [Make a broadcast pack](https://themightytrex.github.io/starboard-plugins/help/use/make-a-broadcast-pack.html) has the specification.

| Row | What it does |
|---|---|
| **Station's pack** | Select **Upload a pack** and choose a zip of up to 60 MB made from the template. It is checked first; when it passes, every channel without a pack of its own uses it. **Remove** stops using it |
| **Try the example pack** | Turn on to use Example TV, a made-up channel drawn in code, for every channel without a pack of its own. The first time, it takes about 2 minutes to make, while no channel is playing. Turn off to go back to your own pack, or none |
| **The last pack checked** | What the check found: each problem with a pack that was not used, or notes on one that was, such as a picture scaled to fit |
| **Downloads** | The template (folders, `pack.json`, its schema and a README), the placement guides for the Coming up next card, the promo and the on-screen logo, and the example pack as a zip |
| **Promos kept** | Each promo, with its programme, its day and time and its channel |
| **Each channel's pack** | Which pack each channel uses. Change it on the channel's page |

## Station

| Setting | What it does |
|---|---|
| **Station name** | Shown in Jellyfin's Live TV, on the cards and with the on-screen logo. Home TV unless you change it |
| **First channel number** | 1 puts your channels first in Jellyfin's Live TV, before the free channels from 101 |
| **Address Jellyfin uses to reach this plug-in** | Filled in by itself: Starboard 0.23.0 and later give the plug-in its address on your home network. Enter one only if Jellyfin runs on another computer that reaches this one by another address |
| **Days in Jellyfin's guide** | 7 unless you change it, up to 14 |

## Streaming

| Setting | What it does |
|---|---|
| **Picture size** | 720p is lighter on the processor; 1080p is sharper |
| **Most channels at once** | Each channel being watched is one conversion. People watching the same channel share it. 2 unless you change it |
| **Stop a channel after the last viewer leaves** | 30 seconds unless you change it |
| **Copy programmes when nothing is drawn on them** | A channel with no on-screen logo and no straps plays its programmes as they are, with no converting |

## Promos

Promos are made only for channels whose broadcast pack has a promo background.

| Setting | What it does |
|---|---|
| **Make promos in quiet hours** | In Starboard's quiet hours, one at a time at the lowest priority, and never while anyone is watching: a few short clips of a programme coming up, a music bed from the pack, and its title, day and time and channel. Turned on unless you change it |
| **Promos kept for each channel** | 3 unless you change it, up to 6 |
| **Replace each promo after** | 2 days unless you change it. A promo is also replaced once its programme has started, so they never pile up |
| **Show promos for your other channels** | Each channel's breaks show the promos of your other channels too. Turned on unless you change it |

## On-screen logo

The station's choices, which every channel uses unless it has its own.

| Setting | What it does |
|---|---|
| **On-screen logo** | The channel's logo, the channel's name, the station's name, or none |
| **Corner** | Which corner of the picture it sits in |
| **Size** | Small, medium or large |
| **Distance from the edge** | **Inside the safe area** keeps it in the picture on every television |
| **Opacity** | From 30% to 100%. 80% unless you change it |
| **When it shows** | Always; only during programmes; or during programmes and cards, not in idents, trailers and clips |
| **Fades in after the opening** | Keeps a programme's opening titles clear |
| **Clock** | The time beside the logo |
| **Label** | New or Repeat, or Live, in words, for the first 2 minutes of each programme |
| **Backing plate** | A dark, partly transparent box behind the logo, the clock and the label, so they are clear on any picture. Turned on unless you change it |

## Straps and cards

| Setting | What it does |
|---|---|
| **Programme name at the start** | For 8 seconds as each programme starts |
| **Up next during the end credits** | The next programme and its time |
| **Up next shows for** | 30 seconds unless you change it |
| **Coming up next and Later cards** | In the breaks: the programme's picture, its title, the date and time it is shown and a short synopsis. Off, a break with no clips shows the station's name |

## Actions

- **Try the example pack:** makes Example TV, if it is not made yet, and uses it for every channel without a pack of its own.
- **Make promos now:** makes any promos that are due, one at a time at the lowest priority, unless someone is watching. They are also made each hour of Starboard's quiet hours.
- **Read the channels from Jellyfin again:** reads every channel's line-up now. It also runs each night at 04:40, so new episodes join.
- **Stop every channel playing:** stops every stream now. Anyone watching can choose the channel again.

## Find out more

- [Dashboard card](../tv-station/dashboard-card.md)
- [Problems](../tv-station/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
