#!/usr/bin/env python3
"""Verify an annotated release tag using GitHub's cryptographic signature-verification result."""
import json
import sys
import urllib.error
import urllib.request

REPOSITORY = "TheMightyTRex/starboard"


def verify(tag_object, expected_commit, opener=urllib.request.urlopen):
    if not tag_object or not expected_commit:
        raise ValueError("A tag object and its target commit are required")
    url = f"https://api.github.com/repos/{REPOSITORY}/git/tags/{tag_object}"
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "Starboard-release-verifier",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with opener(request, timeout=10) as response:
            tag = json.loads(response.read(256 * 1024))
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
        raise ValueError(f"GitHub could not verify the release tag: {error}") from None
    target = tag.get("object") or {}
    verification = tag.get("verification") or {}
    if target.get("type") != "commit" or target.get("sha") != expected_commit:
        raise ValueError("The signed tag does not point to the commit Starboard fetched")
    if verification.get("verified") is not True or verification.get("reason") != "valid":
        reason = verification.get("reason") or "no signature"
        raise ValueError(f"GitHub did not verify this release tag ({reason})")
    return True


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print("Usage: verify_release_tag.py TAG_OBJECT_SHA COMMIT_SHA", file=sys.stderr)
        return 2
    try:
        verify(argv[0], argv[1])
    except ValueError as error:
        print(f"Release signature check failed: {error}", file=sys.stderr)
        return 1
    print("GitHub verified the signed release tag.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
