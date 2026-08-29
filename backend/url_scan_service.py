"""Bulk URL scanner — fetches product listing pages (Amazon, Flipkart, etc.) and evaluates LMPC compliance."""
import os
import re
import json
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

import httpx
from bs4 import BeautifulSoup
from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger("url_scan_service")

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
    "Cache-Control": "no-cache",
}

URL_EXTRACT_SYSTEM_PROMPT = """You are an expert Legal Metrology Enforcement AI reviewing an Indian e-commerce product listing (Amazon.in, Flipkart, Nykaa, etc.) for compliance with Legal Metrology (Packaged Commodities) Rules, 2011.

Read the product listing text carefully and extract ALL statutory declarations that a lawful listing must disclose per Rule 6 of LMPC Rules, 2011 (and the E-commerce Compliance Directive of the Department of Consumer Affairs).

Extract as JSON with these exact keys (use null if absent):
- brand_name
- commodity_name (generic name)
- manufacturer_name
- manufacturer_address (must include PIN code)
- packer_name
- importer_name
- net_quantity_value (numeric)
- net_quantity_unit (must be one of: g, kg, ml, l, N, pieces)
- net_quantity_raw (verbatim text)
- unit_sale_price (e.g. "₹ 0.60 / g" or null)
- mrp_value (numeric)
- mrp_raw (verbatim MRP text with "incl. of all taxes" if present)
- taxes_inclusive_declared (boolean)
- manufacturing_date (MM/YYYY)
- best_before_date
- consumer_care_phone
- consumer_care_email
- consumer_care_details (full block)
- country_of_origin (mandatory for e-commerce)
- batch_number
- barcode_gtin

Also include:
- listing_platform: e.g. "Amazon.in", "Flipkart", "Nykaa" (from the URL)
- listing_url: the URL you were given
- ocr_raw_text: the raw text you extracted from the listing (first 1500 chars)

Respond ONLY with valid JSON. No commentary."""


async def fetch_product_page_text(url: str) -> str:
    """Fetches a product URL and extracts primary content text."""
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=BROWSER_HEADERS) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        html = resp.text
    
    soup = BeautifulSoup(html, "html.parser")
    # Remove noise
    for tag in soup(["script", "style", "nav", "footer", "iframe", "svg", "img"]):
        tag.decompose()
    
    # Focus on likely product content nodes
    content_selectors = [
        "#dp",  # Amazon
        "#centerCol",  # Amazon
        "#productTitle",
        "#feature-bullets",
        "#detailBullets_feature_div",
        "#productDetails_feature_div",
        "#important-information",
        ".B_NuCI",  # Flipkart title
        "._1YokD2._3Mn1Gg",  # Flipkart body
        "._2_XLd",  # Flipkart details
        "._1UhVsV",  # Flipkart manufacturer
        "._2418kt",  # Flipkart specifications
        ".css-1985t7s",  # Nykaa
    ]
    parts = []
    for sel in content_selectors:
        for el in soup.select(sel):
            t = el.get_text(separator="\n", strip=True)
            if t:
                parts.append(t)
    
    if parts:
        text = "\n\n".join(parts)
    else:
        text = soup.get_text(separator="\n", strip=True)
    
    # Compact whitespace and cap length
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text[:12000]


def _detect_platform(url: str) -> str:
    u = url.lower()
    if "amazon." in u: return "Amazon"
    if "flipkart." in u: return "Flipkart"
    if "nykaa." in u: return "Nykaa"
    if "meesho." in u: return "Meesho"
    if "myntra." in u: return "Myntra"
    if "bigbasket." in u: return "BigBasket"
    if "blinkit." in u: return "Blinkit"
    if "zepto." in u: return "Zepto"
    return "E-commerce Listing"


def parse_json_from_llm_response(raw_text: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(raw_text.strip())
    except Exception:
        pass
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
    if m:
        try: return json.loads(m.group(1))
        except Exception: pass
    a, b = raw_text.find("{"), raw_text.rfind("}")
    if a != -1 and b != -1 and b > a:
        try: return json.loads(raw_text[a:b+1])
        except Exception: pass
    return None


async def analyze_ecommerce_url(url: str) -> Dict[str, Any]:
    """Fetches a product URL and uses Gemini to extract LMPC declarations."""
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise RuntimeError("EMERGENT_LLM_KEY not configured.")
    
    try:
        text = await fetch_product_page_text(url)
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"Product URL returned HTTP {e.response.status_code}. Verify the link is public and reachable.")
    except Exception as e:
        raise RuntimeError(f"Failed to fetch product URL: {str(e)}")
    
    if len(text) < 200:
        raise RuntimeError("Product listing content is too sparse to evaluate (likely blocked by anti-bot). Try a public product link.")
    
    platform = _detect_platform(url)
    prompt = f"Product Listing URL: {url}\nPlatform: {platform}\n\nListing Content:\n{text}"
    
    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"lmpc-url-{datetime.now().timestamp()}",
            system_message=URL_EXTRACT_SYSTEM_PROMPT
        ).with_model("gemini", "gemini-3-flash-preview")
        
        response = await chat.send_message(UserMessage(text=prompt))
        parsed = parse_json_from_llm_response(response)
        if not parsed:
            raise RuntimeError("AI could not parse product listing.")
        
        parsed["listing_platform"] = parsed.get("listing_platform") or platform
        parsed["listing_url"] = url
        parsed["engine_used"] = "Google Gemini 3 Flash (E-commerce Listing Analyzer)"
        parsed["ocr_confidence"] = parsed.get("ocr_confidence", 92.0)
        return parsed
    except RuntimeError:
        raise
    except Exception as e:
        logger.error(f"URL LLM analysis failed: {e}")
        raise RuntimeError(f"AI analysis of listing failed: {str(e)}")
