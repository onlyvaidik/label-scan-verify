import os
import uuid
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from fastapi import FastAPI, APIRouter, HTTPException, status, Request, Response, Depends, Query, Body
from fastapi.responses import StreamingResponse, JSONResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from pydantic import BaseModel, Field, ConfigDict

from auth_service import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    generate_2fa_code, generate_backup_codes, get_current_user_from_token
)
from compliance_engine import (
    DEFAULT_STATUTORY_RULES, TABLE_II_REQUIREMENTS,
    validate_declarations_against_lmpc_rules, evaluate_table_ii_font_size
)
from ai_vision_service import scan_label_with_ai_vision
from report_generator import generate_pdf_report, generate_docx_report, export_scans_to_csv
from seed_data import seed_initial_database, SAMPLE_PRODUCTS
from notice_service import (
    build_notice_html, build_notice_sms, send_email_notice, send_sms_notice
)
from url_scan_service import analyze_ecommerce_url

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("legal_metrology_server")

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI(title="Legal Metrology Compliance Checker API", version="2.0.0")
api_router = APIRouter(prefix="/api")


# ------------------ Pydantic Request Models ------------------
class UserRegisterRequest(BaseModel):
    email: str
    password: str
    name: str
    role: Optional[str] = "inspector"
    designation: Optional[str] = "Field Metrology Inspector"
    department: Optional[str] = "Department of Legal Metrology"
    jurisdiction: Optional[str] = "National"

class UserLoginRequest(BaseModel):
    email: str
    password: str

class Verify2FARequest(BaseModel):
    email: str
    code: str

class Toggle2FARequest(BaseModel):
    enabled: bool

class ScanAnalyzeRequest(BaseModel):
    image_base64: str
    product_hint: Optional[str] = None
    panel_area_sq_cm: Optional[float] = 140.0
    barcode_gtin: Optional[str] = None
    brand_name: Optional[str] = None
    category: Optional[str] = "FMCG Packaged Food"

class ScanSaveRequest(BaseModel):
    id: Optional[str] = None
    brand_name: str
    commodity_name: str
    category: str
    barcode_gtin: Optional[str] = None
    image_url: Optional[str] = None
    panel_area_sq_cm: Optional[float] = 140.0
    numeral_height_mm: Optional[float] = 2.4
    letter_height_mm: Optional[float] = 1.6
    declarations: Dict[str, Any]
    ocr_raw_text: Optional[str] = None
    label_regions: Optional[List[Dict[str, Any]]] = None
    inspector_notes: Optional[str] = None
    jurisdiction: Optional[str] = None

class ScanActionRequest(BaseModel):
    action: str  # "issue_notice", "flag_lab_test", "mark_verified", "archive"
    notes: Optional[str] = None

class SendNoticeRequest(BaseModel):
    channel: str  # "email" | "sms" | "both"
    recipient_email: Optional[str] = None
    recipient_phone: Optional[str] = None
    reply_deadline_days: int = 15
    custom_message: Optional[str] = None

class ScanUrlRequest(BaseModel):
    url: str
    category: Optional[str] = "FMCG Packaged Food"


# ------------------ Auth Dependency ------------------
async def get_current_user(request: Request):
    return await get_current_user_from_token(request, db)

async def get_current_user_optional(request: Request):
    try:
        return await get_current_user_from_token(request, db)
    except Exception:
        return None


