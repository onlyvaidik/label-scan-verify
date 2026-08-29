"""Notice-to-seller service — Resend (email) + Twilio (SMS) delivery for Section 36 violation notices."""
import os
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

import resend
from twilio.rest import Client as TwilioClient
from twilio.base.exceptions import TwilioRestException

logger = logging.getLogger("notice_service")


def _fmt_violations_text(violations: List[Dict[str, Any]]) -> str:
    lines = []
    for i, v in enumerate(violations, 1):
        lines.append(f"{i}. [{v.get('severity','Major')}] {v.get('section','')}: {v.get('title','')}")
        lines.append(f"   Rectify: {v.get('recommendation','')}")
        lines.append(f"   Penalty: {v.get('penalty_clause','')}")
    return "\n".join(lines) if lines else "No specific violations recorded."


def _fmt_violations_html(violations: List[Dict[str, Any]]) -> str:
    if not violations:
        return "<p>No specific violations recorded.</p>"
    rows = []
    for v in violations:
        sev = v.get("severity", "Major")
        color = "#DC3545" if sev == "Critical" else ("#E88A1E" if sev == "Major" else "#FFC107")
        rows.append(f"""
        <tr>
          <td style="padding:10px;border-bottom:1px solid #eee;">
            <span style="display:inline-block;background:{color};color:white;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold;">{sev}</span>
            <strong style="color:#001255;font-size:13px;"> {v.get('section','')}: {v.get('title','')}</strong><br/>
            <span style="color:#555;font-size:12px;">{v.get('description','')}</span><br/>
            <span style="color:#E88A1E;font-size:12px;"><b>Rectify:</b> {v.get('recommendation','')}</span><br/>
            <span style="color:#7a3c3c;font-size:11px;font-style:italic;">Penalty Clause: {v.get('penalty_clause','')}</span>
          </td>
        </tr>""")
    return "<table cellspacing='0' cellpadding='0' style='width:100%;border:1px solid #eee;border-radius:6px;'>" + "".join(rows) + "</table>"


def build_notice_html(scan: Dict[str, Any], reply_deadline: str, notice_number: str) -> str:
    """Build official-looking Section 36 notice HTML for email."""
    decl = scan.get("declarations", {})
    return f"""
<!DOCTYPE html>
<html><body style="font-family: Arial, Helvetica, sans-serif; color: #212529; margin:0; padding: 0; background: #f4f6fa;">
  <table cellpadding="0" cellspacing="0" style="max-width:640px;margin:24px auto;background:white;border-radius:10px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.06);">
    <tr>
      <td style="background:#001255;color:white;padding:22px 28px;text-align:center;">
        <div style="font-size:11px;letter-spacing:2px;color:#E88A1E;text-transform:uppercase;font-weight:bold;">Government of India</div>
        <div style="font-size:16px;font-weight:bold;margin-top:4px;">Ministry of Consumer Affairs — Legal Metrology Enforcement Wing</div>
        <div style="font-size:11px;color:#c8d3f5;margin-top:2px;">STATUTORY NOTICE UNDER SECTION 36, LEGAL METROLOGY ACT 2009</div>
      </td>
    </tr>
    <tr>
      <td style="padding:22px 28px;">
        <table width="100%" style="font-size:12px;color:#555;margin-bottom:16px;">
          <tr><td><b>Notice No.:</b> {notice_number}</td><td style="text-align:right;"><b>Date:</b> {datetime.now(timezone.utc).strftime('%d %B %Y')}</td></tr>
          <tr><td><b>Case ID:</b> {scan.get('id','')}</td><td style="text-align:right;"><b>Reply By:</b> {reply_deadline}</td></tr>
        </table>

        <p style="font-size:13px;color:#212529;">To,<br/>
        <b>{decl.get('manufacturer_name','The Manufacturer/Packer/Importer')}</b><br/>
        {decl.get('manufacturer_address','')}
        </p>

        <p style="font-size:13px;">Subject: <b>Statutory Non-Compliance detected on product <i>{scan.get('brand_name','')} — {scan.get('commodity_name','')}</i></b></p>

        <p style="font-size:13px;line-height:1.5;">
          Sir/Madam,<br/><br/>
          Pursuant to an inspection carried out under the <b>Legal Metrology (Packaged Commodities) Rules, 2011</b>,
          your product bearing barcode <code>{scan.get('barcode_gtin','')}</code> has been examined and the following
          statutory violations have been identified. You are hereby directed to <b>show cause within 15 days</b> as to
          why penal action under <b>Section 36 of the Legal Metrology Act, 2009</b> should not be initiated.
        </p>

        <p style="font-size:13px;"><b>Compliance Assessment:</b>
          <span style="background:#FFE8E8;color:#DC3545;padding:2px 10px;border-radius:4px;font-weight:bold;">
            {scan.get('compliance_status','Non-Compliant')} — Score {scan.get('compliance_score',0)}/100
          </span>
        </p>

        <div style="margin:14px 0 6px 0;font-size:13px;color:#001255;font-weight:bold;">Detected Violations:</div>
        {_fmt_violations_html(scan.get('violations', []))}

        <p style="font-size:12px;color:#555;margin-top:18px;line-height:1.5;">
          Failure to respond by <b>{reply_deadline}</b> will result in the case being referred for prosecution and
          seizure of stock as per Section 15 &amp; Section 36 of the Legal Metrology Act, 2009.
          You may submit your written reply along with supporting evidence to the office of the undersigned
          or by email to <code>enforcement@metrology.gov.in</code>.
        </p>

        <p style="font-size:13px;margin-top:22px;">
          Yours faithfully,<br/><br/>
          <b>{scan.get('inspector_name','Authorised Legal Metrology Officer')}</b><br/>
          {scan.get('jurisdiction','Field Enforcement Wing')}<br/>
          Officer ID: {scan.get('inspector_id','')}
        </p>
      </td>
    </tr>
    <tr>
      <td style="background:#f7f8fb;color:#8892a6;padding:14px 28px;font-size:10px;text-align:center;">
        This is an automated statutory notice generated by the Legal Metrology Compliance Portal.<br/>
        Digitally signed under authority of the Legal Metrology Act, 2009 &amp; Rules 2011.
      </td>
    </tr>
  </table>
</body></html>
"""


