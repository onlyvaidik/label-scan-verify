"""Iteration-3 backend tests: Login Guard (5-strike lockout), Notice-to-Seller (Resend/Twilio),
Bulk URL Scan, plus regression on auth/scan/dashboard/report endpoints."""
import os
import uuid

import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

from conftest import API

backend_env = dotenv_values("/app/backend/.env")
MONGO_URL = os.environ.get("MONGO_URL") or backend_env.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME") or backend_env.get("DB_NAME")

SEED_SCAN_ID = "SCAN-2026-002"
INTERNAL_API = "http://localhost:8001/api"


def json_or_xfail(response, context):
    """The preview ingress replaces 5xx bodies with a Cloudflare HTML page, so the JSON
    `detail` never reaches the client. Detect it explicitly instead of masking it."""
    ctype = response.headers.get("content-type", "")
    if "application/json" not in ctype:
        pytest.xfail(
            f"{context}: HTTP {response.status_code} body is NOT JSON (content-type={ctype!r}) — "
            f"ingress replaced the FastAPI error body with an HTML error page. Body starts: "
            f"{response.text[:120]!r}"
        )
    return response.json()


@pytest.fixture(scope="module")
def mongo_db():
    if not (MONGO_URL and DB_NAME):
        pytest.skip("MONGO_URL/DB_NAME not available for direct DB assertions")
    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    yield client[DB_NAME]
    client.close()


# =====================================================================
# LOGIN GUARD — 5-strike lockout (module isolated on its own xdist worker)
# =====================================================================
class TestLoginGuard:
    """Uses a throwaway registered account so the seeded admin never gets locked."""

    @pytest.fixture(scope="class")
    def guard_user(self, mongo_db):
        email = f"test_lockguard_{uuid.uuid4().hex[:8]}@metrology.gov.in"
        password = "GuardPass@2026"
        r = requests.post(
            f"{API}/auth/register",
            json={"email": email, "password": password, "name": "TEST_ Lock Guard", "role": "viewer"},
            timeout=60,
        )
        assert r.status_code == 200, f"register failed {r.status_code}: {r.text[:300]}"
        mongo_db.login_attempts.delete_many({"email": email})
        yield {"email": email, "password": password}
        mongo_db.login_attempts.delete_many({"email": email})
        mongo_db.users.delete_many({"email": email})

    def test_success_before_lockout_clears_counter(self, guard_user, mongo_db):
        # 2 failed attempts -> counter present
        for _ in range(2):
            r = requests.post(
                f"{API}/auth/login",
                json={"email": guard_user["email"], "password": "wrong-pass"},
                timeout=60,
            )
            assert r.status_code == 401, r.text[:300]
        doc = mongo_db.login_attempts.find_one({"email": guard_user["email"]})
        assert doc is not None and doc.get("failures") == 2

        # correct password now succeeds and wipes the counter
        ok = requests.post(
            f"{API}/auth/login",
            json={"email": guard_user["email"], "password": guard_user["password"]},
            timeout=60,
        )
        assert ok.status_code == 200, ok.text[:300]
        assert ok.json().get("token")
        assert mongo_db.login_attempts.find_one({"email": guard_user["email"]}) is None

    def test_five_strike_lockout_sequence(self, guard_user, mongo_db):
        mongo_db.login_attempts.delete_many({"email": guard_user["email"]})
        details = []
        for attempt in range(1, 6):
            r = requests.post(
                f"{API}/auth/login",
                json={"email": guard_user["email"], "password": "wrong-pass"},
                timeout=60,
            )
            assert r.status_code == 401, f"attempt {attempt}: {r.status_code} {r.text[:300]}"
            detail = r.json().get("detail", "")
            details.append(detail)

        # attempts 3 and 4 must warn about remaining attempts
        assert "2 attempt(s) remaining" in details[2], details
        assert "1 attempt(s) remaining" in details[3], details
        # 5th attempt -> locked
        assert "locked" in details[4].lower(), details

        doc = mongo_db.login_attempts.find_one({"email": guard_user["email"]})
        assert doc.get("failures") == 5
        assert doc.get("locked_until", 0) > 0

    def test_correct_password_after_lockout_returns_429(self, guard_user):
        r = requests.post(
            f"{API}/auth/login",
            json={"email": guard_user["email"], "password": guard_user["password"]},
            timeout=60,
        )
        assert r.status_code == 429, f"{r.status_code}: {r.text[:300]}"
        assert "locked" in r.json().get("detail", "").lower()

    def test_unlock_then_login_works(self, guard_user, mongo_db):
        mongo_db.login_attempts.delete_many({"email": guard_user["email"]})
        r = requests.post(
            f"{API}/auth/login",
            json={"email": guard_user["email"], "password": guard_user["password"]},
            timeout=60,
        )
        assert r.status_code == 200, r.text[:300]

    def test_bcrypt_hash_and_httponly_cookies(self, guard_user, mongo_db):
        user = mongo_db.users.find_one({"email": guard_user["email"]})
        assert user["password_hash"].startswith("$2b$"), user["password_hash"][:10]
        r = requests.post(
            f"{API}/auth/login",
            json={"email": guard_user["email"], "password": guard_user["password"]},
            timeout=60,
        )
        assert r.status_code == 200
        cookie_headers = "; ".join(
            v for k, v in r.raw.headers.items() if k.lower() == "set-cookie"
        ) if hasattr(r, "raw") else ""
        combined = cookie_headers or str(r.headers.get("Set-Cookie", ""))
        assert "access_token" in combined, combined[:300]
        assert "HttpOnly" in combined, combined[:300]

    def test_failure_counter_not_reset_after_lockout_window(self, guard_user, mongo_db):
        """Documents current behaviour: `failures` is never reset when the 15-min window
        expires, so a single later typo immediately re-locks the account for 15 more minutes."""
        import time

        email = guard_user["email"]
        mongo_db.login_attempts.update_one(
            {"email": email},
            {"$set": {"email": email, "failures": 5, "locked_until": time.time() - 5}},
            upsert=True,
        )
        bad = requests.post(
            f"{API}/auth/login", json={"email": email, "password": "wrong-pass"}, timeout=60
        )
        assert bad.status_code == 401
        relocked = requests.post(
            f"{API}/auth/login", json={"email": email, "password": guard_user["password"]}, timeout=60
        )
        mongo_db.login_attempts.delete_many({"email": email})
        if relocked.status_code == 429:
            pytest.xfail(
                "No rolling window: after the lockout expires the counter stays at 5, so ONE "
                "further wrong password re-locks the account for another 15 minutes."
            )
        assert relocked.status_code == 200


