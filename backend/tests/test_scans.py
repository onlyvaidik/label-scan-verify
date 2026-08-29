"""Scan module tests: /scan/analyze (Gemini 3 Flash vision), /scan/save persistence, /scans list+filters, actions."""
import pytest
import requests

from conftest import API, compliant_declarations


@pytest.fixture(scope="module")
def created_scan_ids():
    return []


@pytest.fixture(scope="module", autouse=True)
def cleanup(created_scan_ids, request):
    yield
    # best-effort cleanup using an admin token
    import re
    from pathlib import Path
    content = Path("/app/memory/test_credentials.md").read_text(encoding="utf-8")
    email = re.search(r"(?im)Email\*\*?\s*:\s*`?([^`\s]+)", content)
    pwd = re.search(r"(?im)Password\*\*?\s*:\s*`?([^`\s]+)", content)
    if not (email and pwd):
        return
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email.group(1), "password": pwd.group(1)}, timeout=60)
    if r.status_code != 200:
        return
    s.headers.update({"Authorization": f"Bearer {r.json()['token']}"})
    for sid in created_scan_ids:
        s.delete(f"{API}/scans/{sid}", timeout=60)


class TestScanAnalyze:
    """AI Vision analysis via Gemini 3 Flash (emergentintegrations)."""

    def test_analyze_label_image(self, api_client, label_image_b64):
        r = api_client.post(
            f"{API}/scan/analyze",
            json={
                "image_base64": label_image_b64,
                "product_hint": "Whole Wheat Flour 1 kg pack",
                "panel_area_sq_cm": 180.0,
                "category": "FMCG Packaged Food",
            },
            timeout=180,
        )
        assert r.status_code == 200, f"analyze failed {r.status_code}: {r.text[:500]}"
        data = r.json()
        assert "Gemini" in data.get("engine_used", ""), f"engine_used={data.get('engine_used')}"
        decl = data["declarations"]
        assert isinstance(decl, dict) and len(decl) >= 10
        # Compliance evaluation must be present
        for key in ["compliance_status", "compliance_score", "violations", "violations_count",
                    "table_ii_font_check", "verified_declarations"]:
            assert key in data, f"missing key {key}"
        assert data["compliance_status"] in ("Compliant", "Partially Compliant", "Non-Compliant")
        assert 0 <= data["compliance_score"] <= 100
        assert data["table_ii_font_check"]["panel_area_sq_cm"] == 180.0
        assert isinstance(data["ocr_raw_text"], str)
        # OCR should pick up some label text
        combined = (data["ocr_raw_text"] + str(decl)).lower()
        assert any(tok in combined for tok in ["kg", "mrp", "flour", "atta"]), combined[:300]

    def test_analyze_real_product_photo(self, api_client, product_photo_b64):
        r = api_client.post(
            f"{API}/scan/analyze",
            json={"image_base64": product_photo_b64, "product_hint": "Retail packaged product"},
            timeout=180,
        )
        assert r.status_code == 200, f"{r.status_code}: {r.text[:400]}"
        data = r.json()
        assert "declarations" in data and "compliance_status" in data
        assert "Gemini" in data.get("engine_used", "")

    def test_analyze_invalid_base64(self, api_client):
        r = api_client.post(
            f"{API}/scan/analyze",
            json={"image_base64": "not-a-real-base64-image!!!"},
            timeout=120,
        )
        body = r.text
        assert r.status_code == 502, f"expected 502 for invalid image, got {r.status_code}: {body[:400]}"
        assert "Heritage" not in body, "fabricated mock data leaked in error response"
        # NOTE: the Cloudflare/ingress layer replaces a 502 body with its own HTML error page,
        # so the FastAPI JSON detail never reaches the browser. Documented as a UX issue.
        if "application/json" in r.headers.get("Content-Type", ""):
            detail = r.json().get("detail", "")
            assert isinstance(detail, str) and len(detail) > 10, detail
        else:
            assert "502" in body or "Bad gateway" in body

    def test_analyze_non_label_image(self, api_client, non_label_image_b64):
        """A random non-label image must not produce fabricated 'Compliant' mock data."""
        r = api_client.post(
            f"{API}/scan/analyze",
            json={"image_base64": non_label_image_b64},
            timeout=180,
        )
        assert r.status_code in (200, 502), f"{r.status_code}: {r.text[:300]}"
        body = r.text
        assert "Heritage Consumer Products" not in body, "fabricated mock declarations returned"
        if r.status_code == 200:
            data = r.json()
            assert "Fallback" not in data.get("engine_used", ""), data.get("engine_used")
            assert data["compliance_status"] in ("Compliant", "Partially Compliant", "Non-Compliant")

    def test_analyze_missing_field(self, api_client):
        r = api_client.post(f"{API}/scan/analyze", json={}, timeout=60)
        assert r.status_code == 422


