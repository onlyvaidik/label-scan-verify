import re
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# Minimum font size requirements per Table-II of Legal Metrology (Packaged Commodities) Rules, 2011
# Area of Principal Display Panel (PDP) in sq cm -> Minimum height of numeral / letter in mm
TABLE_II_REQUIREMENTS = [
    {"max_area_sq_cm": 50, "min_numeral_height_mm": 1.0, "min_numeral_blown_mm": 2.0, "min_letter_height_mm": 1.0, "area_label": "≤ 50 sq. cm"},
    {"max_area_sq_cm": 200, "min_numeral_height_mm": 2.0, "min_numeral_blown_mm": 4.0, "min_letter_height_mm": 1.5, "area_label": "50 to 200 sq. cm"},
    {"max_area_sq_cm": 1000, "min_numeral_height_mm": 4.0, "min_numeral_blown_mm": 6.0, "min_letter_height_mm": 2.0, "area_label": "200 to 1000 sq. cm"},
    {"max_area_sq_cm": 999999, "min_numeral_height_mm": 6.0, "min_numeral_blown_mm": 8.0, "min_letter_height_mm": 3.0, "area_label": "> 1000 sq. cm"},
]

STANDARD_UNITS = ["g", "kg", "ml", "l", "m", "cm", "mm", "n", "u", "pieces", "units"]
INVALID_UNITS = ["gms", "gm", "kgs", "ml.", "lts", "ltr", "pcs"]

