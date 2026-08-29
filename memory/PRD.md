# Legal Metrology (Packaged Commodities) Rules 2011 Compliance Checker

## Original Problem Statement
Software System to check compliance of Packaged Commodities under Legal Metrology (Packaged Commodities) Rules, 2011 by scanning products, images and labels. Detect mandatory declarations (Manufacturer/Packer/Importer name & address, Net Quantity, MRP, Mfg Date, Consumer Care, Country of Origin, Batch, USP), validate Rule 6 declarations, evaluate Table-II font size compliance, generate PDF/DOCX/CSV compliance reports, dashboard analytics, role-based auth, scan repository, statutory rule library.

## Tech Stack
- Frontend: React 19 + Tailwind + Material Symbols icons + Axios
- Backend: FastAPI + Motor (async MongoDB) + JWT (bcrypt) + emergentintegrations
- AI Vision: Google Gemini 3 Flash (`gemini-3-flash-preview`) via Emergent Universal LLM Key
- Reports: reportlab (PDF), python-docx (DOCX), CSV

## User Personas
1. **Super Admin** — Chief Legal Metrology Officer (national jurisdiction; rule library, user management)
2. **Enforcement Officer** — Zonal joint controller (issue Section 36 notices, review cases)
3. **Field Inspector** — Scans packaging, extracts declarations, saves case
4. **Auditor / Viewer** — Read-only reports & analytics

## Implemented (Aug 29, 2026)
### Backend
- JWT auth (bcrypt), 4 seeded roles, sessions, 2FA scaffold, audit logs
- POST /api/scan/analyze → Gemini 3 Flash multimodal OCR + Rule 6 evaluation + Table-II font check
- POST /api/scan/save → persists scan case with compliance recomputation
- GET /api/scans (filters: search/category/status/jurisdiction) + /api/scans/{id}
- POST /api/scans/{id}/action → issue_notice / mark_verified / flag_lab_test / archive (validated enum)
- GET /api/reports/{id}/pdf|docx|json + /api/reports/export/csv (Government of India banner)
- GET /api/dashboard/stats — total scans, compliance rate, category breakdown, top violations, recent scans
- GET /api/analytics/hotspots — 6 regional risk maps
- GET /api/rules — 12 seeded LMPC rules with penalty clauses + Table-II bracket data
- User management, audit log APIs
- Seed data: 4 users, 12 rules, 5 realistic sample scans (Britannia, Royal Gold Oil, GlowSkin, SoundVibe, Sparkle Clean)

### Frontend
- Login (JWT + 4 role quick-switcher + 2FA UI)
- Compliance Dashboard (metrics, category chart, violation distribution, recent scans table)
- New Product Scan (file upload, sample selector, panel area, category, 4-step progress)
- Scan Analysis Review (bounding boxes, Rule 6 editable declarations, Table-II panel, violations list, save & PDF)
- Inspection Reports Repository
- Statutory Rule Library
- Compliance Hotspots analytics
- User Management (admin)
- Audit Trail
- Profile & Security (2FA toggle)

## Fixed Issues
- React hooks rule violation in Login.js (useState after early return)
- NoneType.strip() crash in compliance_engine (added _s() safe coercion)
- NoneType comparison crash in /scan/analyze when Gemini returns null heights
- Removed fabricated "Heritage Consumer Products" fallback mock (now raises 502 on AI failure)
- Removed hardcoded EMERGENT_LLM_KEY and JWT_SECRET defaults
- Scan action enum validation (400 on unknown action)

## Backlog / Next Tasks
- P1: Add authentication requirement to /scan, /reports, /dashboard endpoints (currently public)
- P1: Login rate limiting / account lockout after N failed attempts
- P2: Return "Not Determinable" for null font heights instead of default 2.4/2.6 substitution
- P2: Multi-image scan (front + back + side panels stitched)
- P2: E-commerce URL crawler (bulk compliance check of product listings)
- P2: Mobile React Native companion app
- P2: Email/SMS Section 36 notice issuance to seller
