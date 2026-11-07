[Help centre](../README.md) · Apps · how-to

# Switch between the two versions of Reelix

Reelix comes in two versions. **Reelix** looks after films, series, books, audiobooks, music and radio, and is the
smaller download. **Reelix with YouTube and Spotify downloads** does all of that and can also download straight from
YouTube and Spotify. It takes about 600 MB more disk. You can switch either way at any time. Both versions use the
same settings folder, so your library, users and settings stay as they are.

## Before you begin

- Reelix was installed by [Install apps](install-apps.md). For a Reelix you set up yourself, change its image in
  your own Compose file instead: `ghcr.io/themightytrex/reelix:lite` for Reelix, or
  `ghcr.io/themightytrex/reelix:full` for the version with YouTube and Spotify downloads.
- You know your Starboard password.

## Steps

1. Go to **Settings**, then **Apps**, then **Reelix**.
2. Under **Version**, choose the version you want. **In use now** marks the one that runs.
3. Type **Your password**, then select **Switch to** and the version's name.
4. Wait until Starboard shows that the version is running. Reelix is unavailable for a minute or two while the new
   version downloads and starts.

### If Starboard has no Docker access

Starboard changes the version, then shows **One step on the server**. Select **Copy the command**, then paste it into
a terminal on the server:

```bash
cd ~/starboard && ./install.sh --start-apps
```

If the Run first window is still open, Starboard asks it to start Reelix instead, and you do not need the command.

## Things to note

- Starboard keeps the old set-up file next to the new one in `data/stack`, named `compose.yaml.before-` and the date.
- Both versions come from the same place, TheMightyTRex's copy of Reelix, so they have the same fixes. If the version
  with YouTube and Spotify downloads cannot be downloaded from there, Starboard uses Reelix's own.
- Reelix updates its database when a newer release starts, and an older release cannot read it afterwards. So
  Starboard does not switch to a version that is behind the one you run. Reelix follows each release within a day.

## If it does not work

- **Cannot be downloaded at the moment:** neither source for that version can be downloaded now. Try again later,
  or keep the version you have.
- **It cannot go back to an older version:** the other version is behind. Try again the next day.
- **Reelix was not installed here by Starboard:** change the image in your own Compose file, as in Before you begin.
- **Reelix did not start:** read the details Starboard shows. To go back, switch to the version you had.

## Find out more

- [Install apps with Starboard](install-apps.md)
- [Update your apps](update-your-apps.md)