# =====================================================================
# NOTICE-TO-SELLER
# =====================================================================
class TestNoticeToSeller:
    def test_validation_unknown_channel(self, auth_client):
        r = auth_client.post(
            f"{API}/scans/{SEED_SCAN_ID}/send-notice",
            json={"channel": "carrier_pigeon"}, timeout=60,
        )
        assert r.status_code in (400, 422), f"{r.status_code}: {r.text[:300]}"

    def test_validation_email_requires_recipient(self, auth_client):
        r = auth_client.post(
            f"{API}/scans/SCAN-2026-004/send-notice",
            json={"channel": "email"}, timeout=60,
        )
        # SCAN-2026-004 may or may not carry a consumer_care_email; assert no crash
        assert r.status_code != 500, r.text[:300]
        if r.status_code == 400:
            assert "email" in r.json()["detail"].lower()

    def test_validation_sms_requires_phone(self, auth_client):
        r = auth_client.post(
            f"{API}/scans/{SEED_SCAN_ID}/send-notice",
            json={"channel": "sms", "recipient_phone": ""}, timeout=60,
        )
        assert r.status_code != 500, r.text[:300]
        if r.status_code == 400:
            assert "phone" in r.json()["detail"].lower()

    def test_missing_scan_returns_404(self, auth_client):
        r = auth_client.post(
            f"{API}/scans/SCAN-DOES-NOT-EXIST/send-notice",
            json={"channel": "email", "recipient_email": "test@example.com"}, timeout=60,
        )
        assert r.status_code == 404, f"{r.status_code}: {r.text[:300]}"

    def test_unauthenticated_send_notice_rejected(self):
        r = requests.post(
            f"{API}/scans/{SEED_SCAN_ID}/send-notice",
            json={"channel": "email", "recipient_email": "test@example.com"}, timeout=60,
        )
        assert r.status_code in (401, 403), f"{r.status_code}: {r.text[:300]}"

    def test_email_notice_invalid_resend_key_returns_502(self, auth_client, mongo_db):
        before = mongo_db.scans.find_one({"id": SEED_SCAN_ID}, {"_id": 0})
        notices_before = mongo_db.notices.count_documents({"scan_id": SEED_SCAN_ID}) \
            if "notices" in mongo_db.list_collection_names() else 0

        r = auth_client.post(
            f"{API}/scans/{SEED_SCAN_ID}/send-notice",
            json={"channel": "email", "recipient_email": "test@example.com"}, timeout=120,
        )
        assert r.status_code == 502, f"expected 502 for invalid Resend key, got {r.status_code}: {r.text[:400]}"

        # must NOT mark the scan as notice issued and must NOT persist a notice
        after = mongo_db.scans.find_one({"id": SEED_SCAN_ID}, {"_id": 0})
        assert after.get("latest_notice_number") == before.get("latest_notice_number"), \
            "scan mutated despite failed email delivery"
        notices_after = mongo_db.notices.count_documents({"scan_id": SEED_SCAN_ID}) \
            if "notices" in mongo_db.list_collection_names() else 0
        assert notices_after == notices_before, "notice persisted despite failed delivery"

        # Error body must be readable JSON with a clear message
        body = json_or_xfail(r, "email notice invalid-Resend-key")
        text = str(body.get("detail")).lower()
        assert "invalid" in text or "fail" in text, text[:400]

    def test_sms_notice_twilio_structured_response(self, auth_client, mongo_db):
        r = auth_client.post(
            f"{API}/scans/{SEED_SCAN_ID}/send-notice",
            json={"channel": "sms", "recipient_phone": "+15005550006"}, timeout=120,
        )
        assert r.status_code in (200, 502), f"unexpected {r.status_code}: {r.text[:400]}"
        if r.status_code == 502:
            body = json_or_xfail(r, "sms notice twilio-trial")
            detail = body["detail"]
            assert isinstance(detail, dict) and detail.get("errors"), detail
            assert detail["errors"][0]["channel"] == "sms"
            assert detail["errors"][0]["error"]
            print("Twilio SMS graceful failure:", detail["errors"][0]["error"][:200])
        else:
            body = r.json()
            # Persistence checks on successful delivery
            assert body["notice_number"].startswith("LM/SEC36/")
            assert body["scan_id"] == SEED_SCAN_ID
            assert body["deliveries"] and body["deliveries"][0]["channel"] == "sms"
            assert body["deliveries"][0]["provider"] == "twilio"
            assert body["deliveries"][0]["provider_message_id"]
            assert "_id" not in body

            scan = mongo_db.scans.find_one({"id": SEED_SCAN_ID}, {"_id": 0})
            assert scan.get("enforcement_notice_issued") is True
            assert scan.get("latest_notice_number") == body["notice_number"]
            stored = mongo_db.notices.find_one({"notice_number": body["notice_number"]})
            assert stored is not None, "notice not stored in db.notices"

            listed = auth_client.get(f"{API}/scans/{SEED_SCAN_ID}/notices", timeout=60)
            assert listed.status_code == 200
            assert any(n["notice_number"] == body["notice_number"] for n in listed.json())

    def test_list_notices_returns_array(self, auth_client):
        r = auth_client.get(f"{API}/scans/{SEED_SCAN_ID}/notices", timeout=60)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert isinstance(data, list)
        for n in data:
            assert "_id" not in n
            assert "notice_number" in n

    def test_list_notices_unknown_scan_returns_empty(self, auth_client):
        r = auth_client.get(f"{API}/scans/SCAN-NOPE-999/notices", timeout=60)
        assert r.status_code == 200
        assert r.json() == []