DEFAULT_STATUTORY_RULES = [
    {
        "rule_id": "LMPC-RULE-6-1-A",
        "rule_name": "Manufacturer / Packer / Importer Name & Complete Address",
        "section": "Rule 6(1)(a)",
        "description": "Every package shall bear name and complete address of manufacturer/packer/importer including city, state and PIN code.",
        "severity": "Critical",
        "penalty_clause": "Section 36(1) of Legal Metrology Act, 2009: Fine up to ₹25,000 for 1st offence, ₹50,000 for 2nd offence, or imprisonment up to 1 year.",
        "mandatory": True,
        "category": "Identity & Origin"
    },
    {
        "rule_id": "LMPC-RULE-6-1-B",
        "rule_name": "Generic or Common Name of Commodity",
        "section": "Rule 6(1)(b)",
        "description": "The common or generic name of the commodity contained in the package must be clearly stated on the Principal Display Panel.",
        "severity": "Major",
        "penalty_clause": "Section 36(1) of Legal Metrology Act, 2009: Fine up to ₹25,000.",
        "mandatory": True,
        "category": "Product Identification"
    },
    {
        "rule_id": "LMPC-RULE-6-1-C",
        "rule_name": "Net Quantity in Standard SI Units",
        "section": "Rule 6(1)(c)",
        "description": "Net quantity in standard SI metric units (g, kg, ml, l, N, U) without prohibited symbols (e.g., 'gms', 'kgs', 'ml.').",
        "severity": "Critical",
        "penalty_clause": "Section 36(1) & Section 30 of Legal Metrology Act, 2009: Fine up to ₹25,000.",
        "mandatory": True,
        "category": "Quantity & Measurement"
    },
    {
        "rule_id": "LMPC-RULE-6-1-D",
        "rule_name": "Month and Year of Manufacture / Packing / Import",
        "section": "Rule 6(1)(d)",
        "description": "Month and year in which commodity is manufactured, pre-packed, or imported (Format MM/YYYY or Month YYYY). Cannot be post-dated.",
        "severity": "Major",
        "penalty_clause": "Section 36(1) of Legal Metrology Act, 2009: Fine up to ₹25,000.",
        "mandatory": True,
        "category": "Dates & Shelf Life"
    },
    {
        "rule_id": "LMPC-RULE-6-1-E",
        "rule_name": "Maximum Retail Price (MRP) Declaration Format",
        "section": "Rule 6(1)(e)",
        "description": "MRP declaration must state 'Maximum Retail Price' or 'MRP Rs. / ₹ ... (incl. of all taxes)'. Rounding and all tax inclusions are mandatory.",
        "severity": "Critical",
        "penalty_clause": "Section 36(1) of Legal Metrology Act, 2009: Fine up to ₹25,000. Overcharging is punishable under Section 36(2).",
        "mandatory": True,
        "category": "Pricing & Taxation"
    },
    {
        "rule_id": "LMPC-RULE-6-1-DA",
        "rule_name": "Unit Sale Price (USP)",
        "section": "Rule 6(1)(da)",
        "description": "Unit sale price in Rupees per gram/ml or per piece for packages containing more than one unit (e.g., ₹0.75 / g).",
        "severity": "Major",
        "penalty_clause": "LMPC Rules 2011 Amendment (2022): Fine up to ₹25,000.",
        "mandatory": True,
        "category": "Pricing & Taxation"
    },
    {
        "rule_id": "LMPC-RULE-6-1-F",
        "rule_name": "Consumer Care Helpline & Contact Details",
        "section": "Rule 6(1)(f)",
        "description": "Name, address, working telephone number, and email address of person/office to be contacted in case of consumer complaints.",
        "severity": "Major",
        "penalty_clause": "Section 36(1) of Legal Metrology Act, 2009: Fine up to ₹25,000.",
        "mandatory": True,
        "category": "Consumer Redressal"
    },
    {
        "rule_id": "LMPC-RULE-6-1-G",
        "rule_name": "Country of Origin",
        "section": "Rule 6(1)(g)",
        "description": "Country of origin must be clearly declared on package (e.g., 'Country of Origin: India' or 'Made in [Country]'). Mandatory for e-commerce and retail.",
        "severity": "Critical",
        "penalty_clause": "Section 36(1) of Legal Metrology Act, 2009: Fine up to ₹25,000.",
        "mandatory": True,
        "category": "Identity & Origin"
    },
    {
        "rule_id": "LMPC-RULE-6-1-H",
        "rule_name": "Batch / Lot / Identification Number",
        "section": "Rule 6(1)(h)",
        "description": "Distinct batch number, lot number, or code identifying the pre-packaged commodity lot.",
        "severity": "Minor",
        "penalty_clause": "Section 36(1) of Legal Metrology Act, 2009: Fine up to ₹10,000.",
        "mandatory": True,
        "category": "Product Identification"
    },
    {
        "rule_id": "LMPC-RULE-6-1-I",
        "rule_name": "Best Before / Expiry / Use By Date",
        "section": "Rule 6(1)(i)",
        "description": "Best before or use by date for commodities liable to deterioration or food/cosmetic items.",
        "severity": "Major",
        "penalty_clause": "Section 36(1) of Legal Metrology Act, 2009: Fine up to ₹25,000.",
        "mandatory": False,
        "category": "Dates & Shelf Life"
    },
    {
        "rule_id": "LMPC-RULE-7-TABLE-2",
        "rule_name": "Table-II Font Size & Principal Display Panel (PDP) Height",
        "section": "Rule 7 & Table-II",
        "description": "Height of numerals and letters declaring Net Quantity and MRP must strictly comply with Table-II based on panel area.",
        "severity": "Major",
        "penalty_clause": "Rule 7 & Section 36(1): Fine up to ₹25,000.",
        "mandatory": True,
        "category": "Typography & Readability"
    },
    {
        "rule_id": "LMPC-RULE-9-LEGIBILITY",
        "rule_name": "Conspicuousness & Contrasting Background",
        "section": "Rule 9",
        "description": "All mandatory declarations must be conspicuous, legible, and printed in color clearly contrasting with background.",
        "severity": "Minor",
        "penalty_clause": "Rule 9 & Section 36(1): Fine up to ₹10,000.",
        "mandatory": True,
        "category": "Typography & Readability"
    }
]


def evaluate_table_ii_font_size(panel_area_sq_cm: float, numeral_height_mm: float, letter_height_mm: float) -> Dict[str, Any]:
    """Validates numeral and letter height against Table-II based on PDP area."""
    target_bracket = TABLE_II_REQUIREMENTS[-1]
    for bracket in TABLE_II_REQUIREMENTS:
        if panel_area_sq_cm <= bracket["max_area_sq_cm"]:
            target_bracket = bracket
            break
            
    min_numeral_req = target_bracket["min_numeral_height_mm"]
    min_letter_req = target_bracket["min_letter_height_mm"]
    
    numeral_pass = numeral_height_mm >= min_numeral_req
    letter_pass = letter_height_mm >= min_letter_req
    is_compliant = numeral_pass and letter_pass
    
    return {
        "panel_area_sq_cm": panel_area_sq_cm,
        "bracket_label": target_bracket["area_label"],
        "required_numeral_height_mm": min_numeral_req,
        "measured_numeral_height_mm": round(numeral_height_mm, 2),
        "numeral_pass": numeral_pass,
        "required_letter_height_mm": min_letter_req,
        "measured_letter_height_mm": round(letter_height_mm, 2),
        "letter_pass": letter_pass,
        "is_compliant": is_compliant
    }


