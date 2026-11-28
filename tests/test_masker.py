"""The core masker (DASH-655): what it hides, what it leaves, and fuzzing of every class it hides. A fixed seed makes the
random cases repeatable; MASKER_FUZZ=n runs n times as many."""
import os
import random
import secrets
import string
import time
import unittest

from starboard import api_v1, masker

ROUNDS = 300 * int(os.environ.get("MASKER_FUZZ", "1"))
ZERO = "\u200b\u200c\u200d\u2060\ufeff\u00ad"


def word(rng, n=None):
    return "".join(rng.choice(string.ascii_lowercase) for _ in range(n or rng.randint(4, 9)))


def key_value(rng):
    kind = rng.randrange(7)
    if kind == 0:
        return f"sb_read_{secrets.token_hex(3)}_{secrets.token_urlsafe(32)}"
    if kind == 1:
        return secrets.token_urlsafe(rng.randint(18, 48))
    if kind == 2:
        return secrets.token_hex(rng.randint(12, 40))
    if kind == 3:
        return "eyJ" + secrets.token_urlsafe(20) + "." + secrets.token_urlsafe(30) + "." + secrets.token_urlsafe(20)
    if kind == 4:
        return rng.choice(["sk-", "ghp_", "xoxb-", "AKIA", "AIza", "ya29."]) + secrets.token_urlsafe(24)
    if kind == 5:
        return "".join(rng.choice(string.ascii_letters + string.digits) for _ in range(rng.randint(24, 60)))
    return secrets.token_urlsafe(30).replace("-", "A").replace("_", "b")


def address_value(rng):
    kind = rng.randrange(6)
    if kind == 0:
        return f"192.168.{rng.randint(0, 255)}.{rng.randint(2, 254)}" + rng.choice(["", f":{rng.randint(80, 65535)}"])
    if kind == 1:
        return f"{rng.randint(11, 99)}.{rng.randint(0, 255)}.{rng.randint(0, 255)}.{rng.randint(1, 254)}"
    if kind == 2:
        return ":".join(f"{rng.randint(0, 65535):x}" for _ in range(8))
    if kind == 3:
        return f"2001:db8::{rng.randint(1, 65535):x}:{rng.randint(1, 65535):x}"
    if kind == 4:
        return ":".join(f"{rng.randint(0, 255):02x}" for _ in range(6))
    return f"{word(rng)}.{word(rng)}.ts.net"


def host_value(rng):
    return rng.choice([f"{word(rng)}.local", f"{word(rng)}.{word(rng)}.ts.net", f"{word(rng)}.example.com", f"nas-{word(rng)}.lan",
                       f"{word(rng)}.duckdns.org", f"{word(rng)}.home.arpa"])


def path_value(rng):
    parts = [word(rng, rng.randint(5, 10)) + rng.choice(["", "", " " + word(rng, 6)]) for _ in range(rng.randint(2, 5))]
    kind = rng.randrange(4)
    if kind == 0:
        return "/mnt/" + "/".join(parts) + "/" + word(rng, 6) + ".mkv"
    if kind == 1:
        return "/home/" + "/".join(parts)
    if kind == 2:
        return "C:\\Users\\" + "\\".join(p.replace(" ", "") for p in parts) + "\\" + word(rng, 6) + ".mkv"
    return "/srv/" + "/".join(parts)


def email_value(rng):
    return f"{word(rng)}.{word(rng)}@{word(rng)}.{rng.choice(['com', 'co.uk', 'org', 'net'])}"


FRAMES = [
    "{v}", "error: {v} was refused", "({v})", "<{v}>", "'{v}'", '"{v}"', "[{v}]", "key={v}", "a {v}, then more", "line one\n{v}\nline three",
    '{{"x": "{v}"}}', "GET /x?token={v} HTTP/1.1", "from {v}.", "{v}: failed", "at {v}; next", "tab\t{v}\tend",
]


def frame(rng, v):
    return rng.choice(FRAMES).replace("{{", "{").replace("}}", "}").replace("{v}", v)


def sprinkle(rng, v):
    """The value with an invisible character put inside it, which a plain pattern would miss."""
    i = rng.randint(1, len(v) - 1)
    return v[:i] + rng.choice(ZERO) + v[i:]