def build_notice_sms(scan: Dict[str, Any], reply_deadline: str, notice_number: str) -> str:
    """Concise SMS body (<= 320 chars)."""
    return (
        f"LEGAL METROLOGY NOTICE {notice_number}\n"
        f"Product: {scan.get('brand_name','')} (Case {scan.get('id','')})\n"
        f"Status: {scan.get('compliance_status','Non-Compliant')} — {scan.get('violations_count',0)} violations under LMPC Rules 2011.\n"
        f"You must reply by {reply_deadline} under Sec 36 LMA 2009. — Ministry of Consumer Affairs"
    )[:320]


async def send_email_notice(to_email: str, subject: str, html_body: str) -> Dict[str, Any]:
    """Send a Section 36 notice via Resend. Returns delivery metadata."""
    api_key = os.environ.get("RESEND_API_KEY")
    from_email = os.environ.get("RESEND_FROM_EMAIL", "onboarding@resend.dev")
    if not api_key:
        raise RuntimeError("RESEND_API_KEY is not configured on the server.")
    
    resend.api_key = api_key
    params = {
        "from": from_email,
        "to": [to_email],
        "subject": subject,
        "html": html_body
    }
    try:
        result = await asyncio.to_thread(resend.Emails.send, params)
        return {
            "channel": "email",
            "provider": "resend",
            "provider_message_id": result.get("id"),
            "status": "sent",
            "recipient": to_email,
            "from": from_email,
            "sent_at": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Resend email failed: {e}")
        raise RuntimeError(f"Email delivery failed: {str(e)}")


async def send_sms_notice(to_phone: str, body: str) -> Dict[str, Any]:
    """Send an SMS notice via Twilio. Requires E.164 format phone (+91...)."""
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_number = os.environ.get("TWILIO_FROM_NUMBER")
    if not (account_sid and auth_token and from_number):
        raise RuntimeError("Twilio SMS credentials are not fully configured on the server.")
    
    # Normalize phone
    to_phone = to_phone.strip()
    if not to_phone.startswith("+"):
        # Assume India country code if no + prefix
        digits = "".join(ch for ch in to_phone if ch.isdigit())
        to_phone = "+91" + digits if len(digits) == 10 else "+" + digits
    
    def _send():
        client = TwilioClient(account_sid, auth_token)
        msg = client.messages.create(body=body, from_=from_number, to=to_phone)
        return msg
        
    try:
        msg = await asyncio.to_thread(_send)
        return {
            "channel": "sms",
            "provider": "twilio",
            "provider_message_id": msg.sid,
            "status": msg.status,
            "recipient": to_phone,
            "from": from_number,
            "sent_at": datetime.now(timezone.utc).isoformat()
        }
    except TwilioRestException as e:
        logger.error(f"Twilio SMS failed: {e}")
        raise RuntimeError(f"SMS delivery failed via Twilio: {e.msg}")
    except Exception as e:
        logger.error(f"Twilio SMS unexpected error: {e}")
        raise RuntimeError(f"SMS delivery failed: {str(e)}")
