[Help centre](../README.md) · Developers

# What the API covers

Every page action in Starboard, and how another app, a script or an AI assistant reaches it: an address in the API
with the right a key needs, an action kept for a person signed in to Starboard, or one not in the API yet. Use it
to see whether what you want to build is possible with a key, and which right and scope to give that key.

- **read:** any key with the scope. **manage:** a key made with **Read and manage**. Read
  [Authentication and keys](api-authentication.md).
- **Signed in only:** a person must do it in Starboard. These actions change settings, keys, plug-ins or the install,
  call an address someone types, use a password, or could lock the owner out, so no key can do them.
- **Not yet:** possible later, as its own decision.

Every address starts with `/api/v1`. The [API reference](api-reference.md) gives each one in full.

## Apps

| What a person can do | In the API | Right and scope |
|---|---|---|
| See each app, whether it answers, and its problems | `GET /apps`, `/apps/{id}`, `/status`, `/health` | read, `apps` |
| See uptime, counts from each app and app updates | `GET /uptime`, `/numbers`, `/app-updates` | read, `apps` |
| See containers and versions; look for newer images | `GET /containers`; `POST /containers/check` | read and manage, `apps` |
| Update chosen apps | Signed in only: it pulls images and restarts containers | |
| Add, edit, test, find or remove an app; copy settings | Signed in only: it stores app keys and calls the address typed | |
| Reorder apps and categories | Not yet | |

## Downloads, requests and Coming up

| What a person can do | In the API | Right and scope |
|---|---|---|
| See the queue, speeds and Reelix's history | `GET /downloads`, `/transfer`, `/history` | read, `downloads` |
| Remove, block, or block and search again | `POST /downloads/actions` | manage, `downloads` |
| See download hours; resume, pause or follow them | `GET /download-hours`; `POST /download-hours` | read and manage, `downloads` |
| See requests; approve or decline | `GET /requests`; `POST /requests/{id}/approve`, `/decline` | read and manage, `requests` |
| See Coming up, as a list or a month | `GET /calendar`, `?month=` | read, `media` |
| Search the apps and add to one | Not yet | |

## Library and media

| What a person can do | In the API | Right and scope |
|---|---|---|
| See the Library's counts and recently added; search it | `GET /library`, `/library/search` | read, `library` |
| See each tab's index; build a tab again | `GET /library/status`; `POST /library/refresh` | read and manage, `library` |
| See recently added and what is playing | `GET /recent`, `/playing` | read, `media` |
| See the Jellyfin and Audiobookshelf jobs; run one now | `GET /extras`; `POST /extras/{name}/run` | read and manage, `media` |
| Add a title to Reelix, change or delete one, saved views | Not yet | |
| Import watch history or listening progress from an address | Signed in only: it calls the address typed | |

## System

| What a person can do | In the API | Right and scope |
|---|---|---|
| See processor, memory, disks and their history | `GET /system`, `/system/history` | read, `system` |
| See the version and the newest release | `GET /version` | read, `system` |
| Send a test alert | `POST /alerts/test` | manage, `system` |
| Events as they happen: apps down and up, alerts, new items, finished downloads, playback | `GET /events` | read, by each event's scope |
| Logs, jobs, storage, disk health and the pool | Not yet: logs can hold addresses and names | |
| Back up, restore, the pool's plan, server jobs | Signed in only: they need the password or run as root | |

## Settings and security

| What a person can do | In the API | Right and scope |
|---|---|---|
| Change General, Alerts, Performance or Jellyfin settings | Signed in only | |
| Make or revoke API keys; add, update or remove plug-ins | Signed in only | |
| Password, Sign out everywhere, who can open the dashboard | Signed in only | |
| Reelix's settings, editions and moving apps into Reelix | Signed in only: they use Reelix's admin password | |
| Your install, Install apps, taking over and rolling back | Signed in only: they change what runs on the server | |
| Upgrade Starboard or reset the password | On the server only, with `./update.sh` or `./reset-password.sh` | |

## Find out more

- [Authentication and keys](api-authentication.md)
- [API reference](api-reference.md)
- [API changelog](api-changelog.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
