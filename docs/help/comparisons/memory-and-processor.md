[Help centre](../README.md) · Comparison tests · reference

# Memory and processor: Starboard against other stacks

These are the memory and processor figures from the comparison tests of 13 November 2026, for each app at rest and
for each whole stack. Every app ran on a fresh, empty set-up, so the figures show what an app costs when it is idle,
before it has a library. [How the tests were run](how-the-tests-were-run.md) has the method and how to repeat it.

## In short

- **Starboard and Reelix Lite together idle in about 35 MiB.** The apps they replace (Radarr, Sonarr, Lidarr,
  Readarr, Prowlarr and Jellyseerr) idle in about 645 MiB: about 18 times as much, from 6 containers instead of 2.
- **At rest, both use almost no processor:** 0.03% of one core for Starboard and Reelix Lite, against 0.39% for the
  six apps they replace.
- **On a whole stack,** with Jellyfin, Audiobookshelf, qBittorrent and NZBGet added to each, Starboard's stack idles
  in about 798 MiB, a classic stack in about 1,409 MiB and a stack led by a dashboard in about 1,644 to 1,668 MiB.
- **Jellyfin is the largest part of every stack.** Starboard saves memory on everything around it.

## Read these figures with care

> [!IMPORTANT]
> The computer was very busy during the tests. Another program was converting a video on 6 to 9 of its 12
> processor threads, and its memory was nearly full. When memory runs short, Linux takes back file cache that Docker
> counts as an app's memory, so **every memory figure here is lower than it would be on a quiet computer.** Every app
> ran under the same conditions, so the apps compare fairly with each other. Compare figures within this page, not
> with figures measured on another day.

- **Units.** Memory is in mebibytes (MiB), as Docker reports it; 1 MiB is about 1.05 megabytes. Processor is a
  percentage of one processor core, so 100% is one core fully busy.
- **Median and peak.** Each app was read 36 times over 3 minutes. The median is the middle reading; the peak is the
  highest.
