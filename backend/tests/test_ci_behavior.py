"""Offline regression tests for production authentication and backchannel logic."""
import unittest
from datetime import timedelta

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    get_user_id_from_token,
    verify_password,
)
from app.services.audio.backchannel import BackchannelManager


class AuthenticationTests(unittest.TestCase):
    def test_password_hash_verifies_only_correct_password(self):
        hashed = get_password_hash("ci-test-password")
        self.assertNotEqual(hashed, "ci-test-password")
        self.assertTrue(verify_password("ci-test-password", hashed))
        self.assertFalse(verify_password("wrong-password", hashed))

    def test_access_token_round_trip(self):
        token = create_access_token("ci-user")
        self.assertEqual(get_user_id_from_token(token), "ci-user")
        self.assertEqual(decode_token(token)["type"], "access")

    def test_refresh_token_is_not_an_access_token(self):
        token = create_refresh_token("ci-user")
        self.assertEqual(decode_token(token)["sub"], "ci-user")
        self.assertEqual(decode_token(token)["type"], "refresh")
        self.assertIsNone(get_user_id_from_token(token))

    def test_expired_token_is_rejected(self):
        token = create_access_token("ci-user", timedelta(seconds=-60))
        self.assertIsNone(decode_token(token))
        self.assertIsNone(get_user_id_from_token(token))

    def test_invalid_signature_is_rejected(self):
        token = create_access_token("ci-user")
        header, payload, signature = token.split(".")
        signature = ("A" if signature[0] != "A" else "B") + signature[1:]
        self.assertIsNone(decode_token(".".join((header, payload, signature))))

    def test_malformed_token_is_rejected(self):
        self.assertIsNone(decode_token("not-a-jwt"))


class BackchannelTests(unittest.TestCase):
    def test_rotation_wraps_after_all_responses(self):
        manager = BackchannelManager()
        responses = [manager.generate_backchannel_text()
                     for _ in manager.BACKCHANNEL_TEXTS]
        self.assertEqual(responses, manager.BACKCHANNEL_TEXTS)
        self.assertEqual(manager.generate_backchannel_text(), responses[0])

    def test_random_response_is_a_known_response(self):
        manager = BackchannelManager()
        self.assertIn(manager.generate_random_backchannel(), manager.BACKCHANNEL_TEXTS)

    def test_only_responds_after_user_message(self):
        manager = BackchannelManager()
        self.assertFalse(manager.should_respond([]))
        self.assertFalse(manager.should_respond([{"role": "assistant"}]))
        self.assertFalse(manager.should_respond([{"role": "system"}]))
        self.assertFalse(manager.should_respond([{}]))
        self.assertTrue(manager.should_respond([{"role": "user"}]))
        self.assertFalse(manager.should_respond([
            {"role": "user"}, {"role": "assistant"}]))


if __name__ == "__main__":
    unittest.main()
