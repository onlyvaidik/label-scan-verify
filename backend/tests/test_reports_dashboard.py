"""Reports (PDF/DOCX/CSV/JSON), dashboard stats, analytics hotspots, rules library, audit logs, users."""
import csv
import io

import pytest
import requests

from conftest import API, compliant_declarations


@pytest.fixture(scope="class")
def sample_scan(auth_client):
    r = auth_client.post(f"{API}/scan/save", json={
        "brand_name": "TEST_Report Brand",
        "commodity_name": "Basmati Rice",
        "category": "FMCG Packaged Food",
        "panel_area_sq_cm": 220.0,
        "numeral_height_mm": 2.0,
        "letter_height_mm": 1.0,
        "declarations": compliant_declarations(),
    }, timeout=90)
    assert r.status_code == 200, r.text[:300]
    doc = r.json()
    yield doc
    auth_client.delete(f"{API}/scans/{doc['id']}", timeout=60)


class TestReports:
    def test_pdf_report(self, auth_client, sample_scan):
        r = auth_client.get(f"{API}/reports/{sample_scan['id']}/pdf", timeout=120)
        assert r.status_code == 200, r.text[:300]
        assert r.headers["content-type"].startswith("application/pdf")
        assert r.content[:4] == b"%PDF", r.content[:40]
        assert len(r.content) > 1024, len(r.content)
        assert "attachment" in r.headers.get("content-disposition", "")

    def test_docx_report(self, auth_client, sample_scan):
        r = auth_client.get(f"{API}/reports/{sample_scan['id']}/docx", timeout=120)
        assert r.status_code == 200, r.text[:300]
        assert "wordprocessingml" in r.headers["content-type"]
        assert r.content[:2] == b"PK", r.content[:20]
        assert len(r.content) > 1024

    def test_json_report(self, auth_client, sample_scan):
        r = auth_client.get(f"{API}/reports/{sample_scan['id']}/json", timeout=60)
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == sample_scan["id"]
        assert "_id" not in data

    def test_report_404_unknown_scan(self, auth_client):
        for fmt in ["pdf", "docx", "json"]:
            r = auth_client.get(f"{API}/reports/SCAN-NOPE/{fmt}", timeout=60)
            assert r.status_code == 404, f"{fmt} -> {r.status_code}"

    def test_csv_export(self, auth_client, sample_scan):
        r = auth_client.get(f"{API}/reports/export/csv", timeout=120)
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/csv")
        rows = list(csv.reader(io.StringIO(r.text)))
        assert len(rows) >= 2, rows
        header = ",".join(rows[0]).lower()
        assert "id" in header or "case" in header
        assert sample_scan["id"] in r.text


class TestDashboardAnalytics:
    def test_dashboard_stats(self, auth_client):
        r = auth_client.get(f"{API}/dashboard/stats", timeout=60)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        for key in ["total_scans", "compliant_count", "non_compliant_count", "compliance_rate",
                    "notices_issued", "category_stats", "violation_chart_data", "recent_scans"]:
            assert key in d, f"missing {key}"
        assert d["total_scans"] >= 1
        assert 0 <= d["compliance_rate"] <= 100
        assert isinstance(d["category_stats"], list) and len(d["category_stats"]) >= 1
        assert "_id" in d["category_stats"][0] or "count" in d["category_stats"][0]
        assert isinstance(d["violation_chart_data"], list)
        assert isinstance(d["recent_scans"], list) and len(d["recent_scans"]) <= 6
        assert all("_id" not in s for s in d["recent_scans"])
        assert d["compliant_count"] + d["non_compliant_count"] <= d["total_scans"]

    def test_hotspots(self, api_client):
        r = api_client.get(f"{API}/analytics/hotspots", timeout=60)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list) and len(data) >= 6
        for row in data:
            assert set(["state", "district", "total_inspections", "compliant_rate", "risk_level"]).issubset(row)

    def test_audit_logs_after_activity(self, auth_client):
        r = auth_client.get(f"{API}/audit-logs", params={"limit": 50}, timeout=60)
        assert r.status_code == 200
        logs = r.json()
        assert isinstance(logs, list) and len(logs) >= 1
        assert all("_id" not in log for log in logs)
        actions = {log["action"] for log in logs}
        assert "USER_LOGIN" in actions, actions
        for log in logs[:5]:
            assert set(["user_email", "action", "entity_type", "timestamp"]).issubset(log)


