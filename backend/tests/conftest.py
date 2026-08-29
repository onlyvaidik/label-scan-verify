"""Shared fixtures for Legal Metrology Compliance backend API tests."""
import base64
import os
import re
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
_base = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not _base:
    raise RuntimeError("REACT_APP_BACKEND_URL missing from env and /app/frontend/.env")
BASE_URL = _base.rstrip("/")
API = f"{BASE_URL}/api"

ASSETS = Path(__file__).parent / "assets"


def _creds_from_file():
    path = Path("/app/memory/test_credentials.md")
    if not path.exists():
        return {}
    content = path.read_text(encoding="utf-8")
    emails = re.findall(r"(?im)^\s*(?:[-*]\s*)?(?:\*\*)?Email(?:\*\*)?\s*:\s*`?([^`\s]+)", content)
    passwords = re.findall(r"(?im)^\s*(?:[-*]\s*)?(?:\*\*)?Password(?:\*\*)?\s*:\s*`?([^`\s]+)", content)
    roles = re.findall(r"(?im)^\s*(?:[-*]\s*)?(?:\*\*)?Role(?:\*\*)?\s*:\s*`?([^`\s]+)", content)
    out = {}
    for i, email in enumerate(emails):
        out[email] = {
            "email": email,
            "password": passwords[i] if i < len(passwords) else None,
            "role": roles[i] if i < len(roles) else None,
        }
    return out


@pytest.fixture(scope="session")
def all_credentials():
    creds = _creds_from_file()
    if not creds:
        pytest.skip("No credentials found in /app/memory/test_credentials.md")
    return creds


@pytest.fixture(scope="session")
def admin_credentials(all_credentials):
    for c in all_credentials.values():
        if c.get("role") == "super_admin":
            return c
    pytest.skip("No super_admin credentials found")


@pytest.fixture(scope="class")
def api_client():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


def clear_login_lockout(email):
    """Remove brute-force lockout rows so suite-internal bad-password tests cannot
    lock the shared seeded accounts for subsequent test classes."""
    try:
        from pymongo import MongoClient

        backend_env = dotenv_values("/app/backend/.env")
        mongo_url = os.environ.get("MONGO_URL") or backend_env.get("MONGO_URL")
        db_name = os.environ.get("DB_NAME") or backend_env.get("DB_NAME")
        if not (mongo_url and db_name):
            return
        client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
        client[db_name].login_attempts.delete_many({"email": email.strip().lower()})
        client.close()
    except Exception:
        pass


@pytest.fixture(scope="class")
def admin_token(api_client, admin_credentials):
    clear_login_lockout(admin_credentials["email"])
    r = api_client.post(
        f"{API}/auth/login",
        json={"email": admin_credentials["email"], "password": admin_credentials["password"]},
        timeout=60,
    )
    if r.status_code != 200:
        pytest.fail(f"Admin login failed {r.status_code}: {r.text[:400]}")
    token = r.json().get("token")
    if not token:
        pytest.fail("Login response missing token")
    return token


@pytest.fixture(scope="class")
def auth_client(admin_token):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json", "Authorization": f"Bearer {admin_token}"})
    return s


@pytest.fixture(scope="session")
def label_image_b64():
    data = (ASSETS / "label_synthetic.jpg").read_bytes()
    return "data:image/jpeg;base64," + base64.b64encode(data).decode()


@pytest.fixture(scope="session")
def product_photo_b64():
    data = (ASSETS / "product_photo.jpg").read_bytes()
    return base64.b64encode(data).decode()


@pytest.fixture(scope="session")
def non_label_image_b64():
    data = (ASSETS / "non_label.jpg").read_bytes()
    return "data:image/jpeg;base64," + base64.b64encode(data).decode()


def compliant_declarations():
    """A fully compliant declaration set (used as baseline for scan/save tests)."""
    return {
        "manufacturer_name": "TEST_Shuddh Foods Pvt Ltd",
        "manufacturer_address": "Plot 44, MIDC, Pune, Maharashtra - 411019",
        "commodity_name": "Whole Wheat Flour",
        "net_quantity_value": 1,
        "net_quantity_unit": "kg",
        "net_quantity_raw": "Net Qty 1 kg",
        "unit_sale_price": "Rs. 0.068 per g",
        "mrp_value": 68.0,
        "mrp_raw": "MRP Rs. 68.00 (incl. of all taxes)",
        "taxes_inclusive_declared": True,
        "manufacturing_date": "03/2026",
        "best_before_date": "09/2026",
        "consumer_care_phone": "1800-200-4455",
        "consumer_care_email": "care@shuddhfoods.in",
        "consumer_care_details": "Consumer Care Cell, Pune",
        "country_of_origin": "India",
        "batch_number": "SBA2026C77",
    }
