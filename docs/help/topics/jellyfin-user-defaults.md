[Help centre](../README.md) · Jellyfin and Audiobookshelf · how-to

# Give every Jellyfin user the same defaults

Starboard can give every Jellyfin user the same starting choices, and new users get them too. For now there
is one default: Live TV opens on the Guide.

## Before you begin

- Jellyfin is on your dashboard with its API key. Read [Add an app](add-an-app.md) and
  [Find an app's API key](find-an-api-key.md).

## Steps

1. Go to **Settings**, then **Apps**, then **Jellyfin**.
2. In **User defaults**, activate **Give every Jellyfin user the defaults**.
3. To apply them straight away, select **Run Defaults now**. Otherwise, Starboard applies them within the
   hour.

Starboard shows **Last run worked** and what it did.

## Things to note

- Starboard checks every hour, so people you add to Jellyfin later get the defaults too.
- A user who has chosen something else in Jellyfin keeps their own choice.
- Deactivate the switch to stop. Choices already given stay as they are, and each person can change their own
  in Jellyfin.
- The hourly check makes two small requests to Jellyfin for each user, which is not noticeable.

## If it does not work

- **"Add Jellyfin first":** Starboard has no Jellyfin app with an API key. Select **Manage apps** in the
  message and add the key. Read [Change or remove an app](change-or-remove-an-app.md).
- **"Last run failed":** read the reason next to it, then read
  [An app shows as not responding](app-not-responding.md).

## Find out more

- [Set up free Live TV in Jellyfin](set-up-live-tv.md)
- [Import watch history into Jellyfin](import-watch-history.md)
- [Read the log and report a problem](read-the-log.md)