class TestRulesLibrary:
    def test_list_rules(self, api_client):
        r = api_client.get(f"{API}/rules", timeout=60)
        assert r.status_code == 200
        d = r.json()
        assert len(d["rules"]) == 12, f"expected 12 seeded rules, got {len(d['rules'])}"
        assert all("_id" not in rule for rule in d["rules"])
        assert len(d["table_ii_reference"]) == 4
        first = d["rules"][0]
        assert set(["rule_id", "rule_name", "section", "severity", "penalty_clause"]).issubset(first)

    def test_update_rule_as_admin(self, auth_client):
        rules = auth_client.get(f"{API}/rules", timeout=60).json()["rules"]
        rule_id = rules[0]["rule_id"]
        original = rules[0].get("description", "")
        r = auth_client.put(f"{API}/rules/{rule_id}", json={"description": "TEST_updated description"}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["description"] == "TEST_updated description"
        # verify persistence + restore
        after = auth_client.get(f"{API}/rules", timeout=60).json()["rules"]
        assert any(x["rule_id"] == rule_id and x["description"] == "TEST_updated description" for x in after)
        auth_client.put(f"{API}/rules/{rule_id}", json={"description": original}, timeout=60)

    def test_update_rule_unknown_id(self, auth_client):
        r = auth_client.put(f"{API}/rules/NOPE-RULE", json={"description": "x"}, timeout=60)
        assert r.status_code == 404

    def test_update_rule_requires_auth(self):
        r = requests.put(f"{API}/rules/LMPC-RULE-6-1-A", json={"description": "hack"}, timeout=60)
        assert r.status_code in (401, 403)

    def test_viewer_cannot_update_rule(self, api_client, all_credentials):
        viewer = next((c for c in all_credentials.values() if c.get("role") == "viewer"), None)
        if not viewer:
            pytest.skip("no viewer credentials")
        login = api_client.post(f"{API}/auth/login", json={"email": viewer["email"], "password": viewer["password"]}, timeout=60)
        assert login.status_code == 200
        token = login.json()["token"]
        r = requests.put(f"{API}/rules/LMPC-RULE-6-1-A", json={"description": "viewer edit"},
                         headers={"Authorization": f"Bearer {token}"}, timeout=60)
        assert r.status_code == 403, f"viewer allowed to edit rules: {r.status_code}"


class TestUserManagement:
    def test_list_users_requires_auth(self):
        r = requests.get(f"{API}/users", timeout=60)
        assert r.status_code in (401, 403)

    def test_list_users_as_admin(self, auth_client):
        r = auth_client.get(f"{API}/users", timeout=60)
        assert r.status_code == 200
        users = r.json()
        assert len(users) >= 4
        assert all("password_hash" not in u and "_id" not in u for u in users)
        roles = {u["role"] for u in users}
        assert {"super_admin", "enforcement_officer", "inspector", "viewer"}.issubset(roles), roles

    def test_viewer_cannot_create_user(self, api_client, all_credentials):
        viewer = next((c for c in all_credentials.values() if c.get("role") == "viewer"), None)
        if not viewer:
            pytest.skip("no viewer credentials")
        token = api_client.post(f"{API}/auth/login", json={"email": viewer["email"], "password": viewer["password"]}, timeout=60).json()["token"]
        r = requests.post(f"{API}/users", json={
            "email": "TEST_hack@metrology.gov.in", "password": "Test@12345", "name": "Hacker", "role": "super_admin"
        }, headers={"Authorization": f"Bearer {token}"}, timeout=60)
        assert r.status_code == 403, r.status_code
