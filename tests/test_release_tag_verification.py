"""Release updates trust only annotated tags GitHub has cryptographically verified."""
import json
import unittest

from tools.verify_release_tag import verify


class Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit):
        return json.dumps(self.payload).encode()


class ReleaseTagVerificationTest(unittest.TestCase):
    def payload(self, verified=True, reason="valid", target="b" * 40, target_type="commit"):
        return {"object": {"sha": target, "type": target_type},
                "verification": {"verified": verified, "reason": reason}}

    def test_accepts_a_verified_annotated_tag_for_the_expected_commit(self):
        payload = self.payload()
        self.assertTrue(verify("a" * 40, "b" * 40, opener=lambda request, timeout: Response(payload)))

    def test_refuses_unsigned_tags(self):
        payload = self.payload(False, "unsigned")
        with self.assertRaisesRegex(ValueError, "unsigned"):
            verify("a" * 40, "b" * 40, opener=lambda request, timeout: Response(payload))

    def test_refuses_a_valid_signature_for_a_different_commit(self):
        payload = self.payload(target="c" * 40)
        with self.assertRaisesRegex(ValueError, "does not point"):
            verify("a" * 40, "b" * 40, opener=lambda request, timeout: Response(payload))

    def test_refuses_lightweight_tag_objects(self):
        payload = self.payload(target_type="tree")
        with self.assertRaisesRegex(ValueError, "does not point"):
            verify("a" * 40, "b" * 40, opener=lambda request, timeout: Response(payload))


if __name__ == "__main__":
    unittest.main()