- **Empty apps.** Memory with a real library is higher for every app. For the figures on a real server, read
  [Basics, Full install and Everything](../topics/install-types.md#memory-and-processor).
- **Readarr** could not be measured, because it has no image that can be pulled. Its figures are an estimate from
  4 November 2026: about 120 MB and 0.07% of a core.

## Whole stacks

Each stack has its own apps plus four apps every stack shares: Jellyfin, Audiobookshelf, qBittorrent and NZBGet. The
shared apps were read on a real server on the same day, with real libraries: 763.5 MiB and 1.60% of a core together,
counted the same way for every stack.

<table>
<caption>Whole stacks at rest, 13 November 2026, including the four shared apps</caption>
<thead>
<tr><th scope="col">Stack</th><th scope="col">Apps besides the shared ones</th><th scope="col">Memory, those apps (MiB)</th><th scope="col">Memory, whole stack (MiB)</th><th scope="col">Processor, whole stack (% of one core)</th><th scope="col">Containers</th></tr>
</thead>
<tbody>
<tr><th scope="row">Starboard with Reelix Lite</th><td>Starboard, Reelix Lite</td><td>34.8</td><td>798</td><td>1.63</td><td>6</td></tr>
<tr><th scope="row">Starboard with the full Reelix</th><td>Starboard, Reelix full</td><td>47.0</td><td>811</td><td>1.63</td><td>6</td></tr>
<tr><th scope="row">Starboard with Reelix Lite and the On demand plug-in</th><td>Starboard, Reelix Lite, On demand</td><td>51.5</td><td>815</td><td>1.64</td><td>7</td></tr>
<tr><th scope="row">Classic stack with Jellyseerr</th><td>Radarr, Sonarr, Lidarr, Prowlarr, Readarr (estimate), Jellyseerr</td><td>645.2</td><td>1,409</td><td>1.99</td><td>10</td></tr>
<tr><th scope="row">Led by a dashboard, with Homarr</th><td>The classic six, Homarr, Jellystat and its database, Unpackerr, Recyclarr</td><td>904.5</td><td>1,668</td><td>2.53</td><td>15</td></tr>
<tr><th scope="row">Led by a dashboard, with Homepage</th><td>The same, with Homepage in place of Homarr</td><td>880.0</td><td>1,644</td><td>2.32</td><td>15</td></tr>
</tbody>
</table>

Leaving out the shared apps, which every stack has, Starboard's stack uses about 18 times less memory than the
classic stack and about 25 to 26 times less than a stack led by a dashboard. On the whole stack it saves about 610 MiB
against the classic stack and about 845 to 870 MiB against a stack led by a dashboard.

Bazarr, for subtitles, is left out of every stack, because every one of them needs it until Reelix has subtitles of
its own. It used 173.6 MiB on a fresh start.

## Starboard and Reelix

<table>
<caption>Starboard, Reelix and the On demand plug-in at rest, 13 November 2026</caption>
<thead>
<tr><th scope="col">App and version</th><th scope="col">Memory, median (MiB)</th><th scope="col">Memory, peak (MiB)</th><th scope="col">Processor, median (% of one core)</th><th scope="col">Processor, peak (% of one core)</th><th scope="col">Image download (MB)</th></tr>
</thead>
<tbody>
<tr><th scope="row">Starboard 0.16.5</th><td>16.9</td><td>18.7</td><td>0.00</td><td>0.01</td><td>38</td></tr>
<tr><th scope="row">Reelix Lite 0.8.6</th><td>17.9</td><td>30.0</td><td>0.03</td><td>3.82</td><td>114</td></tr>
<tr><th scope="row">Reelix full 0.8.7</th><td>30.1</td><td>33.9</td><td>0.03</td><td>0.12</td><td>319</td></tr>
<tr><th scope="row">On demand plug-in 0.9.0, without its engine</th><td>16.7</td><td>16.9</td><td>0.01</td><td>0.06</td><td>69</td></tr>
</tbody>
</table>

Reelix Lite's peak of 3.82% is its health check, which starts a second Reelix process once a minute. Starboard was
not given any apps to watch in this test; with a real stack it read the same 16.9 MiB on the same day.

## The apps Reelix replaces

<table>
<caption>The apps Reelix replaces, at rest, 13 November 2026</caption>
<thead>
<tr><th scope="col">App and version</th><th scope="col">Memory, median (MiB)</th><th scope="col">Memory, peak (MiB)</th><th scope="col">Processor, median (% of one core)</th><th scope="col">Processor, peak (% of one core)</th><th scope="col">Image download (MB)</th></tr>
</thead>
<tbody>
<tr><th scope="row">Radarr 6.4.4</th><td>106.3</td><td>119.5</td><td>0.08</td><td>0.67</td><td>90</td></tr>
<tr><th scope="row">Sonarr 4.0.20</th><td>81.0</td><td>97.0</td><td>0.08</td><td>0.63</td><td>87</td></tr>
<tr><th scope="row">Lidarr 3.1.6</th><td>93.8</td><td>116.9</td><td>0.08</td><td>0.23</td><td>121</td></tr>
<tr><th scope="row">Prowlarr 2.7.0</th><td>87.8</td><td>92.0</td><td>0.08</td><td>1.04</td><td>80</td></tr>
<tr><th scope="row">Readarr (not measured)</th><td>about 120 (estimate)</td><td>not measured</td><td>about 0.07 (estimate)</td><td>not measured</td><td>not measured</td></tr>
<tr><th scope="row">Jellyseerr 2.7.3</th><td>156.3</td><td>174.0</td><td>0.00</td><td>0.13</td><td>433</td></tr>
<tr><th scope="row">Seerr 3.5.2, which follows Jellyseerr</th><td>127.0</td><td>218.7</td><td>0.00</td><td>0.01</td><td>146</td></tr>
<tr><th scope="row">Overseerr 1.35.0</th><td>128.2</td><td>172.6</td><td>0.02</td><td>3.63</td><td>180</td></tr>
</tbody>
</table>

## Dashboards

Starboard is a dashboard as well, so a stack with another dashboard pays for two.

<table>
<caption>Other dashboards at rest, 13 November 2026</caption>
<thead>
<tr><th scope="col">Dashboard</th><th scope="col">Memory, median (MiB)</th><th scope="col">Memory, peak (MiB)</th><th scope="col">Processor, median (% of one core)</th><th scope="col">Processor, peak (% of one core)</th></tr>
</thead>
<tbody>
<tr><th scope="row">Homarr</th><td>129.9</td><td>161.1</td><td>0.21</td><td>25.62</td></tr>
<tr><th scope="row">Homepage 2.8.0</th><td>105.4</td><td>113.4</td><td>0.00</td><td>4.34</td></tr>
<tr><th scope="row">Heimdall 2.8.4, with internet</th><td>85.6</td><td>86.4</td><td>0.00</td><td>0.14</td></tr>
<tr><th scope="row">Heimdall 2.8.4, without internet</th><td>26.6</td><td>58.7</td><td>37.09</td><td>42.37</td></tr>
<tr><th scope="row">Organizr</th><td>33.7</td><td>38.6</td><td>0.00</td><td>5.25</td></tr>
<tr><th scope="row">Dashy 4.9.17</th><td>26.6</td><td>65.0</td><td>0.00</td><td>0.05</td></tr>
</tbody>
</table>

Without internet, Heimdall asks for its list of apps again and again, and uses about a third of a core. With
internet it rests at almost nothing, so the figure with internet is the fair one for a normal home.

## Common add-ons

<table>
<caption>Apps often added to a media stack, at rest, 13 November 2026</caption>
<thead>
<tr><th scope="col">App</th><th scope="col">What it does</th><th scope="col">Memory, median (MiB)</th><th scope="col">Processor, median (% of one core)</th></tr>
</thead>
<tbody>
<tr><th scope="row">Jellystat with its database</th><td>Watch statistics for Jellyfin</td><td>117.4</td><td>0.22</td></tr>
<tr><th scope="row">Tautulli 2.19.1</th><td>Watch statistics for Plex</td><td>77.2</td><td>0.02</td></tr>
<tr><th scope="row">Bazarr 1.6.2</th><td>Subtitles</td><td>173.6</td><td>0.09</td></tr>
<tr><th scope="row">Kavita</th><td>Ebooks and comics</td><td>337.4</td><td>0.99</td></tr>
<tr><th scope="row">Wizarr 0.13.0</th><td>Invitations to Jellyfin</td><td>124.5</td><td>0.02</td></tr>
<tr><th scope="row">Maintainerr</th><td>Library clean-up rules</td><td>127.4</td><td>0.00</td></tr>
<tr><th scope="row">Navidrome 0.64.2</th><td>A music server</td><td>16.4</td><td>0.01</td></tr>
<tr><th scope="row">Tdarr, server only</th><td>Converting the library</td><td>31.1</td><td>0.07</td></tr>
<tr><th scope="row">Unpackerr 1.0.1</th><td>Unpacking downloads</td><td>6.8</td><td>0.11</td></tr>
<tr><th scope="row">Recyclarr 8.8.1, waiting</th><td>Quality settings from the TRaSH Guides</td><td>5.2</td><td>0.00</td></tr>
</tbody>
</table>

Recyclarr does its work in short runs. One run without internet stopped after 2.4 seconds at 61 MiB; with internet
it took 17.3 seconds and peaked at 138 MiB and 82% of a core.

## Compared with 4 November 2026

The same test on 4 November 2026, on a quieter computer, gave higher figures for every app: Radarr used 163.0 MB
then and 106.3 MiB now. Reelix against the five apps it replaces was about 33 times smaller then and about 29 times
smaller now, so the gap is about the same. Treat 13 November as a fair comparison between apps, and 4 November as
closer to what a quiet computer shows.

## Find out more

- [How the tests were run](how-the-tests-were-run.md)
- [How Starboard compares with other media server stacks](how-starboard-compares.md)
- [Basics, Full install and Everything: what each one has](../topics/install-types.md)
- [What you need to run Starboard](../topics/what-you-need.md)
- [Make Starboard use less of your server](../topics/make-starboard-lighter.md)
- [What Reelix is](../basics/what-is-reelix.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