# ------------------ Audit Log Helper ------------------
async def log_audit_event(user_email: str, action: str, entity_type: str, entity_id: str, details: Dict[str, Any], ip_addr: str = "127.0.0.1"):
    try:
        audit_doc = {
            "user_email": user_email,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "details": details,
            "ip_address": ip_addr,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await db.audit_logs.insert_one(audit_doc)
    except Exception as e:
        logger.warning(f"Failed to write audit log: {e}")


# ------------------ Lifespan Startup ------------------
@app.on_event("startup")
async def on_startup():
    logger.info("Initializing Legal Metrology Database indexes & seeds...")
    try:
        await db.users.create_index("email", unique=True)
        await db.scans.create_index("id", unique=True)
        await db.statutory_rules.create_index("rule_id", unique=True)
        await db.audit_logs.create_index("timestamp")
        await seed_initial_database(db)
        logger.info("Database startup seeds completed successfully.")
    except Exception as e:
        logger.error(f"Startup initialization warning: {e}")


# =======================================================
#                 AUTHENTICATION ROUTES
# =======================================================
@api_router.post("/auth/register")
async def register_user(req: UserRegisterRequest, response: Response):
    email_clean = req.email.strip().lower()
    existing = await db.users.find_one({"email": email_clean})
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email address already exists.")
        
    hashed = hash_password(req.password)
    officer_id = f"INS-{uuid.uuid4().hex[:6].upper()}"
    user_doc = {
        "email": email_clean,
        "password_hash": hashed,
        "name": req.name,
        "role": req.role if req.role in ["super_admin", "enforcement_officer", "inspector", "viewer"] else "inspector",
        "designation": req.designation or "Metrology Inspector",
        "department": req.department or "Department of Legal Metrology",
        "jurisdiction": req.jurisdiction or "Central Zone",
        "officer_id": officer_id,
        "two_factor_enabled": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    res = await db.users.insert_one(user_doc)
    user_id = str(res.inserted_id)
    
    access_token = create_access_token(user_id, email_clean, user_doc["role"])
    refresh_token = create_refresh_token(user_id)
    
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=True, samesite="none", max_age=86400, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=True, samesite="none", max_age=604800, path="/")
    
    user_doc.pop("password_hash", None)
    user_doc.pop("_id", None)
    user_doc["id"] = user_id
    user_doc["token"] = access_token
    
    await log_audit_event(email_clean, "USER_REGISTER", "USER", user_id, {"role": user_doc["role"]})
    return user_doc


@api_router.post("/auth/login")
async def login_user(req: UserLoginRequest, response: Response, request: Request):
    email_clean = req.email.strip().lower()
    
    # 5-strike lockout guard: check if account is currently locked
    LOCKOUT_THRESHOLD = 5
    LOCKOUT_WINDOW_MINUTES = 15
    now_ts = datetime.now(timezone.utc).timestamp()
    lock_doc = await db.login_attempts.find_one({"email": email_clean})
    
    # Reset stale counters if the lockout window has already elapsed
    if lock_doc and lock_doc.get("locked_until", 0) > 0 and lock_doc["locked_until"] <= now_ts:
        await db.login_attempts.delete_one({"email": email_clean})
        lock_doc = None
    
    if lock_doc and lock_doc.get("locked_until", 0) > now_ts:
        seconds_left = int(lock_doc["locked_until"] - now_ts)
        raise HTTPException(
            status_code=429,
            detail=f"Account temporarily locked due to {LOCKOUT_THRESHOLD} failed sign-in attempts. Try again in {seconds_left // 60}m {seconds_left % 60}s."
        )
    
    user = await db.users.find_one({"email": email_clean})
    if not user or not verify_password(req.password, user.get("password_hash", "")):
        # Record failed attempt
        failures = (lock_doc.get("failures", 0) if lock_doc else 0) + 1
        update: Dict[str, Any] = {
            "email": email_clean,
            "failures": failures,
            "last_failed_at": datetime.now(timezone.utc).isoformat(),
            "last_failed_ip": request.client.host if request.client else "unknown"
        }
        if failures >= LOCKOUT_THRESHOLD:
            update["locked_until"] = now_ts + (LOCKOUT_WINDOW_MINUTES * 60)
            await log_audit_event(email_clean, "LOGIN_LOCKOUT", "USER", email_clean, {"failures": failures, "lock_minutes": LOCKOUT_WINDOW_MINUTES})
        await db.login_attempts.update_one({"email": email_clean}, {"$set": update}, upsert=True)
        
        remaining = max(0, LOCKOUT_THRESHOLD - failures)
        detail = "Invalid email or password."
        if failures >= LOCKOUT_THRESHOLD:
            detail = f"Too many failed attempts. Account locked for {LOCKOUT_WINDOW_MINUTES} minutes."
        elif remaining <= 2:
            detail = f"Invalid email or password. {remaining} attempt(s) remaining before lockout."
        raise HTTPException(status_code=401, detail=detail)
    
    # Success — clear failure counter
    if lock_doc:
        await db.login_attempts.delete_one({"email": email_clean})
    
    user_id = str(user["_id"])
    
    # 2FA check
    if user.get("two_factor_enabled", False):
        code = generate_2fa_code()
        await db.users.update_one({"_id": user["_id"]}, {"$set": {"temp_2fa_code": code, "temp_2fa_expiry": datetime.now(timezone.utc).timestamp() + 300}})
        return {
            "requires_2fa": True,
            "email": email_clean,
            "message": f"2FA code sent to {email_clean}. (Demo Code: {code})"
        }
        
    access_token = create_access_token(user_id, email_clean, user.get("role", "inspector"))
    refresh_token = create_refresh_token(user_id)
    
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=True, samesite="none", max_age=86400, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=True, samesite="none", max_age=604800, path="/")
    
    # Record session
    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("User-Agent", "Web Browser")
    session_doc = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "user_email": email_clean,
        "ip_address": client_ip,
        "user_agent": user_agent,
        "login_time": datetime.now(timezone.utc).isoformat(),
        "active": True
    }
    await db.user_sessions.insert_one(session_doc)
    await log_audit_event(email_clean, "USER_LOGIN", "SESSION", session_doc["id"], {"ip": client_ip})
    
    user.pop("password_hash", None)
    user.pop("_id", None)
    user["id"] = user_id
    user["token"] = access_token
    user["requires_2fa"] = False
    return user


