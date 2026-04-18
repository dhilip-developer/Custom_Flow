"""
Invoice Extractor — Extracts structured fields from Invoice OCR text.
Handles both standard "Label: Value" and parallel-column OCR layouts.
"""
import re
from typing import Any, Dict, List, Optional
from services.extraction_engine.extractors.base import BaseExtractor
from services.extraction_engine.normalizer import (
    normalize_number, normalize_date, clean_whitespace, prune_empty_fields,
)
from services.extraction_engine.table_parser import extract_line_items


# Known labels in parallel-column Invoice OCR (normalized — no punctuation)
COLUMN_LABELS_NORMALIZED = {
    "invoice no": "invoice no",
    "invoice no.": "invoice no",
    "p.o.no": "p.o.no",
    "po no": "p.o.no",
    "p.o. no": "p.o.no",
    "incoterms": "incoterms",
    "payment terms": "payment terms",
    "carrier": "carrier",
    "ship cond": "ship cond",
    "shipment no": "shipment no",
    "shipment no.": "shipment no",
    "shipment date": "shipment date",
    "invoice date": "invoice date",
}


class InvoiceExtractor(BaseExtractor):

    def extract_fields(self, text: str) -> Dict[str, Any]:
        data: Dict[str, Any] = {}

        # --- Phase 0: Detect and parse parallel-column layout ---
        column_data = self._extract_parallel_columns(text)

        # --- Phase 1: Primary field extraction ---
        # Invoice Number
        data["invoice_number"] = (
            column_data.get("invoice no")
            or self.search_value(text, [
                r"Invoice\s*No\.?\s*[:：]\s*(.+?)(?:\s{2,}|\n|$)",
                r"Inv\.?\s*(?:No\.?|#)\s*[:：]\s*(.+?)(?:\s{2,}|\n|$)",
                r"INVOICE\s+NO\.?\s*[:：]\s*(.+?)(?:\s{2,}|\n|$)",
                r"INVOICE\s+NUMBER\s*[:：]\s*(.+?)(?:\s{2,}|\n|$)",
            ])
        )

        # Invoice Date
        raw_date = (
            column_data.get("invoice date")
            or self.search_value(text, [
                r"Invoice\s*Date\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
                r"Inv\.?\s*Date\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
                r"Date\s*of\s*Invoice\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            ])
        )
        data["invoice_date"] = normalize_date(raw_date) if raw_date else None

        # Shipper & Consignee
        data["shipper_name_address"] = self._extract_seller(text)
        data["consignee_name_address"] = self._extract_buyer(text)

        # PO Number & Item
        data["po_number"] = (
            column_data.get("p.o.no")
            or self.search_value(text, [
                r"P\.?O\.?\s*(?:No\.?|Number|#)\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
                r"Purchase\s*Order\s*(?:No\.?|#)?\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            ])
        )
        data["po_item"] = self.search_value(text, [
            r"P\.?O\.?\s*Item\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ])

        # Incoterms
        data["incoterms"] = (
            column_data.get("incoterms")
            or self.search_value(text, [
                r"\b(FOB|CIF|CFR|CNF|EXW|Ex\s*works|FCA|DAP|DDP|CPT|CIP)\b",
            ])
        )

        # Amount & Currency
        data["amount"] = self._extract_total_amount(text)
        data["currency"] = self.find_currency(text)

        # GST Number
        data["gst_number"] = self.search_value(text, [
            r"GST\s*(?:No\.?|IN|Number|Registration)\s*[:：]?\s*(\w{15})",
            r"GSTIN\s*[:：]?\s*(\w{15})",
            r"(\d{2}[A-Z]{5}\d{4}[A-Z]\d[A-Z\d]{2})",  # GST format
        ])

        # Product Info (Primary item if multiple exist)
        items = self._extract_items_from_ocr(text)
        if items:
            first_item = items[0]
            data["part_no"] = first_item.get("part_no") or first_item.get("code")
            data["description"] = first_item.get("name") or first_item.get("description")
            data["qty_units"] = normalize_number(first_item.get("quantity"))
            data["unit_price"] = normalize_number(first_item.get("unit_price"))
            data["net_value"] = normalize_number(first_item.get("total_price"))
            data["gross_value"] = data["net_value"] # Heuristic

        # Country of Origin
        data["country_of_origin"] = self.search_value(text, [
            r"Country\s*of\s*Origin\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ])

        # HSN Codes
        data["hsn_codes"] = self._extract_hsn_codes(text)

        return prune_empty_fields(data)

    def _extract_parallel_columns(self, text: str) -> Dict[str, str]:
        """
        Detect parallel-column OCR layout where labels and values are in
        separate vertical blocks:

            Line 31: 'Invoice No.'       ← Label block start
            Line 32: 'P.O.No'
            Line 33: 'Incoterms'
            Line 34: 'Payment Terms'
            Line 35: 'Carrier'
            Line 36: 'Ship Cond'
            Line 37: 'Shipment No.'
            Line 38: 'Shipment Date'
            Line 39: 'Invoice Date'      ← Label block end
            Line 40: '501656989'          ← Value block start (same order)
            Line 41: 'PO845487'
            ...
            Line 49: '30.01.2026'

        Returns a dict mapping normalized label → value.
        """
        lines = text.split("\n")
        result: Dict[str, str] = {}

        # Find all lines that match known labels + their positions
        label_hits: List[tuple] = []  # (line_index, normalized_label)
        for i, line in enumerate(lines):
            stripped = line.strip().lower().rstrip(".")
            # Try exact match and with trailing period
            for raw_label, norm_label in COLUMN_LABELS_NORMALIZED.items():
                if stripped == raw_label or stripped == raw_label.rstrip("."):
                    label_hits.append((i, norm_label))
                    break

        if len(label_hits) < 3:
            return result  # Not enough labels for a column layout

        # Find the contiguous block of labels
        # Labels should be consecutive or near-consecutive lines
        first_label_line = label_hits[0][0]
        last_label_line = label_hits[-1][0]
        block_length = last_label_line - first_label_line + 1

        # All lines in the block [first_label_line .. last_label_line]
        # Values follow immediately after in the same order
        value_start = last_label_line + 1

        # Map each label to its value based on its position IN the block
        for line_idx, norm_label in label_hits:
            position_in_block = line_idx - first_label_line
            value_line = value_start + position_in_block
            if value_line < len(lines):
                value = lines[value_line].strip()
                # Don't accept another label as a value
                if value and value.strip().lower().rstrip(".") not in COLUMN_LABELS_NORMALIZED:
                    result[norm_label] = value

        if result:
            print(f"[Invoice] Parallel-column detected: {len(result)} pairs "
                  f"(labels L{first_label_line}-L{last_label_line}, values L{value_start}+)")

        return result

    def _extract_buyer(self, text: str) -> Optional[str]:
        """Extract buyer/consignee from address blocks or labels."""
        # Try standard label patterns first
        buyer = self.search_value(text, [
            r"(?:Buyer|Bill\s*To|Consignee)\s*[:：]\s*(.+?)(?:\s{2,}|\n|$)",
        ])
        if buyer and len(buyer) > 10:
            return buyer

        # Heuristic: Look for company names (LTD/LLC/PVT/LLP/CO) in the text
        # First company = seller, second unique company = buyer
        companies = re.findall(
            r"([A-Z][A-Z\s&().,]+?(?:LTD|LLC|INC|PVT|LLP|CORP|CO)\.?(?:\s*,?\s*(?:LTD|LLC|INC|PVT|LLP)\.?)?)",
            text,
        )
        if len(companies) >= 2:
            seller_name = clean_whitespace(companies[0])
            for comp in companies[1:]:
                cleaned = clean_whitespace(comp)
                # Skip duplicates and very short matches
                if len(cleaned) > 10 and cleaned.upper() != seller_name.upper():
                    return cleaned

        # Fallback: search for multi-line company block after specific headers
        buyer = self.search_block(text, r"(?:Invoice\s*to|Ship\s*To|Sold\s*to)", max_lines=3)
        if buyer and len(buyer) > 5:
            return buyer

        return None

    def _extract_seller(self, text: str) -> Optional[str]:
        """Extract seller/exporter — usually the first company name after the header."""
        # Try standard label
        seller = self.search_value(text, [
            r"(?:Seller|Exporter|Shipper|Ship\s*From|Sold\s*By)\s*[:：]\s*(.+?)(?:\s{2,}|\n|$)",
        ])
        if seller:
            return seller

        # Heuristic: First company-like name in the document (usually the sender)
        m = re.search(
            r"([A-Z][A-Z\s&().,]+(?:LTD|LLC|INC|PVT|LLP|CORP|CO)\b[A-Z.,\s]*)",
            text,
        )
        if m:
            return clean_whitespace(m.group(1))
        return None

    def _extract_total_amount(self, text: str) -> Optional[float]:
        """
        Extract the TOTAL amount — must be near a 'Total' keyword.
        Avoids grabbing commodity codes or other large numbers.
        """
        # Strategy 1: Look for "TOTAL" at end of document — grab LAST non-zero amount
        lines = text.split("\n")
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i].strip()
            if re.match(r"^TOTAL\b", line, re.IGNORECASE):
                # Collect all decimal amounts in the next few lines, take last non-zero
                candidates = []
                for j in range(i, min(i + 6, len(lines))):
                    for m in re.finditer(r"(\d[\d,]*\.\d{2})", lines[j]):
                        val = normalize_number(m.group(1))
                        if val and val > 0:
                            candidates.append(val)
                if candidates:
                    return candidates[-1]  # Last non-zero amount near TOTAL

        # Strategy 2: "Total net value" or "Total Amount" with number
        total_raw = self.search_value(text, [
            r"TOTAL\s*(?:net\s*value|Amount|Value|Invoice)?\s*(?:USD|INR|EUR|GBP|₹|\$)?\s*(?:USD|INR)?\s*(\d[\d,]*\.\d{2})",
            r"(?:Grand\s*Total|Net\s*Total|Payable)\s*(?:USD|INR|EUR|GBP|₹|\$)?\s*(\d[\d,]*\.\d{2})",
        ])
        if total_raw:
            return normalize_number(total_raw)

        # Strategy 3: Last "USD X,XXX.XX" pattern in the document
        all_amounts = re.findall(r"(?:USD|INR|EUR)\s+(\d[\d,]*\.\d{2})", text)
        if all_amounts:
            return normalize_number(all_amounts[-1])

        return None

    def _extract_hsn_codes(self, text: str) -> Optional[List[str]]:
        """Extract HSN/Commodity codes — typically 8-10 digit numbers near 'Commodity' or 'HSN' keywords."""
        codes: List[str] = []

        # Look for codes near "Commodity Code" or "HSN" labels
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if re.search(r"(?:Commodity|HSN|SAC)\s*(?:Code)?", line, re.IGNORECASE):
                # Check next few lines for the actual code
                for j in range(i + 1, min(i + 5, len(lines))):
                    m = re.match(r"^\s*(\d{8,10})\s*$", lines[j])
                    if m:
                        codes.append(m.group(1))
                        break

        # Also try inline patterns
        inline = self.search_all_matches(
            text,
            r"(?:HSN|SAC)\s*(?:Code|/SAC)?\s*[:：]?\s*(\d{4,10})",
        )
        codes.extend(inline)

        return list(set(codes)) if codes else None

    def _extract_items_from_ocr(self, text: str) -> Optional[List[Dict[str, Any]]]:
        """
        Extract line items from OCR text.
        Handles both tabular and parallel-column item layouts.
        """
        items: List[Dict[str, Any]] = []
        lines = text.split("\n")

        # Strategy 1: Look for "Material Description" block → value on next lines
        desc_start = None
        for i, line in enumerate(lines):
            if re.search(r"Material\s*\n?Description|Description\s*of\s*Goods", line, re.IGNORECASE):
                desc_start = i
                break

        if desc_start is not None:
            # Find the item description (lines after "Description" that aren't labels)
            item_desc = None
            item_code = None
            qty = None
            unit_price = None
            total_price = None
            hsn = None

            # Scan forward for values
            for i in range(desc_start + 1, min(desc_start + 20, len(lines))):
                line = lines[i].strip()
                if not line:
                    continue

                # Skip label-only lines
                if line.lower() in ("commodity", "code", "ctry/reg", "origin",
                                     "qty.", "ship", "uom", "unit price", "total", "value",
                                     "material", "description"):
                    continue

                # Item description (text-heavy)
                if not item_desc and re.search(r"[A-Za-z]{3,}", line) and not re.match(r"^\d+$", line):
                    # But skip "Note:", "Computer Generated", etc.
                    if not re.match(r"(?:Note|Computer|SAQA|Special)", line, re.IGNORECASE):
                        item_desc = line
                    elif re.match(r"SAQA", line):
                        # This is additional product info
                        pass
                    continue

                # Commodity code (8-10 digits)
                if re.match(r"^\d{8,10}$", line):
                    hsn = line
                    continue

                # Quantity (decimal number)
                if re.match(r"^\d+\.\d+$", line) and not qty:
                    qty = line
                    continue

                # Price with USD
                m = re.match(r"(?:USD\s+)?(\d[\d,.]+)", line)
                if m:
                    amount = m.group(1)
                    if not unit_price:
                        unit_price = line
                    elif not total_price:
                        total_price = amount

            if item_desc:
                items.append({
                    "name": item_desc,
                    "quantity": qty,
                    "unit_price": unit_price,
                    "total_price": total_price,
                    "hsn_code": hsn,
                    "batch": None,
                })

        # Strategy 2: Fallback to table parser for more standard layouts
        if not items:
            from services.extraction_engine.table_parser import extract_line_items
            table_items = extract_line_items(text)
            # Filter out footer rows (Total Freight, Tax, Downpayment)
            for item in table_items:
                name = (item.get("name") or "").lower()
                if any(skip in name for skip in [
                    "total", "freight", "tax", "downpayment", "discount",
                    "subtotal", "grand", "net value", "computer generated",
                ]):
                    continue
                items.append(item)

        return items if items else None
