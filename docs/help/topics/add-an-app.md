[Help centre](../README.md) · Apps · how-to

# Add an app

Add an app to Starboard by giving it a name, the address Starboard uses to reach it and, for most apps, its
API key. At the end, the app has a card on the Apps page with its status.
Apps such as Sonarr and Radarr are also searched from the Search page.

## Before you begin

- The app is installed and running. If you have no apps yet, read [Install apps with Starboard](install-apps.md).
- You know the app's port, such as 8989 for Sonarr. Read [Addresses and ports](../basics/addresses-and-ports.md)
  if ports are new to you.
- You have the app's API key to hand. Read [Find an app's API key](find-an-api-key.md).

If the app is on the same computer as Starboard, [Search for apps already on your server](search-for-new-apps.md)
may find it and fill in these details for you.

## Steps

1. Go to **Settings**, then **Manage apps**.
2. Select **Add an app**. A side panel opens, called **Add an app**.
3. In **Kind of app**, choose the app, such as **Sonarr**. For an app that is not in the list, choose
   **Other app**.
4. In **Name**, type the name you want on its card, such as `Sonarr`.
5. In **Address Starboard uses**, type the address with `http://` and the port. For an app on the same
   computer as Starboard, use `127.0.0.1` and the app's port, such as `http://127.0.0.1:8989`. For an app on
   another computer, use that computer's address, such as `http://192.168.1.20:8989`.
6. In **API key**, paste the app's API key. The hint under the field says where the key is kept in that app.
   **Other app** has no API key field.
7. Select **Test connection**. Starboard shows **Connected**, with the app's version, when the address and key
   are right.
8. Optional: under **On the dashboard**, choose a **Category** and an **Icon**. Read
   [Organise apps into categories](organise-categories.md) and [Change an app's icon](change-an-icon.md).
9. Select **Add app**. For Sonarr, Radarr, Lidarr and Readarr the button is **Save and continue** instead,
   and the panel moves on to **Adding options**.

### Adding options for Sonarr, Radarr, Lidarr and Readarr

Starboard uses these choices when you add a film, series, album or book from the Search page.

1. In **Quality profile**, choose the profile to use. The list comes from the app itself.
2. In **Folder**, choose the folder new items go in.
3. For Lidarr and Readarr, choose a **Metadata profile**.
4. Leave **Search as soon as something is added** on if you want the app to look for it straight away.
5. Select **Save adding options**. To choose later, select **Skip for now**: Starboard then uses the first in
   each list.

## Things to note

- Starboard uses your computer's own network, so Docker container names, such as `http://sonarr:8989`,
  usually do not work. Use `127.0.0.1` and the port instead.
- Starboard keeps API keys on the server and never sends them to your browser. When you edit an app later, the
  **API key** field is empty: leave it empty to keep the saved key.
- An app saved with `127.0.0.1` still opens from a phone. Starboard swaps in the address you opened Starboard
  with. To open it with a different address, fill in **Address to open in your browser**.
- **Outside address** is for an address that works away from home, such as your own domain. It is optional.
- An app with no web page of its own, such as a VPN (virtual private network), is a background service. Read
  [Add a background service](add-a-background-service.md).

## If it does not work

- **Cannot connect:** check the port and that the address starts with `http://`. Open the address in your
  browser on the server to check the app is running.
- **The address must start with http:// or https://:** add `http://` to the start of the address.
- **The key is refused:** copy the API key again from the app. Read [Find an app's API key](find-an-api-key.md).
- **Could not load the profiles and folders:** the app did not answer with its lists. Select **Skip for now**,
  check the app is running, then edit the app again.

## Find out more

- [Change or remove an app](change-or-remove-an-app.md)
- [Search for apps already on your server](search-for-new-apps.md)
- [Set up your dashboard after installing](../guides/set-up-your-dashboard.md)
- [What an API key is](../basics/what-is-an-api-key.md)
- [The apps Starboard works with](../basics/the-apps.md)