@api_router.post("/auth/verify-2fa")
async def verify_2fa(req: Verify2FARequest, response: Response, request: Request):
    email_clean = req.email.strip().lower()
    user = await db.users.find_one({"email": email_clean})
    if not user:
        raise HTTPException(status_code=400, detail="Invalid user")
        
    saved_code = user.get("temp_2fa_code")
    expiry = user.get("temp_2fa_expiry", 0)
    backup_codes = user.get("backup_codes", [])
    
    is_valid = False
    if saved_code and req.code == saved_code and datetime.now(timezone.utc).timestamp() < expiry:
        is_valid = True
    elif req.code in backup_codes:
        is_valid = True
        # Remove used backup code
        await db.users.update_one({"_id": user["_id"]}, {"$pull": {"backup_codes": req.code}})
        
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid or expired 2FA code.")
        
    # Clear temp code
    await db.users.update_one({"_id": user["_id"]}, {"$unset": {"temp_2fa_code": "", "temp_2fa_expiry": ""}})
    
    user_id = str(user["_id"])
    access_token = create_access_token(user_id, email_clean, user.get("role", "inspector"))
    refresh_token = create_refresh_token(user_id)
    
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=True, samesite="none", max_age=86400, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=True, samesite="none", max_age=604800, path="/")
    
    user.pop("password_hash", None)
    user.pop("_id", None)
    user["id"] = user_id
    user["token"] = access_token
    return user


@api_router.get("/auth/me")
async def get_current_user_profile(user: dict = Depends(get_current_user)):
    return user


@api_router.post("/auth/toggle-2fa")
async def toggle_2fa(req: Toggle2FARequest, user: dict = Depends(get_current_user)):
    backup_codes = generate_backup_codes(8) if req.enabled else []
    await db.users.update_one(
        {"email": user["email"]},
        {"$set": {"two_factor_enabled": req.enabled, "backup_codes": backup_codes}}
    )
    return {"two_factor_enabled": req.enabled, "backup_codes": backup_codes}


@api_router.post("/auth/logout")
async def logout_user(response: Response, user: dict = Depends(get_current_user_optional)):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    if user:
        await log_audit_event(user.get("email", "unknown"), "USER_LOGOUT", "USER", user.get("id", ""), {})
    return {"message": "Successfully logged out."}


@api_router.get("/auth/sessions")
async def get_user_sessions(user: dict = Depends(get_current_user)):
    sessions = await db.user_sessions.find({"user_email": user["email"]}, {"_id": 0}).sort("login_time", -1).to_list(20)
    return sessions


@api_router.post("/auth/sessions/revoke")
async def revoke_session(session_id: str = Body(..., embed=True), user: dict = Depends(get_current_user)):
    await db.user_sessions.update_one({"id": session_id, "user_email": user["email"]}, {"$set": {"active": False}})
    return {"message": "Session revoked."}


# =======================================================
#                 SCAN & ANALYSIS ROUTES
# =======================================================
@api_router.get("/scan/samples")
async def get_sample_products():
    """Provides quick test samples for demonstration and instant scanning."""
    return SAMPLE_PRODUCTS


