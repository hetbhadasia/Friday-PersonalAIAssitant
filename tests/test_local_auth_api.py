import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from aiohttp.test_utils import TestClient, TestServer

import token_server
from friday.core.local_auth import LocalAuthStore


def config_with_database(database):
    base_config = token_server.config

    class ConfigProxy:
        def __getattr__(self, name):
            if name == "database":
                return database
            return getattr(base_config, name)

    return ConfigProxy()


class LocalAuthApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        token_server._local_auth_store = LocalAuthStore(
            str(Path(self.temp_dir.name) / "auth.sqlite3")
        )
        for limiter in (
            token_server.auth_otp_rate_limiter,
            token_server.auth_otp_recipient_limiter,
            token_server.auth_verify_rate_limiter,
        ):
            limiter.requests.clear()
        self.client = TestClient(TestServer(token_server.create_app()))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()
        token_server._local_auth_store = None
        self.temp_dir.cleanup()

    async def test_email_signup_authenticates_conversation_requests(self):
        delivered_codes = []

        async def fake_delivery(channel, identifier, code):
            delivered_codes.append((channel, identifier, code))
            return None

        with patch.object(token_server, "_deliver_otp", fake_delivery):
            response = await self.client.post(
                "/api/auth/otp",
                json={
                    "channel": "email",
                    "identifier": "person@example.com",
                    "mode": "signup",
                },
            )
        self.assertEqual(response.status, 200)
        self.assertEqual(delivered_codes[0][:2], ("email", "person@example.com"))

        response = await self.client.post(
            "/api/auth/verify",
            json={
                "channel": "email",
                "identifier": "person@example.com",
                "mode": "signup",
                "code": delivered_codes[0][2],
            },
        )
        self.assertEqual(response.status, 200)
        session = await response.json()

        response = await self.client.get(
            "/api/conversations",
            headers={"Authorization": f"Bearer {session['access_token']}"},
        )
        self.assertEqual(response.status, 200)
        self.assertEqual((await response.json())["conversations"], [])

        response = await self.client.get("/api/conversations")
        self.assertEqual(response.status, 401)

    async def test_google_signin_validates_provider_and_issues_local_session(self):
        class SupabaseResponse:
            is_error = False

            @staticmethod
            def json():
                return {
                    "id": "supabase-user-id",
                    "email": "person@example.com",
                    "email_confirmed_at": "2026-11-01T00:00:00Z",
                    "user_metadata": {"full_name": "Friday User"},
                }

        class SupabaseClient:
            def __init__(self, **_kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            async def get(self, url, headers):
                self_url = "https://project.supabase.co/auth/v1/user"
                if url != self_url:
                    raise AssertionError("Unexpected Supabase validation URL")
                if headers.get("Authorization") != "Bearer provider-access-token":
                    raise AssertionError("Provider access token was not forwarded")
                return SupabaseResponse()

        config = SimpleNamespace(
            SUPABASE_URL="https://project.supabase.co",
            SUPABASE_API_KEY="sb_publishable_test",
        )
        with (
            patch.object(token_server, "config", config_with_database(config)),
            patch("httpx.AsyncClient", SupabaseClient),
        ):
            response = await self.client.post(
                "/api/auth/google",
                json={"access_token": "provider-access-token"},
            )
        self.assertEqual(response.status, 200)
        session = await response.json()
        self.assertEqual(session["user"]["email"], "person@example.com")
        self.assertEqual(session["user"]["name"], "Friday User")
        self.assertEqual(
            token_server._auth_store().validate_access_token(session["access_token"])["email"],
            "person@example.com",
        )

    async def test_google_signin_rejects_unverified_email(self):
        class SupabaseResponse:
            is_error = False

            @staticmethod
            def json():
                return {"id": "supabase-user-id", "email": "person@example.com"}

        class SupabaseClient:
            def __init__(self, **_kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            async def get(self, *_args, **_kwargs):
                return SupabaseResponse()

        config = SimpleNamespace(
            SUPABASE_URL="https://project.supabase.co",
            SUPABASE_API_KEY="sb_publishable_test",
        )
        with (
            patch.object(token_server, "config", config_with_database(config)),
            patch("httpx.AsyncClient", SupabaseClient),
        ):
            response = await self.client.post(
                "/api/auth/google",
                json={"access_token": "provider-access-token"},
            )
        self.assertEqual(response.status, 403)

    async def test_public_config_does_not_expose_non_public_supabase_key(self):
        config = SimpleNamespace(
            SUPABASE_URL="https://project.supabase.co",
            SUPABASE_API_KEY="service-role-secret",
        )
        with patch.object(token_server, "config", config_with_database(config)):
            response = await self.client.get("/api/config")
        self.assertEqual(response.status, 200)
        public_config = await response.json()
        self.assertIsNone(public_config["supabase_anon_key"])


if __name__ == "__main__":
    unittest.main()
