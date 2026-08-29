"""Auth module tests: login (all roles), /auth/me, invalid creds, token handling, sessions, 2FA guard."""
import requests
import pytest

from conftest import API


class TestAuthLogin:
    def test_samples_endpoint_alive(self, api_client):
        r = api_client.get(f"{API}/scan/samples", timeout=60)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) == 5, f"Expected 5 sample products, got {len(data)}"

    def test_login_super_admin(self, api_client, admin_credentials):
        r = api_client.post(
            f"{API}/auth/login",
            json={"email": admin_credentials["email"], "password": admin_credentials["password"]},
            timeout=60,
        )
        assert r.status_code == 200, r.text[:400]
        data = r.json()
        assert data["email"] == admin_credentials["email"]
        assert data["role"] == "super_admin"
        assert isinstance(data["token"], str) and len(data["token"]) > 20
        assert "password_hash" not in data
        assert "_id" not in data
        assert data.get("requires_2fa") is False
        # httpOnly cookie assertions
        cookie_header = "; ".join(v for k, v in r.headers.items() if k.lower() == "set-cookie")
        assert "access_token" in cookie_header, f"access_token cookie missing: {cookie_header}"
        assert "HttpOnly" in cookie_header or "httponly" in cookie_header

    def test_login_all_seeded_roles(self, api_client, all_credentials):
        failures = []
        for cred in all_credentials.values():
            r = api_client.post(
                f"{API}/auth/login",
                json={"email": cred["email"], "password": cred["password"]},
                timeout=60,
            )
            if r.status_code != 200:
                failures.append((cred["email"], r.status_code, r.text[:150]))
                continue
            body = r.json()
            if cred.get("role") and body.get("role") != cred["role"]:
                failures.append((cred["email"], "role_mismatch", body.get("role")))
        assert not failures, f"Role login failures: {failures}"

    def test_login_wrong_password(self, api_client, admin_credentials):
        r = api_client.post(
            f"{API}/auth/login",
            json={"email": admin_credentials["email"], "password": "WrongPass!123"},
            timeout=60,
        )
        assert r.status_code == 401, r.text[:300]
        assert "detail" in r.json()

    def test_login_unknown_email(self, api_client):
        from conftest import clear_login_lockout

        clear_login_lockout("TEST_nobody@metrology.gov.in")
        r = api_client.post(
            f"{API}/auth/login",
            json={"email": "TEST_nobody@metrology.gov.in", "password": "whatever"},
            timeout=60,
        )
        assert r.status_code == 401

    def test_brute_force_lockout_behaviour(self, api_client):
        """5 consecutive bad logins must lock the account; the 6th must return 429.
        Uses a throwaway email so the shared seeded admin is never locked (and so parallel
        workers logging in as admin cannot race with this sequence)."""
        import uuid

        from conftest import clear_login_lockout

        email = f"test_bruteforce_{uuid.uuid4().hex[:8]}@metrology.gov.in"
        clear_login_lockout(email)
        statuses = []
        try:
            for _ in range(6):
                r = api_client.post(
                    f"{API}/auth/login",
                    json={"email": email, "password": "BadPass!000"},
                    timeout=60,
                )
                statuses.append(r.status_code)
            assert all(s in (401, 423, 429) for s in statuses), statuses
            assert statuses[5] == 429, f"expected lockout on 6th attempt, got {statuses}"
        finally:
            clear_login_lockout(email)


class TestAuthMe:
    def test_me_with_bearer_token(self, auth_client, admin_credentials):
        r = auth_client.get(f"{API}/auth/me", timeout=60)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert data["email"] == admin_credentials["email"]
        assert data["role"] == "super_admin"
        assert "password_hash" not in data
        assert "_id" not in data

    def test_me_without_token(self):
        r = requests.get(f"{API}/auth/me", timeout=60)
        assert r.status_code in (401, 403), f"Expected 401/403 got {r.status_code}"

    def test_me_with_invalid_token(self):
        r = requests.get(f"{API}/auth/me", headers={"Authorization": "Bearer not.a.valid.jwt"}, timeout=60)
        assert r.status_code in (401, 403)

    def test_sessions_listed_after_login(self, auth_client):
        r = auth_client.get(f"{API}/auth/sessions", timeout=60)
        assert r.status_code == 200
        sessions = r.json()
        assert isinstance(sessions, list) and len(sessions) >= 1
        assert "_id" not in sessions[0]
        assert "ip_address" in sessions[0]

    def test_logout(self, auth_client):
        r = auth_client.post(f"{API}/auth/logout", timeout=60)
        assert r.status_code == 200
        assert "message" in r.json()