@api_router.post("/scan/analyze")
async def analyze_product_label(req: ScanAnalyzeRequest, user: Optional[dict] = Depends(get_current_user_optional)):
    """Runs Multimodal AI Vision & Rule Extraction on uploaded package image."""
    try:
        extracted = await scan_label_with_ai_vision(req.image_base64, req.product_hint)
    except RuntimeError as e:
        # Vision AI failed (invalid image, API error, etc.) - fail loudly. 
        # Use 422 (not 502) so the Cloudflare ingress does not replace body with an HTML gateway page.
        raise HTTPException(status_code=422, detail=str(e))
    
    try:
        # Coerce None-values to safe numeric defaults (Gemini/GPT may return null for measured heights)
        panel_area = req.panel_area_sq_cm or extracted.get("estimated_panel_area_sq_cm") or 140.0
        numeral_h = extracted.get("measured_numeral_height_mm") or 2.4
        letter_h = extracted.get("measured_letter_height_mm") or 1.6
        
        # Evaluate complete statutory compliance against LMPC Rules 2011
        declarations_dict = {
            "manufacturer_name": extracted.get("manufacturer_name", ""),
            "manufacturer_address": extracted.get("manufacturer_address", ""),
            "packer_name": extracted.get("packer_name"),
            "importer_name": extracted.get("importer_name"),
            "commodity_name": extracted.get("commodity_name", req.product_hint or "Packaged Commodity"),
            "net_quantity_value": extracted.get("net_quantity_value"),
            "net_quantity_unit": extracted.get("net_quantity_unit", ""),
            "net_quantity_raw": extracted.get("net_quantity_raw", ""),
            "unit_sale_price": extracted.get("unit_sale_price", ""),
            "mrp_value": extracted.get("mrp_value"),
            "mrp_raw": extracted.get("mrp_raw", ""),
            "taxes_inclusive_declared": extracted.get("taxes_inclusive_declared", True),
            "manufacturing_date": extracted.get("manufacturing_date", ""),
            "best_before_date": extracted.get("best_before_date", ""),
            "consumer_care_phone": extracted.get("consumer_care_phone", ""),
            "consumer_care_email": extracted.get("consumer_care_email", ""),
            "consumer_care_details": extracted.get("consumer_care_details", ""),
            "country_of_origin": extracted.get("country_of_origin", "India"),
            "batch_number": extracted.get("batch_number", "")
        }
        
        compliance_results = validate_declarations_against_lmpc_rules(
            declarations_dict,
            panel_area,
            numeral_h,
            letter_h
        )
        
        response_payload = {
            "brand_name": extracted.get("brand_name", req.brand_name or "Scanned Product"),
            "commodity_name": extracted.get("commodity_name", req.product_hint or "Packaged Commodity"),
            "category": req.category or "FMCG Packaged Food",
            "barcode_gtin": extracted.get("barcode_gtin", req.barcode_gtin or "890" + str(uuid.uuid4().int)[:10]),
            "engine_used": extracted.get("engine_used", "Google Gemini 3 Flash Vision"),
            "ocr_confidence": extracted.get("ocr_confidence", 94.0),
            "panel_area_sq_cm": panel_area,
            "numeral_height_mm": numeral_h,
            "letter_height_mm": letter_h,
            "declarations": declarations_dict,
            "ocr_raw_text": extracted.get("ocr_raw_text", ""),
            "label_regions": extracted.get("label_regions", []),
            **compliance_results
        }
        
        return response_payload
    except Exception as e:
        logger.error(f"Analysis failure: {e}")
        raise HTTPException(status_code=500, detail=f"Scan analysis error: {str(e)}")


@api_router.post("/scan/save")
async def save_scan_result(req: ScanSaveRequest, user: Optional[dict] = Depends(get_current_user_optional)):
    """Saves or updates a verified scan case in MongoDB with full audit record."""
    scan_id = req.id or f"SCAN-{datetime.now(timezone.utc).year}-{uuid.uuid4().hex[:6].upper()}"
    
    inspector_id = user.get("officer_id", "INS-782") if user else "INS-782"
    inspector_name = user.get("name", "Field Metrology Inspector") if user else "Field Metrology Inspector"
    jurisdiction = req.jurisdiction or (user.get("jurisdiction") if user else "Central District")
    
    # Run compliance evaluation
    comp_res = validate_declarations_against_lmpc_rules(
        req.declarations,
        req.panel_area_sq_cm or 140.0,
        req.numeral_height_mm or 2.4,
        req.letter_height_mm or 1.6
    )
    
    doc = {
        "id": scan_id,
        "brand_name": req.brand_name,
        "commodity_name": req.commodity_name,
        "category": req.category,
        "barcode_gtin": req.barcode_gtin or ("890" + str(uuid.uuid4().int)[:10]),
        "image_url": req.image_url or "https://images.unsplash.com/photo-1558961363-fa8fdf82db35?w=600&auto=format&fit=crop&q=80",
        "inspector_id": inspector_id,
        "inspector_name": inspector_name,
        "jurisdiction": jurisdiction,
        "panel_area_sq_cm": req.panel_area_sq_cm or 140.0,
        "numeral_height_mm": req.numeral_height_mm or 2.4,
        "letter_height_mm": req.letter_height_mm or 1.6,
        "declarations": req.declarations,
        "ocr_raw_text": req.ocr_raw_text or "",
        "label_regions": req.label_regions or [],
        "inspector_notes": req.inspector_notes or "",
        "review_status": "Verified" if comp_res["is_compliant"] else "Action Required",
        "enforcement_notice_issued": not comp_res["is_compliant"],
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **comp_res
    }
    
    existing = await db.scans.find_one({"id": scan_id})
    if existing:
        await db.scans.update_one({"id": scan_id}, {"$set": doc})
        action_name = "SCAN_UPDATE_VERIFY"
    else:
        doc["created_at"] = datetime.now(timezone.utc).isoformat()
        await db.scans.insert_one(doc)
        action_name = "SCAN_CREATE"
        
    user_email = user.get("email", "system") if user else "inspector@metrology.gov.in"
    await log_audit_event(user_email, action_name, "SCAN", scan_id, {
        "status": doc["compliance_status"],
        "score": doc["compliance_score"],
        "violations": doc["violations_count"]
    })
    
    doc.pop("_id", None)
    return doc


