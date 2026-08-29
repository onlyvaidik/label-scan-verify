"""Unit tests for compliance_engine: Rule 6 checks and Table-II font-size brackets."""
import sys

sys.path.insert(0, "/app/backend")

from compliance_engine import (  # noqa: E402
    evaluate_table_ii_font_size,
    validate_declarations_against_lmpc_rules,
)


def base_declarations(**over):
    d = {
        "manufacturer_name": "Shuddh Foods Pvt Ltd",
        "manufacturer_address": "Plot 44, MIDC, Pune, Maharashtra - 411019",
        "commodity_name": "Whole Wheat Flour",
        "net_quantity_value": 1,
        "net_quantity_unit": "kg",
        "net_quantity_raw": "1 kg",
        "unit_sale_price": "Rs 0.068 per g",
        "mrp_value": 68.0,
        "mrp_raw": "MRP Rs 68.00 (incl. of all taxes)",
        "taxes_inclusive_declared": True,
        "manufacturing_date": "03/2026",
        "consumer_care_phone": "1800-200-4455",
        "consumer_care_email": "care@shuddhfoods.in",
        "country_of_origin": "India",
        "batch_number": "B77",
    }
    d.update(over)
    return d


def rule_ids(res):
    return [v["rule_id"] for v in res["violations"]]


class TestTableII:
    def test_brackets(self):
        assert evaluate_table_ii_font_size(40, 1.0, 1.0)["is_compliant"] is True
        assert evaluate_table_ii_font_size(40, 0.9, 1.0)["numeral_pass"] is False
        b = evaluate_table_ii_font_size(180, 2.0, 1.5)
        assert b["required_numeral_height_mm"] == 2.0 and b["is_compliant"] is True
        b2 = evaluate_table_ii_font_size(500, 3.9, 2.0)
        assert b2["required_numeral_height_mm"] == 4.0 and b2["numeral_pass"] is False
        b3 = evaluate_table_ii_font_size(5000, 6.0, 3.0)
        assert b3["bracket_label"] == "> 1000 sq. cm" and b3["is_compliant"] is True


class TestRule6Engine:
    def test_fully_compliant(self):
        res = validate_declarations_against_lmpc_rules(base_declarations(), 180.0, 4.0, 2.0)
        assert res["violations"] == [], [v["title"] for v in res["violations"]]
        assert res["compliance_status"] == "Compliant"
        assert res["compliance_score"] == 100
        assert len(res["verified_declarations"]) >= 8

    def test_none_values_do_not_crash(self):
        d = {k: None for k in base_declarations()}
        res = validate_declarations_against_lmpc_rules(d, 180.0, 1.0, 0.5)
        assert res["compliance_status"] == "Non-Compliant"
        assert res["violations_count"] >= 8

    def test_missing_mrp_tax_inclusion(self):
        res = validate_declarations_against_lmpc_rules(
            base_declarations(mrp_raw="MRP Rs 68.00", taxes_inclusive_declared=False), 180.0, 4.0, 2.0)
        assert "LMPC-RULE-6-1-E" in rule_ids(res)

    def test_non_si_units(self):
        for bad in ["gms", "kgs", "ltr"]:
            res = validate_declarations_against_lmpc_rules(
                base_declarations(net_quantity_unit=bad), 180.0, 4.0, 2.0)
            assert "LMPC-RULE-6-1-C" in rule_ids(res), f"unit '{bad}' not flagged"

    def test_post_dated_mfg(self):
        res = validate_declarations_against_lmpc_rules(
            base_declarations(manufacturing_date="05/2031"), 180.0, 4.0, 2.0)
        v = [x for x in res["violations"] if x["rule_id"] == "LMPC-RULE-6-1-D"]
        assert v and v[0]["severity"] == "Critical"

    def test_missing_pin_in_address(self):
        res = validate_declarations_against_lmpc_rules(
            base_declarations(manufacturer_address="MIDC Road, Pune, Maharashtra"), 180.0, 4.0, 2.0)
        assert any("PIN" in v["title"] for v in res["violations"])

    def test_missing_consumer_care(self):
        res = validate_declarations_against_lmpc_rules(
            base_declarations(consumer_care_phone="", consumer_care_email="", consumer_care_details=""),
            180.0, 4.0, 2.0)
        assert "LMPC-RULE-6-1-F" in rule_ids(res)

    def test_missing_usp(self):
        res = validate_declarations_against_lmpc_rules(base_declarations(unit_sale_price=""), 180.0, 4.0, 2.0)
        assert "LMPC-RULE-6-1-DA" in rule_ids(res)

    def test_font_below_threshold(self):
        res = validate_declarations_against_lmpc_rules(base_declarations(), 180.0, 1.0, 0.5)
        table_v = [v for v in res["violations"] if v["rule_id"] == "LMPC-RULE-7-TABLE-2"]
        assert len(table_v) == 2
        assert res["table_ii_font_check"]["is_compliant"] is False

    def test_score_weighting(self):
        # one critical (country of origin) = -25
        res = validate_declarations_against_lmpc_rules(base_declarations(country_of_origin=""), 180.0, 4.0, 2.0)
        assert res["compliance_score"] == 75
        assert res["critical_violations"] == 1
        assert res["compliance_status"] == "Partially Compliant"
        # one minor (batch) = -5 -> 95 but still not compliant? minor only => compliant
        res2 = validate_declarations_against_lmpc_rules(base_declarations(batch_number=""), 180.0, 4.0, 2.0)
        assert res2["compliance_score"] == 95
        assert res2["minor_violations"] == 1
        assert res2["compliance_status"] == "Compliant"
