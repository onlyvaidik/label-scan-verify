import uuid
from datetime import datetime, timezone
from auth_service import hash_password
from compliance_engine import DEFAULT_STATUTORY_RULES, validate_declarations_against_lmpc_rules

SAMPLE_PRODUCTS = [
    {
        "id": "SCAN-2026-001",
        "brand_name": "Britannia Good Day",
        "commodity_name": "Butter Cookies / Biscuits",
        "category": "FMCG Packaged Food",
        "barcode_gtin": "8901063012903",
        "image_url": "https://images.unsplash.com/photo-1558961363-fa8fdf82db35?w=600&auto=format&fit=crop&q=80",
        "inspector_id": "INS-782",
        "inspector_name": "Ananya Verma (Senior Field Inspector)",
        "jurisdiction": "New Delhi Central",
        "panel_area_sq_cm": 150.0,
        "numeral_height_mm": 2.5,
        "letter_height_mm": 1.6,
        "declarations": {
            "manufacturer_name": "Britannia Industries Limited",
            "manufacturer_address": "5/1A Hungerford Street, Kolkata, West Bengal - 700017",
            "commodity_name": "Butter Cookies",
            "net_quantity_value": 200,
            "net_quantity_unit": "g",
            "net_quantity_raw": "Net Quantity: 200 g",
            "unit_sale_price": "₹ 0.25 per g",
            "mrp_value": 50.00,
            "mrp_raw": "MRP Rs. 50.00 (incl. of all taxes)",
            "taxes_inclusive_declared": True,
            "manufacturing_date": "03/2026",
            "best_before_date": "6 months from packaging",
            "consumer_care_phone": "1800-425-4449",
            "consumer_care_email": "feedback@britindia.com",
            "consumer_care_details": "Executive, Consumer Care Cell, Britannia Industries Ltd., Kolkata - 700017. Toll Free: 1800-425-4449",
            "country_of_origin": "India",
            "batch_number": "BATCH-BD-0326A",
            "packer_name": None,
            "importer_name": None
        },
        "ocr_raw_text": "BRITANNIA GOOD DAY BUTTER COOKIES\nNet Qty: 200 g | USP: ₹ 0.25/g\nMRP Rs. 50.00 (incl. of all taxes)\nPkd: 03/2026 | B.No: BATCH-BD-0326A\nMfg by: Britannia Industries Ltd., 5/1A Hungerford St, Kolkata 700017\nCustomer Support: 1800-425-4449 / feedback@britindia.com\nCountry of Origin: India",
        "label_regions": [
            {"label": "Brand Name", "text": "BRITANNIA GOOD DAY", "x": 10, "y": 8, "width": 80, "height": 14},
            {"label": "MRP & USP", "text": "MRP Rs. 50.00 (incl. of all taxes) | USP ₹0.25/g", "x": 10, "y": 26, "width": 80, "height": 10},
            {"label": "Net Quantity", "text": "Net Qty: 200 g", "x": 10, "y": 38, "width": 45, "height": 10},
            {"label": "Mfg Date & Batch", "text": "Pkd: 03/2026 | BATCH-BD-0326A", "x": 10, "y": 52, "width": 80, "height": 10},
            {"label": "Manufacturer Address", "text": "Britannia Industries Ltd., Kolkata 700017", "x": 10, "y": 66, "width": 80, "height": 14},
            {"label": "Consumer Care", "text": "1800-425-4449 | feedback@britindia.com", "x": 10, "y": 82, "width": 80, "height": 10}
        ]
    },
    {
        "id": "SCAN-2026-002",
        "brand_name": "Royal Gold Edible Oil",
        "commodity_name": "Refined Sunflower Oil Pouch",
        "category": "FMCG Packaged Food",
        "barcode_gtin": "8902049182301",
        "image_url": "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=600&auto=format&fit=crop&q=80",
        "inspector_id": "INS-782",
        "inspector_name": "Ananya Verma (Senior Field Inspector)",
        "jurisdiction": "Maharashtra Zone 1",
        "panel_area_sq_cm": 220.0,
        "numeral_height_mm": 1.2,  # Substandard! (Req 4.0mm for >200 sq cm)
        "letter_height_mm": 0.8,
        "declarations": {
            "manufacturer_name": "Royal Agro Foods Pvt. Ltd.",
            "manufacturer_address": "Plot 12, GIDC Industrial Estate, Surat, Gujarat",  # Missing PIN!
            "commodity_name": "Sunflower Oil",
            "net_quantity_value": 1,
            "net_quantity_unit": "ltr",  # Invalid unit symbol (must be 'l' or 'L')
            "net_quantity_raw": "Net Volume: 1 ltr",
            "unit_sale_price": "",  # Missing Unit Sale Price
            "mrp_value": 165.00,
            "mrp_raw": "MRP 165/-",  # Missing taxes inclusive
            "taxes_inclusive_declared": False,
            "manufacturing_date": "11/2026",  # Future post-dated!
            "best_before_date": "9 months",
            "consumer_care_phone": "",
            "consumer_care_email": "royalagrosurat@gmail.com",
            "consumer_care_details": "royalagrosurat@gmail.com",
            "country_of_origin": "India",
            "batch_number": "RG-OIL-99",
            "packer_name": None,
            "importer_name": None
        },
        "ocr_raw_text": "ROYAL GOLD SUNFLOWER OIL\nNet Volume: 1 ltr\nMRP 165/-\nMfg Date: 11/2026 | Batch: RG-OIL-99\nMfg by: Royal Agro Foods Pvt. Ltd., Plot 12, GIDC, Surat, Gujarat\nContact: royalagrosurat@gmail.com",
        "label_regions": [
            {"label": "Brand Name", "text": "ROYAL GOLD SUNFLOWER OIL", "x": 10, "y": 10, "width": 80, "height": 14},
            {"label": "Defective MRP", "text": "MRP 165/-", "x": 10, "y": 28, "width": 40, "height": 8},
            {"label": "Invalid Unit Net Qty", "text": "Net Volume: 1 ltr", "x": 10, "y": 40, "width": 50, "height": 8},
            {"label": "Post-Dated Mfg Date", "text": "Mfg: 11/2026", "x": 10, "y": 52, "width": 45, "height": 8},
            {"label": "Incomplete Address", "text": "Plot 12, GIDC, Surat, Gujarat", "x": 10, "y": 64, "width": 80, "height": 12}
        ]
    },
    {
        "id": "SCAN-2026-003",
        "brand_name": "GlowSkin Radiance Face Cream",
        "commodity_name": "Cosmetic Skin Moisturizer Cream",
        "category": "Cosmetics & Personal Care",
        "barcode_gtin": "8903348172654",
        "image_url": "https://images.unsplash.com/photo-1556228720-195a672e8a03?w=600&auto=format&fit=crop&q=80",
        "inspector_id": "INS-782",
        "inspector_name": "Ananya Verma (Senior Field Inspector)",
        "jurisdiction": "New Delhi Central",
        "panel_area_sq_cm": 80.0,
        "numeral_height_mm": 2.2,
        "letter_height_mm": 1.5,
        "declarations": {
            "manufacturer_name": "Aura Cosmetics Lab",
            "manufacturer_address": "Sector 62, Noida, Uttar Pradesh - 201301",
            "commodity_name": "Hydrating Face Cream",
            "net_quantity_value": 50,
            "net_quantity_unit": "g",
            "net_quantity_raw": "Net Wt.: 50 g",
            "unit_sale_price": "₹ 7.98 per g",
            "mrp_value": 399.00,
            "mrp_raw": "MRP Rs. 399.00 (incl. of all taxes)",
            "taxes_inclusive_declared": True,
            "manufacturing_date": "02/2026",
            "best_before_date": "24 months from mfg",
            "consumer_care_phone": "0120-4491900",
            "consumer_care_email": "care@auracosmetics.in",
            "consumer_care_details": "Customer Care Manager, Aura Cosmetics, Sector 62, Noida. Phone: 0120-4491900, Email: care@auracosmetics.in",
            "country_of_origin": "India",
            "batch_number": "LOT-AC-202602",
            "packer_name": None,
            "importer_name": None
        },
        "ocr_raw_text": "GLOWSKIN RADIANCE FACE CREAM\nNet Wt: 50 g | Unit Sale Price: ₹ 7.98 / g\nMRP Rs. 399.00 (incl. of all taxes)\nMfg: 02/2026 | LOT: LOT-AC-202602\nCountry of Origin: India\nMfg by: Aura Cosmetics Lab, Sector 62, Noida 201301\nCustomer Care: 0120-4491900 / care@auracosmetics.in",
        "label_regions": [
            {"label": "Brand Name", "text": "GLOWSKIN RADIANCE", "x": 10, "y": 10, "width": 80, "height": 14},
            {"label": "MRP & USP", "text": "MRP Rs. 399.00 (incl. of all taxes) | USP ₹7.98/g", "x": 10, "y": 28, "width": 80, "height": 10},
            {"label": "Net Quantity", "text": "Net Wt: 50 g", "x": 10, "y": 42, "width": 45, "height": 8},
            {"label": "Mfg Date & Batch", "text": "Mfg: 02/2026 | LOT-AC-202602", "x": 10, "y": 55, "width": 80, "height": 8},
            {"label": "Manufacturer Address", "text": "Aura Cosmetics Lab, Noida 201301", "x": 10, "y": 68, "width": 80, "height": 12},
            {"label": "Consumer Care & Origin", "text": "Made in India | 0120-4491900", "x": 10, "y": 82, "width": 80, "height": 10}
        ]
    },
    {
        "id": "SCAN-2026-004",
        "brand_name": "SoundVibe Bluetooth Wireless Earbuds",
        "commodity_name": "TWS Bluetooth Earphones",
        "category": "Electronics & Appliances",
        "barcode_gtin": "8904491823190",
        "image_url": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=600&auto=format&fit=crop&q=80",
        "inspector_id": "INS-782",
        "inspector_name": "Rajesh Sharma (Enforcement Officer)",
        "jurisdiction": "Maharashtra Zone 1",
        "panel_area_sq_cm": 110.0,
        "numeral_height_mm": 2.2,
        "letter_height_mm": 1.4,
        "declarations": {
            "manufacturer_name": "Shenzhen Audio Precision Co. Ltd.",
            "manufacturer_address": "Baoan District, Shenzhen, Guangdong, China",
            "importer_name": "Apex Impex Pvt. Ltd.",
            "importer_address": "Office 402, Trade Tower, Bandra Kurla Complex, Mumbai - 400051",
            "commodity_name": "Wireless Stereo Earbuds",
            "net_quantity_value": 1,
            "net_quantity_unit": "N",
            "net_quantity_raw": "Net Quantity: 1 N (1 Pair Earbuds + 1 Charging Case + 1 Cable)",
            "unit_sale_price": "₹ 1,499.00 / N",
            "mrp_value": 1499.00,
            "mrp_raw": "MRP Rs. 1499.00 (inclusive of all taxes)",
            "taxes_inclusive_declared": True,
            "import_date": "01/2026",
            "manufacturing_date": "12/2025",
            "consumer_care_phone": "1800-889-2211",
            "consumer_care_email": "support@soundvibeindia.com",
            "consumer_care_details": "Customer Grievance Officer, Apex Impex, BKC, Mumbai 400051. Call: 1800-889-2211",
            "country_of_origin": "China",
            "batch_number": "SV-2026-IMP-88",
            "packer_name": None
        },
        "ocr_raw_text": "SOUNDVIBE TWS EARBUDS\nNet Qty: 1 N | USP: ₹ 1499.00 / N\nMRP Rs. 1499.00 (inclusive of all taxes)\nImported & Marketed by: Apex Impex Pvt. Ltd., BKC, Mumbai 400051\nCountry of Origin: China | Month/Year of Import: 01/2026\nCustomer Helpline: 1800-889-2211 / support@soundvibeindia.com\nBatch: SV-2026-IMP-88",
        "label_regions": [
            {"label": "Brand Name", "text": "SOUNDVIBE TWS EARBUDS", "x": 10, "y": 8, "width": 80, "height": 12},
            {"label": "MRP & USP", "text": "MRP Rs. 1499.00 (inclusive of all taxes)", "x": 10, "y": 24, "width": 80, "height": 10},
            {"label": "Net Quantity", "text": "Net Qty: 1 N", "x": 10, "y": 38, "width": 40, "height": 8},
            {"label": "Origin & Importer", "text": "Country of Origin: China | Imported by Apex Impex, Mumbai 400051", "x": 10, "y": 50, "width": 80, "height": 14},
            {"label": "Import Date & Batch", "text": "Imported: 01/2026 | SV-2026-IMP-88", "x": 10, "y": 68, "width": 80, "height": 8},
            {"label": "Consumer Care", "text": "1800-889-2211 | support@soundvibeindia.com", "x": 10, "y": 80, "width": 80, "height": 10}
        ]
    },
    {
        "id": "SCAN-2026-005",
        "brand_name": "Sparkle Clean Dishwash Liquid",
        "commodity_name": "Dishwashing Detergent Gel",
        "category": "Household Goods",
        "barcode_gtin": "8905582910243",
        "image_url": "https://images.unsplash.com/photo-1585421514738-01798e348b17?w=600&auto=format&fit=crop&q=80",
        "inspector_id": "INS-782",
        "inspector_name": "Ananya Verma (Senior Field Inspector)",
        "jurisdiction": "Delhi NCR",
        "panel_area_sq_cm": 180.0,
        "numeral_height_mm": 2.6,
        "letter_height_mm": 1.6,
        "declarations": {
            "manufacturer_name": "Sparkle Hygiene Care Ltd.",
            "manufacturer_address": "Plot 55, Okhla Phase III, New Delhi - 110020",
            "commodity_name": "Concentrated Dishwash Gel",
            "net_quantity_value": 750,
            "net_quantity_unit": "ml",
            "net_quantity_raw": "Net Volume: 750 ml",
            "unit_sale_price": "₹ 0.19 per ml",
            "mrp_value": 145.00,
            "mrp_raw": "MRP Rs. 145.00 (incl. of all taxes)",
            "taxes_inclusive_declared": True,
            "manufacturing_date": "01/2026",
            "best_before_date": "24 months from packing",
            "consumer_care_phone": "1800-112-990",
            "consumer_care_email": "customercare@sparkleclean.co.in",
            "consumer_care_details": "Customer Care Officer, Sparkle Hygiene Care, Okhla, New Delhi 110020. Toll-Free: 1800-112-990",
            "country_of_origin": "India",
            "batch_number": "SPK-DW-202601",
            "packer_name": None,
            "importer_name": None
        },
        "ocr_raw_text": "SPARKLE CLEAN DISHWASH GEL\nNet Volume: 750 ml | USP: ₹ 0.19 / ml\nMRP Rs. 145.00 (incl. of all taxes)\nBatch: SPK-DW-202601 | Pkd: 01/2026\nMfg by: Sparkle Hygiene Care Ltd., Okhla Phase III, New Delhi 110020\nConsumer Care Toll Free: 1800-112-990 | customercare@sparkleclean.co.in\nCountry of Origin: India",
        "label_regions": [
            {"label": "Brand Name", "text": "SPARKLE CLEAN DISHWASH", "x": 10, "y": 10, "width": 80, "height": 12},
            {"label": "MRP & USP", "text": "MRP Rs. 145.00 (incl. of all taxes) | USP ₹0.19/ml", "x": 10, "y": 26, "width": 80, "height": 10},
            {"label": "Net Quantity", "text": "Net Volume: 750 ml", "x": 10, "y": 40, "width": 45, "height": 8},
            {"label": "Mfg Date & Batch", "text": "Pkd: 01/2026 | SPK-DW-202601", "x": 10, "y": 54, "width": 80, "height": 8},
            {"label": "Manufacturer Address", "text": "Sparkle Hygiene Care Ltd, New Delhi 110020", "x": 10, "y": 68, "width": 80, "height": 12},
            {"label": "Consumer Care & Origin", "text": "Made in India | 1800-112-990", "x": 10, "y": 82, "width": 80, "height": 10}
        ]
    }
]


