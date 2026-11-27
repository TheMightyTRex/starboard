# UPS and power: Dashboard card
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

UPS and power adds 3 cards you can put on your dashboard. Each starts with a band: UPS and power's logo and name and a status in words. A footer says when it last changed. The cards only read what the plug-in kept at its last reading, so opening the dashboard never asks the UPS.

## Power

Shows one line: on mains power or on battery, with the battery charge, the time left and the load.

- **How often it updates:** once a minute while the dashboard is open. Nothing is asked while the browser tab is hidden.
- **Example:** On mains power: battery 100%, about 42 minutes left, load 23%.

![The Power card in the light theme: the band with UPS and power's logo and On mains power, and the battery, time left and load](../../images/plugins/ups-power/dashboard-card-2-light.png)

## UPS details

Shows the UPS's name and model, its status, the battery charge, the time left, the load, and the voltage in and out. It also shows the power used and the last time the power switched. It shows whichever of these the UPS reports.

- **How often it updates:** every 5 minutes while the dashboard is open.
- **Example:**
  - Battery: 100%
  - Time left on battery: 42 minutes
  - Load: 23%

## Load and battery

Shows a small line chart for the load, the battery charge and the time left, one point every 5 minutes for the last 8 hours.

- **How often it updates:** every 5 minutes while the dashboard is open.
- **Example:** Load: Latest 23%.

![The Load and battery card: a line for the load and one for the battery](../../images/plugins/ups-power/dashboard-card-3-history.png)

## What the status says

| Status | Means |
|---|---|
| **On mains power** | The UPS is on mains power and its battery is fine. |
| **On battery** | The mains power has gone and the UPS is running on its battery. |
| **Low battery** | On battery, with the charge or the time left under the limits you chose, or the UPS says so. |
| **Replace the battery** | The UPS says its battery needs replacing. |
| **Last reading failed** | The last reading could not reach the UPS, but an earlier one worked. The card says why. |
| **Cannot read it** | The UPS has never answered. The card says why, such as that nothing is listening at that address. |
| **Needs setting up** | No address is saved yet. |
| **Scheduled** | Saved, and waiting for the first reading, which comes within a minute. |

## Add it to your dashboard

1. Select **Edit dashboard**.
2. In **Add a card**, choose the card. Its name ends with (UPS and power), such as **Power (UPS and power)**.
3. Select **Save**.

![Edit dashboard, with Power (UPS and power) chosen in Add a card (step 2) and Save (step 3) outlined](../../images/plugins/ups-power/dashboard-card-1-add.png)

UPS and power must be added and active first. Read [Install](../ups-power/install.md).

## Find out more

- [Use and change the dashboard, in Starboard's help](../../topics/use-the-dashboard.md)
- [Settings](../ups-power/settings.md)
- [Problems](../ups-power/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
