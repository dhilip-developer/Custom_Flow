"""
Packing List Extractor — Extracts structured fields from Packing List OCR text.
"""
from typing import Any, Dict
from services.extraction_engine.extractors.base import BaseExtractor
from services.extraction_engine.normalizer import (
    normalize_number, normalize_weight, normalize_date, prune_empty_fields,
)
from services.extraction_engine.table_parser import extract_line_items


class PackingListExtractor(BaseExtractor):

    def extract_fields(self, text: str) -> Dict[str, Any]:
        data: Dict[str, Any] = {}

        data["invoice_number"] = self.search_value(text, [
            r"Invoice\s*(?:No\.?|Number|#)\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            r"Inv\.?\s*(?:No\.?|#)\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ])

        data["invoice_date"] = normalize_date(self.search_value(text, [
            r"Invoice\s*Date\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            r"Inv\.?\s*Date\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            r"Date\s*of\s*Invoice\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ]))

        data["shipper"] = self.search_block(text, r"Shipper", max_lines=3)
        data["consignee"] = self.search_block(text, r"Consignee", max_lines=3)

        data["po_number"] = self.search_value(text, [
            r"P\.?O\.?\s*(?:No\.?|Number|#)\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            r"Purchase\s*Order\s*(?:No\.?|#)?\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ])

        # Weights
        gross_raw = self.search_value(text, [
            r"(?:Total\s*)?Gross\s*Weight\s*[:：]?\s*([0-9][0-9,.\s]*(?:KGS?|MT|LBS?)?)",
        ])
        data["gross_weight"] = normalize_weight(gross_raw) if gross_raw else None

        net_raw = self.search_value(text, [
            r"(?:Total\s*)?Net\s*Weight\s*[:：]?\s*([0-9][0-9,.\s]*(?:KGS?|MT|LBS?)?)",
        ])
        data["net_weight"] = normalize_weight(net_raw) if net_raw else None

        # Marks and Numbers
        data["marks_and_numbers"] = (
            self.search_value(text, [
                r"Marks?\s*(?:and|&)?\s*Numbers?\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
                r"Shipping\s*Marks?\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            ])
            or self.search_block(text, r"Marks?\s*(?:and|&)?\s*Numbers?", max_lines=4)
        )

        # Pallet details
        data["pallet_details"] = self.search_block(
            text, r"Pallet", max_lines=3
        )

        # Product line items
        items = extract_line_items(text)
        if items:
            first_item = items[0]
            data["qty"] = normalize_number(first_item.get("quantity"))
            data["part_number"] = first_item.get("part_no") or first_item.get("code")
            data["hs_code"] = first_item.get("hsn_code")
            data["description"] = first_item.get("name") or first_item.get("description")

        # Country of Origin
        data["country_of_origin"] = self.search_value(text, [
            r"Country\s*of\s*Origin\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ])

        return prune_empty_fields(data)