async def seed_initial_database(db):
    """Seeds initial users, statutory rules, and realistic product inspection scans."""
    # 1. Seed Users
    users_to_seed = [
        {
            "email": "admin@metrology.gov.in",
            "password": "AdminMetrology@2026",
            "name": "Chief Legal Metrology Officer",
            "role": "super_admin",
            "designation": "Director of Legal Metrology",
            "department": "Ministry of Consumer Affairs, Central Wing",
            "jurisdiction": "All India (National Jurisdiction)",
            "officer_id": "LMO-HQ-001",
            "two_factor_enabled": False
        },
        {
            "email": "officer.mumbai@metrology.gov.in",
            "password": "Officer@2026",
            "name": "Rajesh Sharma",
            "role": "enforcement_officer",
            "designation": "Joint Controller of Legal Metrology",
            "department": "Enforcement Division, Western Zone",
            "jurisdiction": "Maharashtra Zone 1",
            "officer_id": "LMO-MH-104",
            "two_factor_enabled": False
        },
        {
            "email": "inspector.delhi@metrology.gov.in",
            "password": "Inspector@2026",
            "name": "Ananya Verma",
            "role": "inspector",
            "designation": "Senior Field Metrology Inspector",
            "department": "District Inspection Squad",
            "jurisdiction": "New Delhi Central",
            "officer_id": "INS-782",
            "two_factor_enabled": False
        },
        {
            "email": "viewer@metrology.gov.in",
            "password": "Viewer@2026",
            "name": "Sunil Patil",
            "role": "viewer",
            "designation": "Compliance Auditor & Legal Researcher",
            "department": "Consumer Protection Audit Wing",
            "jurisdiction": "Pan India View",
            "officer_id": "AUD-2026-9",
            "two_factor_enabled": False
        }
    ]

    for u in users_to_seed:
        existing = await db.users.find_one({"email": u["email"]})
        if not existing:
            doc = {**u}
            doc["password_hash"] = hash_password(doc.pop("password"))
            doc["created_at"] = datetime.now(timezone.utc).isoformat()
            await db.users.insert_one(doc)

    # 2. Seed Statutory Rules
    for r in DEFAULT_STATUTORY_RULES:
        existing_rule = await db.statutory_rules.find_one({"rule_id": r["rule_id"]})
        if not existing_rule:
            doc = {**r, "created_at": datetime.now(timezone.utc).isoformat(), "is_active": True}
            await db.statutory_rules.insert_one(doc)

    # 3. Seed Sample Product Scans
    existing_scans_count = await db.scans.count_documents({})
    if existing_scans_count == 0:
        for p in SAMPLE_PRODUCTS:
            # Evaluate compliance using engine
            eval_res = validate_declarations_against_lmpc_rules(
                p["declarations"],
                p.get("panel_area_sq_cm", 140.0),
                p.get("numeral_height_mm", 2.4),
                p.get("letter_height_mm", 1.6)
            )
            scan_doc = {
                **p,
                **eval_res,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "review_status": "Verified" if eval_res["is_compliant"] else "Action Required",
                "enforcement_notice_issued": False if eval_res["is_compliant"] else True,
                "evidence_images": [p["image_url"]]
            }
            await db.scans.insert_one(scan_doc)