class MaskerTest(unittest.TestCase):
    def test_what_it_hides_and_what_it_leaves(self):
        text, counts = masker.mask("Radarr failed: connect to 192.168.1.20:7878 timed out at 12:34:56 on 2026-11-28 (v4.0.8.1874)")
        self.assertEqual(text, "Radarr failed: connect to [address 1] timed out at 12:34:56 on 2026-11-28 (v4.0.8.1874)")
        self.assertEqual(counts, {"address": 1})
        for same in ("Sonarr 3.0.10.1234 is up", "version 10.9.11.0", "Disk 83% full, 120 GB free", "Movie.Name.2020.1080p.mkv",
                     "http://localhost:8095/api/v1/status", "GET /api/v1/mcp 200", "e.g. a note, i.e. words and/or more"):
            self.assertEqual(masker.mask(same)[0], same, same)

    def test_a_field_named_version_keeps_a_number_that_looks_like_an_address(self):
        out, counts = masker.mask_value({"apps": [{"name": "Jellyfin", "version": "10.9.11.0", "note": "10.9.11.0"}]})
        self.assertEqual(out["apps"][0]["version"], "10.9.11.0")
        self.assertEqual(out["apps"][0]["note"], "[address 1]")  # anywhere else it is hidden

    def test_the_same_value_has_the_same_number_inside_one_answer(self):
        text, _ = masker.mask("from 192.0.2.5 to 192.0.2.6 and back to 192.0.2.5")
        self.assertEqual(text, "from [address 1] to [address 2] and back to [address 1]")
        again, _ = masker.mask("only 192.0.2.6")
        self.assertEqual(again, "only [address 1]")  # numbers do not carry from one answer to the next

    def test_keys_are_removed_without_a_number(self):
        key = f"sb_read_ab12cd_{secrets.token_urlsafe(32)}"
        text, counts = masker.mask(f"Authorization: Bearer {key} and again {key}")
        self.assertNotIn(key[-20:], text)
        self.assertNotIn("Bearer sb_", text)
        self.assertGreaterEqual(counts["key"] + counts.get("secret", 0), 1)

    def test_private_words_are_hidden_in_any_case(self):
        text, counts = masker.mask("Scan of Bob's Film Palace ended; BOB'S FILM PALACE is slow", ["Bob's Film Palace"])
        self.assertEqual(text, "Scan of [name 1] ended; [name 1] is slow")
        self.assertEqual(counts, {"name": 2})

    def test_common_words_are_not_treated_as_private(self):
        self.assertEqual(masker.mask("The media server is on", ["media", "server", "the"])[0], "The media server is on")

    def test_folders_and_files_with_spaces(self):
        text, _ = masker.mask("Import failed: /mnt/pool/Films/Some Private Film (2020)/Some Private Film.mkv could not be read")
        self.assertNotIn("Private", text)
        self.assertNotIn("pool", text)
        self.assertIn("could not be read", text)
        self.assertNotIn("Users", masker.mask("C:\\Users\\Alex\\Videos\\clip.mkv")[0])

    def test_urls_keep_only_the_scheme_and_the_api_path(self):
        self.assertEqual(masker.mask("see http://user:pw@nas.example.com:8095/api/v1/status now")[0], "see http://[host 1]/api/v1/status now")

    def test_a_secret_state_word_is_kept_but_a_value_is_not(self):
        self.assertEqual(masker.mask("token: expired")[0], "token: expired")
        self.assertNotIn("hunter2", masker.mask("password: hunter2")[0])
        self.assertNotIn("dragon", masker.mask("password=dragon")[0])
        self.assertNotIn("abc123", masker.mask('{"api_key": "abc123"}')[0])

    def test_invisible_characters_cannot_split_a_key(self):
        key = f"sb_read_ab12cd_{secrets.token_urlsafe(32)}"
        split = key[:12] + "\u200b" + key[12:30] + "\u2060" + key[30:]
        self.assertNotIn(key[14:30], masker.mask(f"key {split} end")[0])
        wide = "ｓｂ_read_ab12cd_" + secrets.token_urlsafe(32)  # full-width letters fold to ordinary ones
        self.assertNotIn(wide[12:], masker.mask(wide)[0])

    def test_long_text_is_cut_at_a_space_not_inside_a_key(self):
        key = secrets.token_urlsafe(40)
        out = masker.mask("a " * (masker.LIMIT // 2 - 10) + key)[0]
        self.assertNotIn(key[:10], out)
        self.assertLessEqual(len(out), masker.LIMIT + 10)

    def test_values_are_masked_inside_json_and_secret_names_are_dropped(self):
        out, counts = masker.mask_value({"a": ["x@y.example", {"api_key": "zzz", "n": 5, "ok": True, "none": None}], "b": "plain"}, drop=api_v1.SECRET_NAMES)
        self.assertEqual(out, {"a": ["[email 1]", {"n": 5, "ok": True, "none": None}], "b": "plain"})
        self.assertEqual(counts, {"email": 1})

    # Fuzzing --------------------------------------------------------------------------------------------------------

    def assert_hidden(self, secret, text, masked):
        clean = "".join(c for c in secret if c not in ZERO)
        self.assertNotIn(clean, masked, f"left in the answer: {text!r} gave {masked!r}")

    def fuzz(self, make, minimum=1):
        rng = random.Random(f"{self.id()}")
        for _ in range(ROUNDS):
            v = make(rng)
            text = frame(rng, v)
            self.assert_hidden(v, text, masker.mask(text)[0])
            if len(v) > 12 and rng.random() < 0.3:  # the same value with an invisible character inside it
                text = frame(rng, sprinkle(rng, v))
                self.assert_hidden(v, text, masker.mask(text)[0])

    def test_fuzz_keys_and_tokens(self):
        self.fuzz(key_value)

    def test_fuzz_addresses(self):
        self.fuzz(address_value)

    def test_fuzz_hosts_in_web_addresses(self):
        rng = random.Random("hosts")
        for _ in range(ROUNDS):
            host = host_value(rng)
            for text in (f"https://{host}/x", f"http://{host}:8095/api/v1/mcp", f"connect {host} failed", f"user@{host}"):
                self.assert_hidden(host, text, masker.mask(text)[0])

    def test_fuzz_emails(self):
        self.fuzz(email_value)

    def test_fuzz_paths_and_folder_names(self):
        rng = random.Random("paths")
        for _ in range(ROUNDS):
            path = path_value(rng)
            text = frame(rng, path)
            out = masker.mask(text)[0]
            for part in path.replace("\\", "/").split("/")[2:]:
                token = part.split(" ")[0]
                if len(token) >= 5 and not token.endswith(".mkv"):
                    self.assertNotIn(token, out, f"{text!r} gave {out!r}")

    def test_fuzz_private_words(self):
        rng = random.Random("words")
        for _ in range(ROUNDS):
            name = " ".join(word(rng, rng.randint(4, 8)).capitalize() for _ in range(rng.randint(1, 3)))
            text = frame(rng, name if rng.random() < 0.5 else name.upper())
            self.assertNotIn(name.lower(), masker.mask(text, [name])[0].lower(), text)

    def test_fuzz_mixed_text_never_fails_and_masking_twice_is_the_same(self):
        rng = random.Random("mixed")
        for _ in range(ROUNDS):
            parts = [frame(rng, make(rng)) for make in (key_value, address_value, email_value, path_value, host_value) if rng.random() < 0.7]
            text = " ".join(parts + [word(rng) for _ in range(rng.randint(0, 5))])
            once = masker.mask(text)[0]
            self.assertEqual(masker.mask(once)[0], once, text)

    def test_fuzz_random_characters_never_raise(self):
        rng = random.Random("noise")
        pool = string.printable + "".join(chr(c) for c in range(0x80, 0x400)) + ZERO + "\u202e\u0301\U0001f600\x00\x1b"
        for _ in range(ROUNDS):
            text = "".join(rng.choice(pool) for _ in range(rng.randint(0, 400)))
            out, counts = masker.mask(text)
            self.assertIsInstance(out, str)
            self.assertNotIn("\u200b", out)
            self.assertNotIn("\x00", out)

    def test_hostile_long_text_is_fast(self):
        start = time.time()
        for bad in ("a" * 500_000, "a." * 250_000, "/a" * 250_000, "1." * 250_000, "x:" * 250_000, "C:\\" + "a\\" * 150_000,
                    "k=" * 250_000, "/" + "a b " * 150_000, "a" * 100 + "@" * 100_000, "http://" + "a" * 200_000):
            masker.mask(bad)
        self.assertLess(time.time() - start, 8, "a pattern takes quadratic time on long text")


if __name__ == "__main__":
    unittest.main()
