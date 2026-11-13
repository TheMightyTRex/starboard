[Help centre](../README.md) · Comparison tests · how-to

# How the tests were run, and how to repeat them

This page says how the comparison tests of 13 November 2026 measured each app, on what computer and under what
conditions, and how to run the same tests on your own computer. The results are in
[Memory and processor](memory-and-processor.md).

## What was measured

How much memory and processor each app uses at rest, on a fresh, empty set-up: 26 apps in all. These were Starboard,
both versions of Reelix and the On demand plug-in; the apps Reelix replaces; five other dashboards; and ten apps
people often add to a media stack. Four apps every stack shares (Jellyfin, Audiobookshelf, qBittorrent and NZBGet)
were read on a real server on the same day.

## The method

1. Each app ran from its own image, on a fresh, empty set-up in a new Docker volume.
2. Every app ran on a Docker network with no way out to the internet, so no app could fetch anything during the test.
   No app had a memory or processor limit.
3. Three apps ran at a time. Each had 120 seconds to settle.
4. Then Docker's own figures (`docker stats`) were read every 5 seconds for 3 minutes: 36 readings for each app.
5. For each app, the median and the highest of the 36 readings were kept, for memory and for processor, with its
   number of threads.
6. After each group of three, each app's log was kept, and its container and volume were removed.
7. The whole stacks were made by adding up the medians. Each stack has the same four shared apps, from the reading
   on the real server.

Every image was pulled by its exact digest, so the versions are known and can be tested again.

A few apps needed something to start at all. Homarr and Jellystat needed a made-up secret key, Jellystat needed its
own database beside it (the two are measured together), and Organizr needed internet once, to fetch its own code,
before it was measured without internet like the others.

## The computer

<table>
<caption>The computer the tests ran on</caption>
<tbody>
<tr><th scope="row">Date</th><td>13 November 2026, 13:51 to 15:50, UK time</td></tr>
<tr><th scope="row">Processor</th><td>AMD Ryzen 5 1600: 6 cores, 12 threads, up to 3.2 GHz</td></tr>
<tr><th scope="row">Memory</th><td>15.5 GiB (gibibytes), with 8 GiB of swap</td></tr>
<tr><th scope="row">Disk for Docker</th><td>A 250 GB SSD</td></tr>
<tr><th scope="row">Software</th><td>Linux 7.0, Docker 29.1.3</td></tr>
</tbody>
</table>

## The conditions, which matter

The computer was very busy. A video conversion was running the whole time, other work was building software and
testing in a browser, and the swap was full, with 3.0 to 6.7 GiB of memory free.

- **Memory figures are lower than on a quiet computer.** When memory runs short, Linux takes back file cache that
  Docker counts as an app's memory. This happened to every app, so the apps still compare fairly with each other.
- **Processor figures at rest are still fair,** because each container's own use is measured. Short peaks can look
  longer, because an app may wait for a free processor.
- **Compare apps within one run.** The same test on 4 November 2026 gave higher figures for every app. Compare
  figures from the same day, not across days.

## What the tests do not show

- **An app with a real library.** Every app started empty. With films, series and books, every app uses more.
- **Readarr.** It has no image that can be pulled, so its figures are an estimate from 4 November 2026.
- **Plex.** Plex was not part of these tests, so there are no measured figures for a stack built on Plex.
- **What happens while an app works.** Searching, importing and converting use far more than these figures.

## Repeat the tests on your own computer

The scripts are in Starboard's code, in the folder `tools/bench`, with a short
[read-me](https://github.com/TheMightyTRex/starboard/blob/main/tools/bench/README.md). They need a Linux computer with
Docker, about 75 minutes, and nothing else running in Docker named `bench-`. They touch only the containers, volumes
and network they make, and remove them at the end.

1. Download Starboard's code, and copy the three scripts into an empty folder:

   ```
   git clone --depth 1 https://github.com/TheMightyTRex/starboard.git
   mkdir -p ~/bench
   cp starboard/tools/bench/bench.sh starboard/tools/bench/*.py ~/bench
   cd ~/bench
   ```

2. Read your running apps for 3 minutes, without changing anything. This gives the figures for Jellyfin,
   Audiobookshelf, qBittorrent and NZBGet if you run them:

   ```
   ./bench.sh live
   ```

3. Download every image, then run the tests:

   ```
   ./bench.sh pull
   ./bench.sh run
   ```

   To test only some apps, name them, such as `ONLY="radarr sonarr" ./bench.sh run`.

4. Remove everything the test made:

   ```
   ./bench.sh clean
   ```

5. Turn the readings into tables:

   ```
   python3 -I summarise.py bench-results/samples.txt > bench-results/summary.tsv
   python3 -I summarise.py bench-results/samples-live.txt > bench-results/summary-live.tsv
   python3 -I stacks.py bench-results > bench-results/stacks.tsv
   ```

Open the files ending in `.tsv` in a spreadsheet. Each row is one app or one stack, with memory in MiB and processor
as a percentage of one core. Your figures will not match these: your computer, its load and the versions you test
are different. The apps should still come out in about the same order.

## Find out more

- [Memory and processor: Starboard against other stacks](memory-and-processor.md)
- [How Starboard compares with other media server stacks](how-starboard-compares.md)
- [Find out what each app is using](../topics/monitor-apps.md)
- [What Docker is](../basics/what-is-docker.md)
- [The terminal: typing commands](../basics/the-terminal.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