def _s(val: Any) -> str:
    """Safely coerce any value (None, int, float, str) to a stripped string."""
    if val is None:
        return ""
    return str(val).strip()


def validate_declarations_against_lmpc_rules(
    declarations: Dict[str, Any],
    panel_area_sq_cm: float = 120.0,
    numeral_height_mm: float = 2.4,
    letter_height_mm: float = 1.6
) -> Dict[str, Any]:
    """Comprehensive Legal Metrology compliance validation engine."""
    violations: List[Dict[str, Any]] = []
    verified_items: List[Dict[str, Any]] = []
    
    # 1. Manufacturer Name & Address
    mfg_name = _s(declarations.get("manufacturer_name"))
    mfg_address = _s(declarations.get("manufacturer_address"))
    if not mfg_name or not mfg_address:
        violations.append({
            "rule_id": "LMPC-RULE-6-1-A",
            "rule_name": "Manufacturer Name & Address",
            "section": "Rule 6(1)(a)",
            "severity": "Critical",
            "title": "Missing Manufacturer Declaration",
            "description": "Name or complete address of the manufacturer is missing from the package label.",
            "recommendation": "Clearly state complete manufacturer name, street address, city, state, and 6-digit PIN code.",
            "penalty_clause": "Section 36(1) of Legal Metrology Act, 2009: Fine up to ₹25,000."
        })
    else:
        # Address completeness: PIN code check
        pin_match = re.search(r"\b\d{6}\b", mfg_address)
        if not pin_match:
            violations.append({
                "rule_id": "LMPC-RULE-6-1-A",
                "rule_name": "Manufacturer Address Completeness",
                "section": "Rule 6(1)(a)",
                "severity": "Major",
                "title": "Incomplete Manufacturer Address (Missing PIN code)",
                "description": f"Manufacturer address '{mfg_address}' lacks a valid 6-digit postal PIN code.",
                "recommendation": "Provide full address including locality, state, and 6-digit PIN code as required by statutory rules.",
                "penalty_clause": "Section 36(1) of Legal Metrology Act, 2009."
            })
        else:
            verified_items.append({
                "rule_id": "LMPC-RULE-6-1-A",
                "title": "Manufacturer Details Valid",
                "detail": f"{mfg_name}, {mfg_address}"
            })

    # 2. Generic / Common Commodity Name
    commodity_name = _s(declarations.get("commodity_name"))
    if not commodity_name:
        violations.append({
            "rule_id": "LMPC-RULE-6-1-B",
            "rule_name": "Common / Generic Name of Commodity",
            "section": "Rule 6(1)(b)",
            "severity": "Major",
            "title": "Missing Generic Commodity Name",
            "description": "The generic or common identity of the packaged product is missing or ambiguously represented.",
            "recommendation": "Declare generic name (e.g., 'Wheat Flour', 'Biscuits', 'Body Lotion') in prominent lettering on PDP.",
            "penalty_clause": "Section 36(1) of Legal Metrology Act, 2009."
        })
    else:
        verified_items.append({
            "rule_id": "LMPC-RULE-6-1-B",
            "title": "Generic Name Valid",
            "detail": commodity_name
        })

    # 3. Net Quantity & Standard Unit Check
    net_qty_val = declarations.get("net_quantity_value")
    net_qty_unit = _s(declarations.get("net_quantity_unit")).lower()
    net_qty_raw = _s(declarations.get("net_quantity_raw"))
    
    if not net_qty_raw and net_qty_val is None:
        violations.append({
            "rule_id": "LMPC-RULE-6-1-C",
            "rule_name": "Net Quantity Declaration",
            "section": "Rule 6(1)(c)",
            "severity": "Critical",
            "title": "Missing Net Quantity Declaration",
            "description": "Net quantity is not declared on the package Principal Display Panel.",
            "recommendation": "Print net quantity with appropriate standard SI metric unit.",
            "penalty_clause": "Section 36(1) of Legal Metrology Act, 2009."
        })
    else:
        # Unit compliance check
        unit_to_check = net_qty_unit.lower() if net_qty_unit else net_qty_raw.lower()
        has_invalid_unit = any(bad in unit_to_check.split() for bad in INVALID_UNITS) or ("gms" in unit_to_check) or ("kgs" in unit_to_check)
        if has_invalid_unit:
            violations.append({
                "rule_id": "LMPC-RULE-6-1-C",
                "rule_name": "Standard SI Metric Unit Violation",
                "section": "Rule 6(1)(c)",
                "severity": "Major",
                "title": f"Non-Standard Unit Symbol Used ({net_qty_unit or net_qty_raw})",
                "description": "Use of prohibited symbols like 'gms', 'kgs', 'ml.' violates Rule 6(1)(c). Only 'g', 'kg', 'ml', 'l', 'N' are permitted.",
                "recommendation": "Replace non-standard unit symbols with standard SI symbols (e.g., use 'g' instead of 'gms').",
                "penalty_clause": "Section 36(1) of Legal Metrology Act, 2009."
            })
        else:
            verified_items.append({
                "rule_id": "LMPC-RULE-6-1-C",
                "title": "Net Quantity Metric Unit Valid",
                "detail": f"{net_qty_val} {net_qty_unit}" if net_qty_val else net_qty_raw
            })

    # 4. MRP Declaration & Taxes Inclusion
    mrp_val = declarations.get("mrp_value")
    mrp_raw = _s(declarations.get("mrp_raw"))
    taxes_incl = declarations.get("taxes_inclusive_declared", False)
    
    if not mrp_raw and mrp_val is None:
        violations.append({
            "rule_id": "LMPC-RULE-6-1-E",
            "rule_name": "Maximum Retail Price (MRP)",
            "section": "Rule 6(1)(e)",
            "severity": "Critical",
            "title": "Missing MRP Declaration",
            "description": "Maximum Retail Price is absent from the packaging.",
            "recommendation": "Print 'MRP Rs. / ₹ ... (incl. of all taxes)' in conspicuous location.",
            "penalty_clause": "Section 36(1) of Legal Metrology Act, 2009: Fine up to ₹25,000."
        })
    else:
        mrp_str = mrp_raw.lower()
        has_tax_phrase = any(w in mrp_str for w in ["incl", "tax", "inclusive", "all taxes"]) or taxes_incl
        if not has_tax_phrase:
            violations.append({
                "rule_id": "LMPC-RULE-6-1-E",
                "rule_name": "MRP Tax Inclusion Declaration",
                "section": "Rule 6(1)(e)",
                "severity": "Major",
                "title": "Missing 'Inclusive of all taxes' in MRP",
                "description": "MRP declaration lacks statutory phrase '(inclusive of all taxes)' or 'incl. of all taxes'.",
                "recommendation": "Append '(incl. of all taxes)' adjacent to the MRP value.",
                "penalty_clause": "Section 36(1) of Legal Metrology Act, 2009."
            })
        else:
            verified_items.append({
                "rule_id": "LMPC-RULE-6-1-E",
                "title": "MRP & Tax Inclusivity Valid",
                "detail": mrp_raw or f"₹ {mrp_val} (incl. of all taxes)"
            })

    # 5. Unit Sale Price (USP)
    usp_declared = _s(declarations.get("unit_sale_price"))
    # If net quantity is more than 1 unit/g/ml, USP is mandatory
    if not usp_declared:
        violations.append({
            "rule_id": "LMPC-RULE-6-1-DA",
            "rule_name": "Unit Sale Price (USP)",
            "section": "Rule 6(1)(da)",
            "severity": "Major",
            "title": "Missing Unit Sale Price (USP)",
            "description": "Unit sale price (e.g. ₹ per g / per ml / per piece) is not declared on pre-packaged commodity.",
            "recommendation": "Print Unit Sale Price as '₹ X.XX per g' or '₹ X.XX per ml' rounded to two decimal places.",
            "penalty_clause": "LMPC Rules 2011 (Amendment): Fine up to ₹25,000."
        })
    else:
        verified_items.append({
            "rule_id": "LMPC-RULE-6-1-DA",
            "title": "Unit Sale Price Valid",
            "detail": usp_declared
        })

    # 6. Month and Year of Manufacture / Packing / Import
    mfg_date_raw = _s(declarations.get("manufacturing_date"))
    packing_date_raw = _s(declarations.get("packing_date"))
    import_date_raw = _s(declarations.get("import_date"))
    date_present = mfg_date_raw or packing_date_raw or import_date_raw
    
    if not date_present:
        violations.append({
            "rule_id": "LMPC-RULE-6-1-D",
            "rule_name": "Month & Year of Manufacture / Packing",
            "section": "Rule 6(1)(d)",
            "severity": "Major",
            "title": "Missing Manufacturing / Packing Date",
            "description": "Month and year of manufacture, packing, or import is not declared on label.",
            "recommendation": "Declare date in MM/YYYY format or 'Month YYYY' with 'Mfg Date:' or 'Packed on:'.",
            "penalty_clause": "Section 36(1) of Legal Metrology Act, 2009."
        })
    else:
        # Check for future dating
        current_year = datetime.now(timezone.utc).year
        current_month = datetime.now(timezone.utc).month
        date_match = re.search(r"(\d{1,2})[/.-](\d{4})", date_present)
        if date_match:
            m = int(date_match.group(1))
            y = int(date_match.group(2))
            if y > current_year or (y == current_year and m > current_month + 1):
                violations.append({
                    "rule_id": "LMPC-RULE-6-1-D",
                    "rule_name": "Post-Dated Manufacturing Declaration",
                    "section": "Rule 6(1)(d)",
                    "severity": "Critical",
                    "title": f"Future / Post-Dated Manufacturing Date ({date_present})",
                    "description": f"Manufacturing date {date_present} is in the future. Post-dating is a severe deceptive trade violation.",
                    "recommendation": "Rectify manufacturing batch dates immediately. Pre-dating/post-dating is prohibited.",
                    "penalty_clause": "Section 36(1) of Legal Metrology Act, 2009: Fine up to ₹25,000 and seizure of stock."
                })
            else:
                verified_items.append({
                    "rule_id": "LMPC-RULE-6-1-D",
                    "title": "Manufacturing / Packing Date Valid",
                    "detail": date_present
                })
        else:
            verified_items.append({
                "rule_id": "LMPC-RULE-6-1-D",
                "title": "Manufacturing Date Present",
                "detail": date_present
            })

    # 7. Consumer Care Details
    consumer_care_phone = _s(declarations.get("consumer_care_phone"))
    consumer_care_email = _s(declarations.get("consumer_care_email"))
    consumer_care_raw = _s(declarations.get("consumer_care_details"))
    
    if not consumer_care_phone and not consumer_care_email and not consumer_care_raw:
        violations.append({
            "rule_id": "LMPC-RULE-6-1-F",
            "rule_name": "Consumer Care Helpline Details",
            "section": "Rule 6(1)(f)",
            "severity": "Major",
            "title": "Missing Consumer Care Contact Details",
            "description": "Consumer helpline phone number or email ID is completely missing.",
            "recommendation": "Provide telephone helpline number and official consumer support email address.",
            "penalty_clause": "Section 36(1) of Legal Metrology Act, 2009."
        })
    elif not consumer_care_email and not consumer_care_phone:
        violations.append({
            "rule_id": "LMPC-RULE-6-1-F",
            "rule_name": "Incomplete Consumer Care Channels",
            "section": "Rule 6(1)(f)",
            "severity": "Minor",
            "title": "Single-Channel Consumer Care Only",
            "description": "Both working telephone and email ID are recommended for consumer redressal.",
            "recommendation": "Include both toll-free/telephone number and customer care email.",
            "penalty_clause": "Rule 6(1)(f) advisory."
        })
    else:
        verified_items.append({
            "rule_id": "LMPC-RULE-6-1-F",
            "title": "Consumer Care Redressal Details Valid",
            "detail": f"Phone: {consumer_care_phone or 'N/A'}, Email: {consumer_care_email or 'N/A'}"
        })

    # 8. Country of Origin
    country_origin = _s(declarations.get("country_of_origin"))
    if not country_origin:
        violations.append({
            "rule_id": "LMPC-RULE-6-1-G",
            "rule_name": "Country of Origin Declaration",
            "section": "Rule 6(1)(g)",
            "severity": "Critical",
            "title": "Missing Country of Origin",
            "description": "Country of origin is not declared on the package.",
            "recommendation": "Print 'Country of Origin: India' or respective country of manufacture.",
            "penalty_clause": "Section 36(1) of Legal Metrology Act, 2009."
        })
    else:
        verified_items.append({
            "rule_id": "LMPC-RULE-6-1-G",
            "title": "Country of Origin Declared",
            "detail": country_origin
        })

    # 9. Batch / Lot Number
    batch_num = _s(declarations.get("batch_number"))
    if not batch_num:
        violations.append({
            "rule_id": "LMPC-RULE-6-1-H",
            "rule_name": "Batch / Lot Number",
            "section": "Rule 6(1)(h)",
            "severity": "Minor",
            "title": "Missing Batch / Lot Number",
            "description": "Batch or lot code is missing or illegible.",
            "recommendation": "Declare distinct batch or lot code with 'Batch No.' prefix.",
            "penalty_clause": "Section 36(1) of Legal Metrology Act, 2009."
        })
    else:
        verified_items.append({
            "rule_id": "LMPC-RULE-6-1-H",
            "title": "Batch Identification Valid",
            "detail": batch_num
        })

    # 10. Table-II Font Size & PDP Verification
    font_check = evaluate_table_ii_font_size(panel_area_sq_cm, numeral_height_mm, letter_height_mm)
    if not font_check["numeral_pass"]:
        violations.append({
            "rule_id": "LMPC-RULE-7-TABLE-2",
            "rule_name": "Table-II Numeral Height Substandard",
            "section": "Rule 7 & Table-II",
            "severity": "Major",
            "title": f"Substandard Numeral Height ({font_check['measured_numeral_height_mm']} mm < {font_check['required_numeral_height_mm']} mm)",
            "description": f"Numeral font height of {font_check['measured_numeral_height_mm']} mm fails the Table-II minimum requirement of {font_check['required_numeral_height_mm']} mm for PDP area {font_check['bracket_label']}.",
            "recommendation": f"Increase font size of Net Quantity and MRP numerals to at least {font_check['required_numeral_height_mm']} mm.",
            "penalty_clause": "Rule 7 & Section 36(1) of Legal Metrology Act, 2009."
        })
    if not font_check["letter_pass"]:
        violations.append({
            "rule_id": "LMPC-RULE-7-TABLE-2",
            "rule_name": "Table-II Letter Height Substandard",
            "section": "Rule 7 & Table-II",
            "severity": "Minor",
            "title": f"Substandard Letter Height ({font_check['measured_letter_height_mm']} mm < {font_check['required_letter_height_mm']} mm)",
            "description": f"Declaration letter height of {font_check['measured_letter_height_mm']} mm is below Table-II prescribed {font_check['required_letter_height_mm']} mm.",
            "recommendation": f"Enlarge declaration lettering to minimum {font_check['required_letter_height_mm']} mm.",
            "penalty_clause": "Rule 7 & Section 36(1) of Legal Metrology Act, 2009."
        })
    if font_check["is_compliant"]:
        verified_items.append({
            "rule_id": "LMPC-RULE-7-TABLE-2",
            "title": "Table-II Font Size & PDP Compliant",
            "detail": f"Numeral: {font_check['measured_numeral_height_mm']}mm (Req: {font_check['required_numeral_height_mm']}mm), Letter: {font_check['measured_letter_height_mm']}mm"
        })

    # Calculate Overall Compliance Score (0 to 100%)
    # Weightings: Total 100 pts. Critical deduction: 25 pts each, Major: 15 pts each, Minor: 5 pts each
    score = 100
    for v in violations:
        if v["severity"] == "Critical":
            score -= 25
        elif v["severity"] == "Major":
            score -= 15
        elif v["severity"] == "Minor":
            score -= 5
    score = max(0, min(100, score))
    
    is_overall_compliant = len([v for v in violations if v["severity"] in ["Critical", "Major"]]) == 0 and score >= 85
    compliance_status = "Compliant" if is_overall_compliant else ("Partially Compliant" if score >= 50 else "Non-Compliant")

    return {
        "compliance_status": compliance_status,
        "compliance_score": score,
        "is_compliant": is_overall_compliant,
        "violations_count": len(violations),
        "critical_violations": len([v for v in violations if v["severity"] == "Critical"]),
        "major_violations": len([v for v in violations if v["severity"] == "Major"]),
        "minor_violations": len([v for v in violations if v["severity"] == "Minor"]),
        "violations": violations,
        "verified_declarations": verified_items,
        "table_ii_font_check": font_check,
        "evaluated_at": datetime.now(timezone.utc).isoformat()
    }