# =====================================================================
# BULK URL SCAN
# =====================================================================
class TestUrlScan:
    def test_invalid_url_missing_scheme_returns_400(self, auth_client):
        r = auth_client.post(f"{API}/scan/url", json={"url": "www.bigbasket.com/pd/40133761/"}, timeout=60)
        assert r.status_code == 400, f"{r.status_code}: {r.text[:300]}"
        assert "http" in r.json()["detail"].lower()

    def test_antibot_url_returns_502_not_crash(self, auth_client):
        r = auth_client.post(
            f"{API}/scan/url",
            json={"url": "https://www.amazon.in/dp/B08L5VBTY4"}, timeout=180,
        )
        assert r.status_code in (200, 502), f"unexpected {r.status_code}: {r.text[:400]}"
        if r.status_code == 502:
            body = json_or_xfail(r, "anti-bot URL scan")
            detail = str(body.get("detail", ""))
            assert detail, "502 with empty detail"
            print("Anti-bot URL detail:", detail[:250])

    def test_unreachable_domain_returns_502(self, auth_client):
        r = auth_client.post(
            f"{API}/scan/url",
            json={"url": "https://this-domain-should-not-exist-98761234.example/product"}, timeout=180,
        )
        assert r.status_code == 502, f"{r.status_code}: {r.text[:300]}"
        body = json_or_xfail(r, "unreachable domain URL scan")
        assert "fetch" in str(body.get("detail", "")).lower()

    def test_bigbasket_product_url_scan(self, auth_client):
        r = auth_client.post(
            f"{API}/scan/url",
            json={"url": "https://www.bigbasket.com/pd/40133761/parle-marie-biscuit-250-g/"},
            timeout=240,
        )
        if r.status_code == 502:
            pytest.xfail(f"BigBasket blocked/sparse: {str(r.json().get('detail'))[:250]}")
        assert r.status_code == 200, f"{r.status_code}: {r.text[:400]}"
        data = r.json()
        assert data["compliance_status"] in ("Compliant", "Partially Compliant", "Non-Compliant")
        assert isinstance(data["compliance_score"], (int, float))
        assert 0 <= data["compliance_score"] <= 100
        assert isinstance(data["violations"], list)
        assert data["listing_platform"] == "BigBasket"
        assert data["listing_url"].startswith("https://www.bigbasket.com")
        assert isinstance(data["declarations"], dict)
        assert data["declarations"].get("commodity_name") or data.get("brand_name")
        assert data["barcode_gtin"]