@api_router.get("/scans")
async def list_scans(
    search: Optional[str] = None,
    category: Optional[str] = None,
    compliance_status: Optional[str] = Query(None, alias="status"),
    severity: Optional[str] = None,
    jurisdiction: Optional[str] = None,
    limit: int = 50,
    skip: int = 0
):
    """Searches and filters inspection case repository."""
    query: Dict[str, Any] = {}
    
    if search:
        regex_pat = {"$regex": search, "$options": "i"}
        query["$or"] = [
            {"brand_name": regex_pat},
            {"commodity_name": regex_pat},
            {"barcode_gtin": regex_pat},
            {"id": regex_pat},
            {"declarations.manufacturer_name": regex_pat}
        ]
        
    if category and category != "All":
        query["category"] = category
        
    if compliance_status and compliance_status != "All":
        query["compliance_status"] = compliance_status
        
    if jurisdiction and jurisdiction != "All":
        query["jurisdiction"] = jurisdiction
        
    scans = await db.scans.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.scans.count_documents(query)
    return {"total": total, "scans": scans}


@api_router.get("/scans/{scan_id}")
async def get_scan_by_id(scan_id: str):
    scan = await db.scans.find_one({"id": scan_id}, {"_id": 0})
    if not scan:
        raise HTTPException(status_code=404, detail=f"Inspection case {scan_id} not found.")
    return scan


