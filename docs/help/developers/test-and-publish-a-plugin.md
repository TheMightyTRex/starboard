[Help centre](../README.md) · Developers

# Test and publish a plug-in

How to check a plug-in before anyone else adds it, pin its images, and publish it in a catalogue so people can add
it and get its updates. To build your first one, read [Make your first plug-in](make-a-plugin.md).

## Test it

The plug-in tester runs the same check Starboard runs before any plug-in is added, and more. Each issue says where
it is, what is wrong and how to fix it.

- **Errors** stop the plug-in being added.
- **Warnings** should be fixed, such as a card with no `example` or a plug-in with no `health` path.
- **Tips** are worth reading, such as a container that can reach your home network.

Accessibility is always tested: every style in light and dark, the labels and hints people read, and every card.

### In Starboard

1. Go to **Settings**, then **Plug-ins**, then **Catalogue**.
2. Under **Test a plug-in**, choose the plug-in's `starboard-plugin.json`.
3. While its images are not pinned yet, select **Allow images without a digest (while you develop it)**.
4. Select **Test it**.

### In the terminal

In a folder with Starboard's files:

```bash
python3 -m starboard.plugin_tester path/to/your-plugin
python3 -m starboard.plugin_tester --dev path/to/your-plugin
```

Give it the plug-in's folder or its `starboard-plugin.json`. `--dev` allows images without a digest, as the box does.
It ends with how many errors, warnings and tips it found, and exits with 1 when there are errors, so you can run it
in your own checks before each release.

## Development mode

Development mode is the tester's **Allow images without a digest** box, and `--dev` in the terminal. It lets you
test a manifest whose image has a tag, such as `127.0.0.1:5000/hello-card:0.1.0`, and it warns that the image is
not pinned. Adding a plug-in to Starboard always needs every image pinned by digest, even your own. A small registry
on your own server gives you a digest in a few seconds: read
[Build it and pin it by digest](make-a-plugin.md#6-build-it-and-pin-it-by-digest).

## Pin every image by digest

A tag, such as `:1.0` or `:latest`, can point at different code tomorrow. A digest is the image's own fingerprint,
so what people approved is what runs.

1. Build and push the image to a public container registry:

   ```bash
   docker build -t registry.example.invalid/sam/hello-card:0.2.0 .
   docker push registry.example.invalid/sam/hello-card:0.2.0
   ```

2. Get its digest:

   ```bash
   docker inspect --format '{{index .RepoDigests 0}}' registry.example.invalid/sam/hello-card:0.2.0
   ```

3. Put what it prints in `image`, such as
   `registry.example.invalid/sam/hello-card@sha256:7d2f4b6e8a0c1e3f5b7d9a2c4e6f8b0d1a3c5e7f9b2d4a6c8e0f1b3d5a7c9e2f`.
4. Test again without development mode. It worked when there are 0 errors.

Build each release from a tagged commit, and pin a new digest each time.

## Publish the manifest

Put the plug-in's folder somewhere people can reach, such as a public Git repository. Its manifest needs an `https`
address that gives the file itself, not a web page about it, such as a repository's raw
`starboard-plugin.json`. People can add a plug-in by that address alone. Read
[Add a plug-in by its address](../topics/add-a-plugin.md#add-a-plug-in-by-its-address).

Give each version its own address, such as a folder per version or a Git tag, so a catalogue can point at each.

## Write a catalogue

A catalogue lists your plug-ins and every version of each, so Starboard can offer the right version for each
Starboard, and offer updates. The full shape is in
[Catalogues in the Plug-in API reference](plugin-api-reference.md#catalogues).

1. Get the SHA-256 of each version's manifest, exactly as it is served:

   ```bash
   curl -sL https://example.invalid/hello-card/0.2.0/starboard-plugin.json | sha256sum
   ```

   Or, for the file on your computer, if it is byte for byte the same:

   ```bash
   sha256sum starboard-plugin.json
   ```

   The first 64 characters it prints are the SHA-256. A change of even one space, or a different line ending,
   changes it, so check the served file.

2. Write `catalogue.json`, with the newest version first:

   ```json
   {
     "name": "Sam's plug-ins",
     "plugins": [
       {
         "id": "hello-card",
         "name": "Hello card",
         "description": "Shows on your dashboard how long it has been running.",
         "kind": "System",
         "author": "Sam",
         "permissions": [],
         "versions": [
           {"version": "0.2.0", "starboard_api": ">=1.4 <2.0", "released": "2026-11-12",
            "manifest": "https://example.invalid/hello-card/0.2.0/starboard-plugin.json",
            "manifest_sha256": "9b1d3f5a7c2e4b6d8f0a1c3e5b7d9f2a4c6e8b0d1f3a5c7e9b2d4f6a8c0e1b3d",
            "changelog": "A list card of the last five starts."}
         ]
       }
     ]
   }
   ```

3. Publish it at an `https` address that gives the file itself, such as a repository's raw `catalogue.json`.
4. To release a new version, add it to `versions` with its own address and SHA-256. Leave the older ones, so
   people on an older Starboard still get the newest version that works for them.

Never change a manifest after it is listed: Starboard refuses a file whose SHA-256 does not match, and says it
changed since the catalogue listed it. Publish a new version instead.

## Add a catalogue from a link

To try your catalogue, or to add one someone else publishes:

1. Go to **Settings**, then **Plug-ins**, then **Catalogue**.
2. Under **Catalogue sources**, paste the address into **Catalogue address**.
3. Select **Add catalogue**. Starboard reads it and says how many plug-ins it lists.

Its plug-ins show in their own section, named after the catalogue. Adding a catalogue installs nothing. Starboard
reads it again at most once a day. The steps for everyone are in
[Add a catalogue from a link](../topics/add-a-plugin.md#add-a-catalogue-from-a-link).

## Before you share it

- The tester shows 0 errors without development mode, and you have read every warning.
- Every image is pinned by digest.
- `permissions` lists only what the plug-in uses. People read each one before they add it.
- `homepage` and `support_url` work, and the readme says what the plug-in does and what it sends anywhere.
- `version` follows semantic versioning: raise the first number when something stops working the old way.
- `starboard_api` names the lowest API version with everything you use. Read
  [What each API version added](plugin-manifest-reference.md#what-each-api-version-added).

## Find out more

- [Make your first plug-in](make-a-plugin.md)
- [Plug-in manifest reference](plugin-manifest-reference.md)
- [Plug-in API reference](plugin-api-reference.md)
- [Add a plug-in](../topics/add-a-plugin.md)
- [The plug-in collection](../basics/plugin-collection.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
