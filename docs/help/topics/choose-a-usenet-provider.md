[Help centre](../README.md) · Apps · how-to

# Choose a Usenet provider and add it

NZBGet, or SABnzbd if you chose it, downloads from Usenet. To use it, you need an account with a Usenet provider,
then you add the provider's server to NZBGet or SABnzbd. Usenet is a worldwide network of discussion groups,
running since 1980, that also carries files. Any provider works with NZBGet and SABnzbd.

## Before you begin

- Install apps has set up NZBGet or SABnzbd. Read [Install apps with Starboard](install-apps.md).
- You have decided you need Usenet. Torrents through qBittorrent need no account.

## Usenet providers

Ad: these are affiliate links. If you sign up through one, the provider pays a small commission towards
Starboard's development. You pay the same price.

| Provider | Link |
|---|---|
| Newshosting | [Newshosting](https://www.newshosting.com/?a_aid=6aec3d712dec1) |
| Easynews | [Easynews](https://easynews.com/?a_aid=6aec3d712dec1) |
| UsenetServer | [UsenetServer](https://www.usenetserver.com/?a_aid=6aec3d712dec1&a_bid=ef245116) |
| Pure Usenet | [Pure Usenet](https://www.pureusenet.nl/?a_aid=6aec3d712dec1&a_bid=9fa99e6a) |
| XLned | [XLned](https://www.xlned.com/?a_aid=6aec3d712dec1&a_bid=dbc287fb) |

Compare what each offers on its own site before you choose: how many connections, how long files are kept
(retention) and the price.

## Steps

1. Choose a provider and make an account on its site. Keep the details it gives you: the server address, the
   port (563 for an encrypted connection), your user name, your password and how many connections you may use.
2. Open NZBGet from your dashboard. It asks for its sign-in: the user name is `starboard`, and the password is
   `NZBGET_PASS` in `data/stack/.env` in the Starboard folder.
3. Select **Settings**, then **News-Servers**, then **Server1**.
4. Fill in **Host**, **Port**, **Username** and **Password**, set **Encryption** to **Yes** and **Connections** to
   the number your provider allows.
5. Select **Save all changes** at the bottom of the menu, then **Reload**.

### If you use SABnzbd

1. Open SABnzbd from your dashboard.
2. Select **Config**, then **Servers**, then **Add Server**.
3. Fill in the same details, tick **SSL**, then select **Test Server** and **Add Server**.

Reelix already sends downloads to NZBGet or SABnzbd. Nothing else needs to change.

## Things to note

- Changing from SABnzbd to NZBGet in **Settings**, **Apps**, **Your install** moves your servers across. Read
  [Change your install](change-your-install.md).
- Downloads go through your VPN, as torrents do.
- Download only what you have the right to: see the note at the bottom of this page.

## If it does not work

- **NZBGet says the server refused the sign-in:** check the user name and password with the provider's site.
- **Downloads are slow or stop:** lower **Connections** to the number your plan includes.

## Find out more

- [Install apps with Starboard](install-apps.md)
- [Change your install](change-your-install.md)
- [Basics, Full install and Everything: what each one has](install-types.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
