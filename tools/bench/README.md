# Idle benchmark

The scripts behind the help centre's comparison tests
([How the tests were run](../../docs/help/comparisons/how-the-tests-were-run.md)). They measure how much memory and
processor each app uses when it is idle, then add the apps up into whole stacks.

- `bench.sh` starts each app on a fresh, empty config in its own Docker volume, on a Docker network with no way out
  to the internet, three apps at a time. After 120 seconds to settle it reads `docker stats` every 5 seconds for
  180 seconds (36 readings), keeps each container's log, then removes the containers and volumes.
- `summarise.py` turns the readings into one row per container: the median and highest memory and processor, and the
  number of threads.
- `stacks.py` adds the rows up into whole stacks: Starboard with Reelix, a classic stack of Radarr, Sonarr, Lidarr,
  Readarr, Prowlarr and Jellyseerr, and the same with a dashboard and common add-ons.

## Before you begin

- A Linux computer with Docker, and about 75 minutes. Three apps run at a time; the largest measured, Kavita, reached
  361 MiB on its own.
- Every container, volume and the network the script makes are named `bench-...`. It touches nothing else.
- The other apps' images are pinned by digest, as measured on 13 November 2026. Starboard and Reelix are pulled by
  tag, so the newest release is measured.

## Run it

```
git clone --depth 1 https://github.com/TheMightyTRex/starboard.git
mkdir -p ~/bench
cp starboard/tools/bench/bench.sh starboard/tools/bench/*.py ~/bench
cd ~/bench
./bench.sh live        # read every running container for 3 minutes, without changing anything
./bench.sh pull        # pull every image
./bench.sh run         # all the apps, three at a time (about 75 minutes)
./bench.sh recyclarr   # time one Recyclarr run
./bench.sh clean       # remove every bench- container and volume, and the bench network
python3 -I summarise.py bench-results/samples.txt > bench-results/summary.tsv
python3 -I summarise.py bench-results/samples-live.txt > bench-results/summary-live.tsv
python3 -I stacks.py bench-results > bench-results/stacks.tsv
```

`./bench.sh live` needs Jellyfin, Audiobookshelf, qBittorrent and NZBGet running on your computer for the whole
stack totals. If one of them is not running, `stacks.py` leaves it out of every stack and says so.

## Settings

| Setting | What it does | Default |
|---|---|---|
| `OUT` | The folder for the results | `bench-results` in the current folder |
| `SETTLE` | Seconds each app has to settle before the readings | 120 |
| `SAMPLES` | Readings per app, 5 seconds apart | 36 |
| `ONLY` | Run only these apps, such as `ONLY="radarr sonarr"` | every app |
| `START` | Begin at this entry of the list, counting from 0 | 0 |
| `STARBOARD_IMAGE` | Starboard's image | `ghcr.io/themightytrex/starboard` |
| `REELIX_FULL_IMAGE`, `REELIX_LITE_IMAGE` | Reelix's two images | `ghcr.io/themightytrex/reelix:full` and `:lite` |
| `ON_DEMAND_IMAGE` | The On demand plug-in's image; it is measured only when this is set | not set |

To test a newer version of another app, change its digest in the `APPS` list at the top of `bench.sh`.

## What it does not measure

- Apps with a real library. Every app starts empty, so this is the cost of an idle app. Memory with a real library is
  higher for every app.
- Readarr. It has no image that can be pulled, so `stacks.py` uses the estimate from 4 November 2026 (about 120 MB
  and 0.07% of a core).
- Figures from another day. Docker's memory figure includes some file cache, and a busy computer gives some of it
  back, so compare apps measured in the same run, not figures from different days.
