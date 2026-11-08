"""Local SQLite-backed accounts, OTP challenges, sessions, and chat history."""

import hashlib
import hmac
import json
import secrets
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


ACCESS_TOKEN_TTL = 60 * 60
REFRESH_TOKEN_TTL = 60 * 60 * 24 * 30
OTP_TTL = 10 * 60
OTP_MAX_ATTEMPTS = 5


class LocalAuthStore:
    def __init__(self, database_path: str):
        self.database_path = database_path
        if database_path != ":memory:":
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                PRAGMA foreign_keys = ON;
                CREATE TABLE IF NOT EXISTS auth_users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE,
                    phone TEXT UNIQUE,
                    display_name TEXT,
                    created_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS auth_otp_challenges (
                    channel TEXT NOT NULL,
                    identifier TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    salt BLOB NOT NULL,
                    code_hash BLOB NOT NULL,
                    expires_at INTEGER NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (channel, identifier)
                );
                CREATE TABLE IF NOT EXISTS auth_sessions (
                    access_token_hash TEXT PRIMARY KEY,
                    refresh_token_hash TEXT UNIQUE NOT NULL,
                    user_id TEXT NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
                    access_expires_at INTEGER NOT NULL,
                    refresh_expires_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS auth_conversations (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    messages TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS auth_conversations_user_updated
                    ON auth_conversations(user_id, updated_at DESC);
                """
            )
            user_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(auth_users)")
            }
            if "display_name" not in user_columns:
                connection.execute("ALTER TABLE auth_users ADD COLUMN display_name TEXT")

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _new_token() -> str:
        return secrets.token_urlsafe(32)

    @staticmethod
    def _session_result(user: sqlite3.Row, access: str, refresh: str, now: int) -> dict[str, Any]:
        return {
            "access_token": access,
            "refresh_token": refresh,
            "expires_in": ACCESS_TOKEN_TTL,
            "expires_at": now + ACCESS_TOKEN_TTL,
            "user": {
                "id": user["id"],
                **({"email": user["email"]} if user["email"] else {}),
                **({"phone": user["phone"]} if user["phone"] else {}),
                **({"name": user["display_name"]} if user["display_name"] else {}),
            },
        }

    @staticmethod
    def _issue_session(connection: sqlite3.Connection, user: sqlite3.Row, now: int) -> dict[str, Any]:
        access = LocalAuthStore._new_token()
        refresh = LocalAuthStore._new_token()
        connection.execute(
            """
            INSERT INTO auth_sessions
                (access_token_hash, refresh_token_hash, user_id, access_expires_at, refresh_expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                LocalAuthStore._token_hash(access),
                LocalAuthStore._token_hash(refresh),
                user["id"],
                now + ACCESS_TOKEN_TTL,
                now + REFRESH_TOKEN_TTL,
            ),
        )
        return LocalAuthStore._session_result(user, access, refresh, now)

    def save_otp(self, channel: str, identifier: str, mode: str, code: str) -> None:
        salt = secrets.token_bytes(16)
        code_hash = hashlib.pbkdf2_hmac("sha256", code.encode("ascii"), salt, 120_000)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO auth_otp_challenges
                    (channel, identifier, mode, salt, code_hash, expires_at, attempts)
                VALUES (?, ?, ?, ?, ?, ?, 0)
                ON CONFLICT(channel, identifier) DO UPDATE SET
                    mode = excluded.mode,
                    salt = excluded.salt,
                    code_hash = excluded.code_hash,
                    expires_at = excluded.expires_at,
                    attempts = 0
                """,
                (channel, identifier, mode, salt, code_hash, int(time.time()) + OTP_TTL),
            )

    def verify_otp(self, channel: str, identifier: str, mode: str, code: str) -> dict[str, Any] | None:
        now = int(time.time())
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            challenge = connection.execute(
                """
                SELECT mode, salt, code_hash, expires_at, attempts
                FROM auth_otp_challenges WHERE channel = ? AND identifier = ?
                """,
                (channel, identifier),
            ).fetchone()
            if (
                challenge is None
                or challenge["expires_at"] < now
                or challenge["attempts"] >= OTP_MAX_ATTEMPTS
                or challenge["mode"] != mode
            ):
                connection.execute(
                    "DELETE FROM auth_otp_challenges WHERE channel = ? AND identifier = ?",
                    (channel, identifier),
                )
                return None

            candidate = hashlib.pbkdf2_hmac(
                "sha256", code.encode("ascii"), challenge["salt"], 120_000
            )
            if not hmac.compare_digest(candidate, challenge["code_hash"]):
                attempts = challenge["attempts"] + 1
                if attempts >= OTP_MAX_ATTEMPTS:
                    connection.execute(
                        "DELETE FROM auth_otp_challenges WHERE channel = ? AND identifier = ?",
                        (channel, identifier),
                    )
                else:
                    connection.execute(
                        """
                        UPDATE auth_otp_challenges SET attempts = ?
                        WHERE channel = ? AND identifier = ?
                        """,
                        (attempts, channel, identifier),
                    )
                return None

            connection.execute(
                "DELETE FROM auth_otp_challenges WHERE channel = ? AND identifier = ?",
                (channel, identifier),
            )
            identity_column = "email" if channel == "email" else "phone"
            user = connection.execute(
                f"SELECT id, email, phone, display_name FROM auth_users WHERE {identity_column} = ?",
                (identifier,),
            ).fetchone()
            if mode == "signup":
                if user is not None:
                    return None
                user_id = str(uuid.uuid4())
                email = identifier if channel == "email" else None
                phone = identifier if channel == "phone" else None
                connection.execute(
                    "INSERT INTO auth_users (id, email, phone, created_at) VALUES (?, ?, ?, ?)",
                    (user_id, email, phone, now),
                )
                user = connection.execute(
                    "SELECT id, email, phone, display_name FROM auth_users WHERE id = ?", (user_id,)
                ).fetchone()
            elif user is None:
                return None

            return self._issue_session(connection, user, now)

    def validate_access_token(self, token: str) -> dict[str, str] | None:
        now = int(time.time())
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT u.id, u.email, u.phone, u.display_name
                FROM auth_sessions s JOIN auth_users u ON u.id = s.user_id
                WHERE s.access_token_hash = ? AND s.access_expires_at > ?
                """,
                (self._token_hash(token), now),
            ).fetchone()
            if row is None:
                return None
            return {
                "id": row["id"],
                **({"email": row["email"]} if row["email"] else {}),
                **({"phone": row["phone"]} if row["phone"] else {}),
                **({"name": row["display_name"]} if row["display_name"] else {}),
            }

    def refresh_session(self, refresh_token: str) -> dict[str, Any] | None:
        now = int(time.time())
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT s.access_token_hash, u.id, u.email, u.phone, u.display_name
                FROM auth_sessions s JOIN auth_users u ON u.id = s.user_id
                WHERE s.refresh_token_hash = ? AND s.refresh_expires_at > ?
                """,
                (self._token_hash(refresh_token), now),
            ).fetchone()
            if row is None:
                return None
            connection.execute(
                "DELETE FROM auth_sessions WHERE access_token_hash = ?", (row["access_token_hash"],)
            )
            return self._issue_session(connection, row, now)

    def login_with_verified_email(self, email: str, display_name: str | None = None) -> dict[str, Any]:
        now = int(time.time())
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            user = connection.execute(
                "SELECT id, email, phone, display_name FROM auth_users WHERE email = ?", (email,)
            ).fetchone()
            if user is None:
                user_id = str(uuid.uuid4())
                connection.execute(
                    "INSERT INTO auth_users (id, email, display_name, created_at) VALUES (?, ?, ?, ?)",
                    (user_id, email, display_name, now),
                )
            elif display_name and display_name != user["display_name"]:
                connection.execute(
                    "UPDATE auth_users SET display_name = ? WHERE id = ?",
                    (display_name, user["id"]),
                )
            user = connection.execute(
                "SELECT id, email, phone, display_name FROM auth_users WHERE email = ?", (email,)
            ).fetchone()
            return self._issue_session(connection, user, now)

    def list_conversations(self, user_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, title, updated_at, messages FROM auth_conversations
                WHERE user_id = ? ORDER BY updated_at DESC
                """,
                (user_id,),
            ).fetchall()
            return [
                {
                    "id": row["id"],
                    "title": row["title"],
                    "updated_at": row["updated_at"],
                    "messages": json.loads(row["messages"]),
                }
                for row in rows
            ]

    def save_conversation(
        self, user_id: str, conversation_id: str, title: str, updated_at: str, messages: list[dict[str, Any]]
    ) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO auth_conversations (id, user_id, title, updated_at, messages)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    updated_at = excluded.updated_at,
                    messages = excluded.messages
                WHERE auth_conversations.user_id = excluded.user_id
                """,
                (conversation_id, user_id, title, updated_at, json.dumps(messages)),
            )
            return cursor.rowcount > 0

    def delete_conversation(self, user_id: str, conversation_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM auth_conversations WHERE id = ? AND user_id = ?",
                (conversation_id, user_id),
            )