@api_router.delete("/scans/{scan_id}")
async def delete_scan_by_id(scan_id: str, user: dict = Depends(get_current_user)):
    res = await db.scans.delete_one({"id": scan_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Scan not found")
    await log_audit_event(user["email"], "SCAN_DELETE", "SCAN", scan_id, {})
    return {"message": f"Scan case {scan_id} deleted successfully."}


@api_router.post("/scans/{scan_id}/action")
async def perform_scan_action(scan_id: str, req: ScanActionRequest, user: dict = Depends(get_current_user)):
    allowed_actions = {"issue_notice", "mark_verified", "flag_lab_test", "archive"}
    if req.action not in allowed_actions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action '{req.action}'. Allowed: {', '.join(sorted(allowed_actions))}"
        )
        
    scan = await db.scans.find_one({"id": scan_id})
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
        
    update_fields: Dict[str, Any] = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if req.action == "issue_notice":
        update_fields["enforcement_notice_issued"] = True
        update_fields["notice_issued_at"] = datetime.now(timezone.utc).isoformat()
        update_fields["notice_issued_by"] = user.get("name", "Officer")
        update_fields["review_status"] = "Notice Issued under Sec 36"
    elif req.action == "mark_verified":
        update_fields["review_status"] = "Verified"
    elif req.action == "flag_lab_test":
        update_fields["review_status"] = "Flagged for Physical Lab Metrology Verification"
    elif req.action == "archive":
        update_fields["review_status"] = "Archived Case"
        
    if req.notes:
        update_fields["inspector_notes"] = f"{scan.get('inspector_notes', '')}\n[{datetime.now().strftime('%d/%m/%Y %H:%M')}] {req.notes}".strip()
        
    await db.scans.update_one({"id": scan_id}, {"$set": update_fields})
    await log_audit_event(user["email"], f"ACTION_{req.action.upper()}", "SCAN", scan_id, {"notes": req.notes})
    
    updated = await db.scans.find_one({"id": scan_id}, {"_id": 0})
    return updated


# =======================================================
#                 REPORT EXPORT ROUTES
# =======================================================
@api_router.get("/reports/{scan_id}/pdf")
async def download_scan_pdf_report(scan_id: str):
    scan = await db.scans.find_one({"id": scan_id}, {"_id": 0})
    if not scan:
        raise HTTPException(status_code=404, detail="Inspection case not found")
        
    pdf_stream = generate_pdf_report(scan)
    filename = f"Legal_Metrology_Inspection_Report_{scan_id}.pdf"
    return StreamingResponse(
        pdf_stream,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@api_router.get("/reports/{scan_id}/docx")
async def download_scan_docx_report(scan_id: str):
    scan = await db.scans.find_one({"id": scan_id}, {"_id": 0})
    if not scan:
        raise HTTPException(status_code=404, detail="Inspection case not found")
        
    docx_stream = generate_docx_report(scan)
    filename = f"Legal_Metrology_Inspection_Report_{scan_id}.docx"
    return StreamingResponse(
        docx_stream,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@api_router.get("/reports/{scan_id}/json")
async def get_scan_json_report(scan_id: str):
    scan = await db.scans.find_one({"id": scan_id}, {"_id": 0})
    if not scan:
        raise HTTPException(status_code=404, detail="Inspection case not found")
    return scan


# =======================================================
#           NOTICE-TO-SELLER (Section 36)
# =======================================================
@api_router.post("/scans/{scan_id}/send-notice")
async def send_seller_notice(scan_id: str, req: SendNoticeRequest, user: dict = Depends(get_current_user)):
    """Sends a Section 36 statutory notice via email (Resend) and/or SMS (Twilio)."""
    scan = await db.scans.find_one({"id": scan_id}, {"_id": 0})
    if not scan:
        raise HTTPException(status_code=404, detail="Inspection case not found")
    
    if req.channel not in ("email", "sms", "both"):
        raise HTTPException(status_code=400, detail="Channel must be one of: email, sms, both")
    
    # Auto-pick recipient from declarations if not provided
    decl = scan.get("declarations", {})
    to_email = (req.recipient_email or decl.get("consumer_care_email") or "").strip()
    to_phone = (req.recipient_phone or decl.get("consumer_care_phone") or "").strip()
    
    if req.channel in ("email", "both") and not to_email:
        raise HTTPException(status_code=400, detail="Recipient email is required for email channel.")
    if req.channel in ("sms", "both") and not to_phone:
        raise HTTPException(status_code=400, detail="Recipient phone is required for SMS channel.")
    
    from datetime import timedelta
    deadline_dt = datetime.now(timezone.utc) + timedelta(days=max(1, req.reply_deadline_days))
    reply_deadline = deadline_dt.strftime("%d %B %Y")
    notice_number = f"LM/SEC36/{datetime.now().year}/{uuid.uuid4().hex[:6].upper()}"
    
    delivery_results = []
    errors = []
    
    if req.channel in ("email", "both"):
        try:
            html = build_notice_html(scan, reply_deadline, notice_number)
            subject = f"Legal Metrology Statutory Notice {notice_number} — {scan.get('brand_name','Product')}"
            result = await send_email_notice(to_email, subject, html)
            delivery_results.append(result)
        except Exception as e:
            errors.append({"channel": "email", "error": str(e)})
    
    if req.channel in ("sms", "both"):
        try:
            body = req.custom_message or build_notice_sms(scan, reply_deadline, notice_number)
            result = await send_sms_notice(to_phone, body)
            delivery_results.append(result)
        except Exception as e:
            errors.append({"channel": "sms", "error": str(e)})
    
    if not delivery_results and errors:
        # 422 (not 502) so Cloudflare ingress preserves our JSON body.
        raise HTTPException(status_code=422, detail={"message": "All delivery attempts failed", "errors": errors})
    
    # Record notice in DB
    notice_doc = {
        "id": notice_number,
        "scan_id": scan_id,
        "notice_number": notice_number,
        "issued_by_email": user["email"],
        "issued_by_name": user.get("name", "Officer"),
        "reply_deadline": reply_deadline,
        "channels_attempted": req.channel,
        "deliveries": delivery_results,
        "errors": errors,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notices.insert_one(notice_doc)
    
    # Mark scan as notice-issued
    await db.scans.update_one(
        {"id": scan_id},
        {"$set": {
            "enforcement_notice_issued": True,
            "notice_issued_at": datetime.now(timezone.utc).isoformat(),
            "notice_issued_by": user.get("name", "Officer"),
            "review_status": "Notice Issued under Sec 36",
            "latest_notice_number": notice_number
        }}
    )
    
    await log_audit_event(user["email"], "SEND_SECTION_36_NOTICE", "SCAN", scan_id, {
        "notice_number": notice_number, "channels": req.channel,
        "success": len(delivery_results), "failed": len(errors)
    })
    
    notice_doc.pop("_id", None)
    return notice_doc


@api_router.get("/scans/{scan_id}/notices")
async def list_notices_for_scan(scan_id: str):
    notices = await db.notices.find({"scan_id": scan_id}, {"_id": 0}).sort("created_at", -1).to_list(50)
    return notices


# =======================================================
#           BULK URL SCAN (e-commerce listings)
# =======================================================
@api_router.post("/scan/url")
async def scan_ecommerce_url(req: ScanUrlRequest, user: Optional[dict] = Depends(get_current_user_optional)):
    """Scan an e-commerce product listing URL (Amazon, Flipkart, Nykaa, etc.) for LMPC compliance."""
    url = req.url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        raise HTTPException(status_code=400, detail="URL must start with http:// or https://")
    
    try:
        extracted = await analyze_ecommerce_url(url)
    except RuntimeError as e:
        # 422 keeps the JSON body intact through the Cloudflare preview ingress.
        raise HTTPException(status_code=422, detail=str(e))
    
    panel_area = 200.0  # E-commerce listings — assume large primary display panel
    numeral_h = extracted.get("measured_numeral_height_mm") or 3.0
    letter_h = extracted.get("measured_letter_height_mm") or 2.0
    
    declarations = {
        "manufacturer_name": extracted.get("manufacturer_name", ""),
        "manufacturer_address": extracted.get("manufacturer_address", ""),
        "packer_name": extracted.get("packer_name"),
        "importer_name": extracted.get("importer_name"),
        "commodity_name": extracted.get("commodity_name", ""),
        "net_quantity_value": extracted.get("net_quantity_value"),
        "net_quantity_unit": extracted.get("net_quantity_unit", ""),
        "net_quantity_raw": extracted.get("net_quantity_raw", ""),
        "unit_sale_price": extracted.get("unit_sale_price", ""),
        "mrp_value": extracted.get("mrp_value"),
        "mrp_raw": extracted.get("mrp_raw", ""),
        "taxes_inclusive_declared": extracted.get("taxes_inclusive_declared", False),
        "manufacturing_date": extracted.get("manufacturing_date", ""),
        "best_before_date": extracted.get("best_before_date", ""),
        "consumer_care_phone": extracted.get("consumer_care_phone", ""),
        "consumer_care_email": extracted.get("consumer_care_email", ""),
        "consumer_care_details": extracted.get("consumer_care_details", ""),
        "country_of_origin": extracted.get("country_of_origin", ""),
        "batch_number": extracted.get("batch_number", "")
    }
    
    compliance = validate_declarations_against_lmpc_rules(declarations, panel_area, numeral_h, letter_h)
    
    return {
        "brand_name": extracted.get("brand_name", "E-commerce Listing"),
        "commodity_name": declarations["commodity_name"] or "Online Product",
        "category": req.category or "FMCG Packaged Food",
        "barcode_gtin": extracted.get("barcode_gtin") or ("URL-" + str(uuid.uuid4().hex[:10]).upper()),
        "listing_url": url,
        "listing_platform": extracted.get("listing_platform"),
        "engine_used": extracted.get("engine_used", "Gemini 3 Flash E-commerce Analyzer"),
        "ocr_confidence": extracted.get("ocr_confidence", 92.0),
        "panel_area_sq_cm": panel_area,
        "numeral_height_mm": numeral_h,
        "letter_height_mm": letter_h,
        "declarations": declarations,
        "ocr_raw_text": extracted.get("ocr_raw_text", ""),
        "label_regions": [],
        **compliance
    }


@api_router.get("/reports/export/csv")
async def export_scans_csv():
    scans = await db.scans.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    csv_stream = export_scans_to_csv(scans)
    filename = f"LMPC_Inspection_Records_{datetime.now().strftime('%Y%m%d')}.csv"
    return Response(
        content=csv_stream.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# =======================================================
#                 DASHBOARD & ANALYTICS ROUTES
# =======================================================
@api_router.get("/dashboard/stats")
async def get_dashboard_statistics():
    total_scans = await db.scans.count_documents({})
    compliant_count = await db.scans.count_documents({"compliance_status": "Compliant"})
    non_compliant_count = await db.scans.count_documents({"compliance_status": {"$in": ["Non-Compliant", "Partially Compliant"]}})
    notices_issued = await db.scans.count_documents({"enforcement_notice_issued": True})
    
    compliance_rate = round((compliant_count / total_scans * 100), 1) if total_scans > 0 else 0
    
    # Category Breakdown
    pipeline = [
        {"$group": {"_id": "$category", "count": {"$sum": 1}, "non_compliant": {"$sum": {"$cond": [{"$eq": ["$compliance_status", "Non-Compliant"]}, 1, 0]}}}},
        {"$sort": {"count": -1}}
    ]
    category_stats = await db.scans.aggregate(pipeline).to_list(10)
    
    # Violation Type Distribution
    all_scans = await db.scans.find({}, {"violations": 1}).to_list(1000)
    violation_dist: Dict[str, int] = {}
    for s in all_scans:
        for v in s.get("violations", []):
            v_title = v.get("rule_name", "Other")
            violation_dist[v_title] = violation_dist.get(v_title, 0) + 1
            
    violation_chart_data = [{"name": k, "count": v} for k, v in sorted(violation_dist.items(), key=lambda x: x[1], reverse=True)[:6]]
    
    recent_scans = await db.scans.find({}, {"_id": 0}).sort("created_at", -1).limit(6).to_list(6)
    
    return {
        "total_scans": total_scans,
        "compliant_count": compliant_count,
        "non_compliant_count": non_compliant_count,
        "compliance_rate": compliance_rate,
        "notices_issued": notices_issued,
        "category_stats": category_stats,
        "violation_chart_data": violation_chart_data,
        "recent_scans": recent_scans
    }


@api_router.get("/analytics/hotspots")
async def get_compliance_hotspots():
    """Regional geographic hotspots of Legal Metrology compliance."""
    return [
        {"state": "Maharashtra", "district": "Mumbai & Thane", "total_inspections": 3450, "compliant_rate": 84.2, "violations_rate": 15.8, "risk_level": "Medium", "top_violation": "Improper MRP Tax Inscription", "enforcement_officers": 28},
        {"state": "Delhi NCR", "district": "Central & South Delhi", "total_inspections": 2890, "compliant_rate": 88.5, "violations_rate": 11.5, "risk_level": "Low", "top_violation": "Missing Unit Sale Price (USP)", "enforcement_officers": 22},
        {"state": "Gujarat", "district": "Surat & Ahmedabad", "total_inspections": 2140, "compliant_rate": 72.4, "violations_rate": 27.6, "risk_level": "High", "top_violation": "Non-Standard Metric Units (gms/ltr)", "enforcement_officers": 16},
        {"state": "Karnataka", "district": "Bengaluru Urban", "total_inspections": 1980, "compliant_rate": 91.0, "violations_rate": 9.0, "risk_level": "Low", "top_violation": "Table-II Font Size Substandard", "enforcement_officers": 18},
        {"state": "Tamil Nadu", "district": "Chennai & Coimbatore", "total_inspections": 1670, "compliant_rate": 82.0, "violations_rate": 18.0, "risk_level": "Medium", "top_violation": "Incomplete Manufacturer Address", "enforcement_officers": 14},
        {"state": "West Bengal", "district": "Kolkata & Howrah", "total_inspections": 1420, "compliant_rate": 76.5, "violations_rate": 23.5, "risk_level": "High", "top_violation": "Missing Consumer Care Helpline", "enforcement_officers": 12}
    ]


@api_router.get("/audit-logs")
async def get_audit_logs(limit: int = 50):
    logs = await db.audit_logs.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit).to_list(limit)
    return logs


# =======================================================
#                 STATUTORY RULES LIBRARY
# =======================================================
@api_router.get("/rules")
async def list_statutory_rules():
    rules = await db.statutory_rules.find({}, {"_id": 0}).to_list(100)
    return {"rules": rules, "table_ii_reference": TABLE_II_REQUIREMENTS}


@api_router.put("/rules/{rule_id}")
async def update_statutory_rule(rule_id: str, updates: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
    if user.get("role") not in ["super_admin", "enforcement_officer"]:
        raise HTTPException(status_code=403, detail="Admin or Enforcement Officer permissions required to modify rules.")
        
    res = await db.statutory_rules.update_one({"rule_id": rule_id}, {"$set": updates})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
        
    await log_audit_event(user["email"], "RULE_UPDATE", "RULE", rule_id, updates)
    updated = await db.statutory_rules.find_one({"rule_id": rule_id}, {"_id": 0})
    return updated


# =======================================================
#                 USER & TEAM MANAGEMENT
# =======================================================
@api_router.get("/users")
async def get_all_users(user: dict = Depends(get_current_user)):
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(100)
    for u in users:
        if "id" not in u and "_id" in u:
            u["id"] = str(u["_id"])
    return users


@api_router.post("/users")
async def create_user_by_admin(req: UserRegisterRequest, user: dict = Depends(get_current_user)):
    if user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Super Admin permission required to add new officers.")
        
    email_clean = req.email.strip().lower()
    existing = await db.users.find_one({"email": email_clean})
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists.")
        
    hashed = hash_password(req.password)
    officer_id = f"INS-{uuid.uuid4().hex[:6].upper()}"
    user_doc = {
        "email": email_clean,
        "password_hash": hashed,
        "name": req.name,
        "role": req.role,
        "designation": req.designation or "Legal Metrology Inspector",
        "department": req.department or "Enforcement Wing",
        "jurisdiction": req.jurisdiction or "Field Inspection",
        "officer_id": officer_id,
        "two_factor_enabled": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user_doc)
    await log_audit_event(user["email"], "USER_CREATE", "USER", officer_id, {"email": email_clean, "role": req.role})
    
    user_doc.pop("password_hash", None)
    user_doc.pop("_id", None)
    return user_doc


@api_router.put("/users/{user_id_or_email}")
async def update_user_profile(user_id_or_email: str, updates: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
    # Disallow updating password_hash directly here
    updates.pop("password_hash", None)
    updates.pop("password", None)
    
    query = {"$or": [{"email": user_id_or_email}, {"officer_id": user_id_or_email}]}
    try:
        query["$or"].append({"_id": ObjectId(user_id_or_email)})
    except Exception:
        pass
        
    res = await db.users.update_one(query, {"$set": updates})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
        
    await log_audit_event(user["email"], "USER_UPDATE", "USER", user_id_or_email, updates)
    updated = await db.users.find_one(query, {"_id": 0, "password_hash": 0})
    return updated


# ------------------ Mount Routers & Middleware ------------------
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://label-scan-verify.preview.emergentagent.com"
    ],
    allow_origin_regex=r"https://.*\.preview\.emergentagent\.com",
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()