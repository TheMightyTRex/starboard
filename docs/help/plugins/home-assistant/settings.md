# Home Assistant: Settings
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Home Assistant's settings are on its own tab: go to **Settings**, then **Plug-ins**, then **Home Assistant**. Starboard draws them and keeps them; secrets are never shown again once saved.

## Settings

| Setting | What it does | Default |
|---|---|---|
| **Home Assistant's address** | Such as http://192.0.2.30:8123 A web address. | Empty |
| **Long-lived access token** | In Home Assistant: your profile, Security, Long-lived access tokens, Create token. Kept by Starboard. Kept secret by Starboard: it is never shown again. | Empty |
| **What to show** | One entity id each, such as binary_sensor.front_door or sensor.lounge_temperature. One a line. | Empty |
| **Warn when any is** | States that turn the card amber, separated by commas. Words. | on, open, unlocked |

Home Assistant has no buttons. Select **Save** to keep the settings.

## Things to note

- A setting you change is used the next time the card asks, within a minute; you do not need to deactivate it first.
- **What to show** takes entity ids, exactly as Home Assistant shows them, such as `sensor.lounge_temperature`. The card shows the first 8.
- **Warn when any is** does not mind capital letters: `Open` and `open` are the same.
- It only reads states. It never changes anything in Home Assistant.
- Settings are kept when you update or deactivate it, and when you remove it they stay in its folder.

## Find out more

- [Install](../home-assistant/install.md)
- [Dashboard card](../home-assistant/dashboard-card.md)
- [Problems](../home-assistant/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
