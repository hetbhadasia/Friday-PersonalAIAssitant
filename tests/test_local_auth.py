import tempfile
import sqlite3
import unittest
from pathlib import Path

from friday.core.local_auth import LocalAuthStore


class LocalAuthStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = LocalAuthStore(str(Path(self.temp_dir.name) / "auth.sqlite3"))

    def tearDown(self):
        self.temp_dir.cleanup()

    def create_account(self, identifier="person@example.com"):
        self.store.save_otp("email", identifier, "signup", "012345")
        session = self.store.verify_otp("email", identifier, "signup", "012345")
        self.assertIsNotNone(session)
        return session

    def test_signup_signin_and_access_token_validation(self):
        signup = self.create_account()
        self.assertEqual(signup["user"]["email"], "person@example.com")
        self.assertEqual(
            self.store.validate_access_token(signup["access_token"])["id"],
            signup["user"]["id"],
        )

        self.store.save_otp("email", "person@example.com", "signin", "123456")
        signin = self.store.verify_otp("email", "person@example.com", "signin", "123456")
        self.assertEqual(signin["user"]["id"], signup["user"]["id"])

    def test_invalid_code_is_limited_and_consumed(self):
        self.store.save_otp("email", "person@example.com", "signup", "012345")
        for _ in range(5):
            self.assertIsNone(
                self.store.verify_otp("email", "person@example.com", "signup", "999999")
            )
        self.assertIsNone(
            self.store.verify_otp("email", "person@example.com", "signup", "012345")
        )

    def test_refresh_rotates_tokens(self):
        session = self.create_account()
        refreshed = self.store.refresh_session(session["refresh_token"])
        self.assertIsNotNone(refreshed)
        self.assertIsNone(self.store.refresh_session(session["refresh_token"]))
        self.assertEqual(
            self.store.validate_access_token(refreshed["access_token"])["id"],
            session["user"]["id"],
        )

    def test_conversations_are_isolated_by_user(self):
        first = self.create_account("first@example.com")
        second = self.create_account("second@example.com")
        conversation_id = "12345678-1234-1234-1234-123456789abc"
        messages = [{"id": "m1", "role": "user", "text": "Hi", "timestamp": "2026-01-01T00:00:00Z"}]

        self.assertTrue(
            self.store.save_conversation(
                first["user"]["id"], conversation_id, "Chat", "2026-01-01T00:00:00Z", messages
            )
        )
        self.assertFalse(
            self.store.save_conversation(
                second["user"]["id"], conversation_id, "Changed", "2026-01-02T00:00:00Z", messages
            )
        )
        self.assertEqual(len(self.store.list_conversations(first["user"]["id"])), 1)
        self.assertEqual(self.store.list_conversations(second["user"]["id"]), [])

    def test_verified_google_name_is_saved_and_returned_in_sessions(self):
        session = self.store.login_with_verified_email("google@example.com", "Google User")
        self.assertEqual(session["user"]["name"], "Google User")
        validated_user = self.store.validate_access_token(session["access_token"])
        self.assertEqual(validated_user["name"], "Google User")
        refreshed = self.store.refresh_session(session["refresh_token"])
        self.assertEqual(refreshed["user"]["name"], "Google User")

    def test_existing_auth_database_is_migrated_for_display_name(self):
        database_path = Path(self.temp_dir.name) / "old-auth.sqlite3"
        with sqlite3.connect(database_path) as connection:
            connection.execute(
                """
                CREATE TABLE auth_users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE,
                    phone TEXT UNIQUE,
                    created_at INTEGER NOT NULL
                )
                """
            )
        migrated_store = LocalAuthStore(str(database_path))
        session = migrated_store.login_with_verified_email(
            "existing@example.com", "Existing User"
        )
        self.assertEqual(session["user"]["name"], "Existing User")


if __name__ == "__main__":
    unittest.main()