# =====================================================================
# REGRESSION
# =====================================================================
class TestRegression:
    def test_admin_login_still_works(self, api_client, admin_credentials, mongo_db):
        mongo_db.login_attempts.delete_many({"email": admin_credentials["email"]})
        r = api_client.post(
            f"{API}/auth/login",
            json={"email": admin_credentials["email"], "password": admin_credentials["password"]},
            timeout=60,
        )
        assert r.status_code == 200, r.text[:300]
        body = r.json()
        assert body.get("token")
        assert body["email"] == admin_credentials["email"]
        assert body["role"] == "super_admin"

    def test_dashboard_stats_non_null(self, auth_client):
        r = auth_client.get(f"{API}/dashboard/stats", timeout=60)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        for key in ("total_scans", "compliant_count", "non_compliant_count"):
            assert key in data, data.keys()
            assert data[key] is not None
        assert data["total_scans"] >= 5

    def test_pdf_report_still_valid(self, auth_client):
        r = auth_client.get(f"{API}/reports/{SEED_SCAN_ID}/pdf", timeout=120)
        assert r.status_code == 200, r.text[:300]
        assert r.content[:4] == b"%PDF", r.content[:20]
        assert len(r.content) > 1000

    def test_scan_analyze_real_image_still_works(self, auth_client, product_photo_b64):
        r = auth_client.post(
            f"{API}/scan/analyze",
            json={"image_base64": product_photo_b64, "category": "FMCG Packaged Food"},
            timeout=240,
        )
        assert r.status_code == 200, f"{r.status_code}: {r.text[:400]}"
        data = r.json()
        assert data["compliance_status"] in ("Compliant", "Partially Compliant", "Non-Compliant")
        assert "declarations" in data
        assert "Fallback" not in str(data.get("engine_used", ""))


# =====================================================================
# RCA: same failures hit directly on the app (bypassing the ingress) to prove
# the FastAPI error contract is correct and the HTML body comes from the edge.
# =====================================================================
class TestInternalErrorContract:
    @pytest.fixture(scope="class")
    def internal_headers(self, admin_credentials):
        r = requests.post(
            f"{INTERNAL_API}/auth/login",
            json={"email": admin_credentials["email"], "password": admin_credentials["password"]},
            timeout=60,
        )
        assert r.status_code == 200, r.text[:300]
        return {"Authorization": f"Bearer {r.json()['token']}"}

    def test_internal_email_notice_error_json(self, internal_headers):
        r = requests.post(
            f"{INTERNAL_API}/scans/{SEED_SCAN_ID}/send-notice",
            json={"channel": "email", "recipient_email": "test@example.com"},
            headers=internal_headers, timeout=120,
        )
        assert r.status_code == 502
        assert "application/json" in r.headers.get("content-type", "")
        err = r.json()["detail"]["errors"][0]
        assert err["channel"] == "email"
        assert "invalid" in err["error"].lower(), err["error"]

    def test_internal_sms_notice_error_json(self, internal_headers):
        r = requests.post(
            f"{INTERNAL_API}/scans/{SEED_SCAN_ID}/send-notice",
            json={"channel": "sms", "recipient_phone": "+15005550006"},
            headers=internal_headers, timeout=120,
        )
        assert r.status_code in (200, 502)
        assert "application/json" in r.headers.get("content-type", "")
        if r.status_code == 502:
            err = r.json()["detail"]["errors"][0]
            assert err["channel"] == "sms"
            assert "twilio" in err["error"].lower()

    def test_internal_url_scan_error_json(self, internal_headers):
        r = requests.post(
            f"{INTERNAL_API}/scan/url",
            json={"url": "https://this-domain-should-not-exist-98761234.example/p"},
            headers=internal_headers, timeout=120,
        )
        assert r.status_code == 502
        assert "application/json" in r.headers.get("content-type", "")
        assert "Failed to fetch product URL" in r.json()["detail"]