class TestScanSaveAndRepository:
    def test_save_compliant_scan_and_persist(self, auth_client, created_scan_ids):
        payload = {
            "brand_name": "TEST_Shuddh Bharat Atta",
            "commodity_name": "Whole Wheat Flour",
            "category": "FMCG Packaged Food",
            "panel_area_sq_cm": 180.0,
            "numeral_height_mm": 4.0,
            "letter_height_mm": 2.5,
            "declarations": compliant_declarations(),
            "jurisdiction": "Maharashtra Zone 1",
            "inspector_notes": "TEST_baseline compliant case",
        }
        r = auth_client.post(f"{API}/scan/save", json=payload, timeout=90)
        assert r.status_code == 200, r.text[:400]
        doc = r.json()
        created_scan_ids.append(doc["id"])
        assert doc["id"].startswith("SCAN-")
        assert "_id" not in doc
        assert doc["compliance_status"] == "Compliant", f"{doc['compliance_status']} score={doc['compliance_score']} violations={[v['title'] for v in doc['violations']]}"
        assert doc["compliance_score"] == 100
        assert doc["violations_count"] == 0
        assert doc["review_status"] == "Verified"
        assert doc["enforcement_notice_issued"] is False
        assert doc["jurisdiction"] == "Maharashtra Zone 1"

        # GET verify persistence
        g = auth_client.get(f"{API}/scans/{doc['id']}", timeout=60)
        assert g.status_code == 200
        fetched = g.json()
        assert fetched["brand_name"] == payload["brand_name"]
        assert fetched["compliance_score"] == 100
        assert fetched["declarations"]["batch_number"] == "SBA2026C77"
        assert "_id" not in fetched

    def test_save_non_compliant_scan(self, auth_client, created_scan_ids):
        bad = compliant_declarations()
        bad.update({
            "manufacturer_address": "Some Street, Pune",  # no PIN
            "net_quantity_unit": "gms",
            "mrp_raw": "MRP 68.00",
            "taxes_inclusive_declared": False,
            "unit_sale_price": "",
            "manufacturing_date": "12/2030",
            "consumer_care_phone": "",
            "consumer_care_email": "",
            "consumer_care_details": "",
            "batch_number": "",
            "country_of_origin": "",
        })
        r = auth_client.post(f"{API}/scan/save", json={
            "brand_name": "TEST_Violation Brand",
            "commodity_name": "Snack Mix",
            "category": "FMCG Packaged Food",
            "panel_area_sq_cm": 180.0,
            "numeral_height_mm": 1.2,
            "letter_height_mm": 0.9,
            "declarations": bad,
        }, timeout=90)
        assert r.status_code == 200, r.text[:400]
        doc = r.json()
        created_scan_ids.append(doc["id"])
        titles = " | ".join(v["title"] for v in doc["violations"])
        assert doc["compliance_status"] == "Non-Compliant", f"score={doc['compliance_score']} {titles}"
        assert doc["enforcement_notice_issued"] is True
        assert doc["review_status"] == "Action Required"
        expected = ["Non-Standard Unit", "Inclusive of all taxes", "Unit Sale Price",
                    "Post-Dated", "PIN code", "Consumer Care", "Country of Origin",
                    "Batch", "Numeral Height", "Letter Height"]
        missing = [e for e in expected if e.lower() not in titles.lower()]
        assert not missing, f"Rule engine missed violations {missing}. Got: {titles}"

    def test_update_existing_scan_recomputes_compliance(self, auth_client, created_scan_ids):
        # create
        base = auth_client.post(f"{API}/scan/save", json={
            "brand_name": "TEST_Update Brand",
            "commodity_name": "Cooking Oil",
            "category": "Edible Oils",
            "declarations": compliant_declarations(),
        }, timeout=90).json()
        scan_id = base["id"]
        created_scan_ids.append(scan_id)
        assert base["compliance_score"] == 100

        broken = compliant_declarations()
        broken["country_of_origin"] = ""
        upd = auth_client.post(f"{API}/scan/save", json={
            "id": scan_id,
            "brand_name": "TEST_Update Brand v2",
            "commodity_name": "Cooking Oil",
            "category": "Edible Oils",
            "declarations": broken,
        }, timeout=90)
        assert upd.status_code == 200
        assert upd.json()["compliance_score"] == 75

        g = auth_client.get(f"{API}/scans/{scan_id}", timeout=60).json()
        assert g["brand_name"] == "TEST_Update Brand v2"
        assert g["compliance_score"] == 75
        assert g["critical_violations"] == 1

    def test_list_scans_and_filters(self, auth_client):
        r = auth_client.get(f"{API}/scans", timeout=60)
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body["total"], int) and body["total"] >= 1
        assert isinstance(body["scans"], list)
        assert all("_id" not in s for s in body["scans"])

        # search filter
        s = auth_client.get(f"{API}/scans", params={"search": "TEST_Shuddh"}, timeout=60).json()
        assert s["total"] >= 1
        for sc in s["scans"]:
            haystack = (sc["brand_name"] + sc["commodity_name"] + sc["id"] +
                        str(sc.get("declarations", {}).get("manufacturer_name", ""))).lower()
            assert "test_shuddh" in haystack, f"search returned unrelated record {sc['id']}"

        # status filter
        st = auth_client.get(f"{API}/scans", params={"status": "Non-Compliant"}, timeout=60).json()
        assert all(sc["compliance_status"] == "Non-Compliant" for sc in st["scans"])

        # category filter
        cat = auth_client.get(f"{API}/scans", params={"category": "Edible Oils"}, timeout=60).json()
        assert all(sc["category"] == "Edible Oils" for sc in cat["scans"])

        # jurisdiction filter
        jur = auth_client.get(f"{API}/scans", params={"jurisdiction": "Maharashtra Zone 1"}, timeout=60).json()
        assert all(sc["jurisdiction"] == "Maharashtra Zone 1" for sc in jur["scans"])

        # pagination
        pag = auth_client.get(f"{API}/scans", params={"limit": 2, "skip": 0}, timeout=60).json()
        assert len(pag["scans"]) <= 2

    def test_get_unknown_scan_404(self, auth_client):
        r = auth_client.get(f"{API}/scans/SCAN-DOES-NOT-EXIST", timeout=60)
        assert r.status_code == 404

    def test_scan_actions(self, auth_client, created_scan_ids):
        doc = auth_client.post(f"{API}/scan/save", json={
            "brand_name": "TEST_Action Brand",
            "commodity_name": "Detergent Powder",
            "category": "Household Care",
            "declarations": compliant_declarations(),
        }, timeout=90).json()
        scan_id = doc["id"]
        created_scan_ids.append(scan_id)

        r = auth_client.post(f"{API}/scans/{scan_id}/action", json={"action": "issue_notice", "notes": "TEST notice"}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["enforcement_notice_issued"] is True
        assert d["review_status"] == "Notice Issued under Sec 36"
        assert "TEST notice" in d["inspector_notes"]
        assert "_id" not in d

        for action, expected in [
            ("mark_verified", "Verified"),
            ("flag_lab_test", "Flagged for Physical Lab Metrology Verification"),
            ("archive", "Archived Case"),
        ]:
            rr = auth_client.post(f"{API}/scans/{scan_id}/action", json={"action": action}, timeout=60)
            assert rr.status_code == 200, f"{action}: {rr.text[:200]}"
            assert rr.json()["review_status"] == expected
            g = auth_client.get(f"{API}/scans/{scan_id}", timeout=60).json()
            assert g["review_status"] == expected, f"{action} not persisted"

    def test_action_requires_auth(self, api_client, created_scan_ids):
        if not created_scan_ids:
            pytest.skip("no scan created")
        r = requests.post(f"{API}/scans/{created_scan_ids[0]}/action", json={"action": "archive"}, timeout=60)
        assert r.status_code in (401, 403)

    def test_unknown_action_is_rejected(self, auth_client, created_scan_ids):
        if not created_scan_ids:
            pytest.skip("no scan created")
        scan_id = created_scan_ids[0]
        before = auth_client.get(f"{API}/scans/{scan_id}", timeout=60).json()["review_status"]
        r = auth_client.post(f"{API}/scans/{scan_id}/action", json={"action": "bogus_action"}, timeout=60)
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text[:300]}"
        detail = r.json().get("detail", "")
        for act in ["archive", "flag_lab_test", "issue_notice", "mark_verified"]:
            assert act in detail, f"allowed action '{act}' missing from error detail: {detail}"
        after = auth_client.get(f"{API}/scans/{scan_id}", timeout=60).json()["review_status"]
        assert after == before, "state changed despite invalid action"
