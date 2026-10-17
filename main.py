import re
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="Invoice Field Extractor")


class ExtractRequest(BaseModel):
    text: str = Field(..., description="Free-form invoice text")


class InvoiceExtract(BaseModel):
    vendor: str
    amount: float
    currency: str
    date: str


def extract_vendor(text: str) -> str:
    # Look for common invoice wording.
    patterns = [
        r"(?:from|vendor|supplier|billed by|issued by)\s*[:\-]?\s*([A-Za-z0-9&.,'\- ]+?)(?=\s*(?:Total|Amount|Invoice|Due|Date|Currency|Payment|Address|\n|$))",
        r"([A-Za-z0-9&.,'\- ]+(?:Industries|Ltd\.?|Limited|LLC|Inc\.?|Corporation|Corp\.?|Company|Co\.?|GmbH|Pvt\.?))",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            vendor = match.group(1).strip(" .,:;-")
            if vendor:
                return vendor

    # Best-effort fallback: first non-empty line.
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line

    return "Unknown Vendor"


def extract_amount(text: str) -> float:
    # Handles formats such as 1234.56, 1,234.56, $1234.56, EUR 1234.56.
    patterns = [
        r"(?:total\s*(?:due|amount)?|amount\s*(?:due|payable)?|balance\s*due|grand\s*total)\s*[:\-]?\s*(?:[A-Z]{3}\s*)?[$€£]?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)",
        r"(?:[$€£]\s*|[A-Z]{3}\s*)([0-9][0-9,]*(?:\.[0-9]{1,2})?)",
        r"([0-9][0-9,]*(?:\.[0-9]{1,2})?)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            raw = match.group(1).replace(",", "")
            try:
                return float(raw)
            except ValueError:
                continue

    return 0.0


def extract_currency(text: str) -> str:
    symbol_map = {
        "$": "USD",
        "€": "EUR",
        "£": "GBP",
    }

    # Prefer an explicit three-letter code.
    match = re.search(r"\b(USD|EUR|GBP)\b", text, flags=re.IGNORECASE)
    if match:
        return match.group(1).upper()

    # Otherwise infer from a currency symbol.
    for symbol, code in symbol_map.items():
        if symbol in text:
            return code

    return "USD"


def extract_date(text: str) -> str:
    # Already in YYYY-MM-DD form.
    match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if match:
        return match.group(0)

    # Handles 14 July 2026 / July 14, 2026.
    month_names = {
        "january": "01", "february": "02", "march": "03", "april": "04",
        "may": "05", "june": "06", "july": "07", "august": "08",
        "september": "09", "october": "10", "november": "11", "december": "12",
    }

    for name, number in month_names.items():
        pattern = rf"\b(\d{{1,2}})\s+{name}\s+(\d{{4}})\b"
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            day = int(match.group(1))
            year = match.group(2)
            return f"{year}-{number}-{day:02d}"

        pattern = rf"\b{name}\s+(\d{{1,2}}),?\s+(\d{{4}})\b"
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            day = int(match.group(1))
            year = match.group(2)
            return f"{year}-{number}-{day:02d}"

    # Handles 14/07/2026 or 07/14/2026.
    match = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", text)
    if match:
        first, second, year = match.groups()
        month = int(first)
        day = int(second)

        # If the first number cannot be a month, treat it as the day.
        if month > 12:
            month, day = day, month

        return f"{year}-{month:02d}-{day:02d}"

    return "1970-01-01"


@app.post("/extract", response_model=InvoiceExtract)
def extract_invoice(request: ExtractRequest) -> InvoiceExtract:
    text = request.text or ""

    return InvoiceExtract(
        vendor=extract_vendor(text),
        amount=extract_amount(text),
        currency=extract_currency(text),
        date=extract_date(text),
    )
    