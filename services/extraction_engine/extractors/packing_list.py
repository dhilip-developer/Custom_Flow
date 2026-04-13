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

        data["pl_number"] = self.search_value(text, [
            r"Packing\s*List\s*(?:No\.?|Number|#)\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            r"PL\s*(?:No\.?|#)\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            r"(?:Doc(?:ument)?|Ref(?:erence)?)\s*(?:No\.?|#)\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ])

        data["pl_date"] = normalize_date(self.search_value(text, [
            r"(?:Packing\s*List\s*)?Date\s*[:：]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
            r"Date\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ]))

        # Total packages
        pkg_raw = self.search_value(text, [
            r"Total\s*(?:Packages?|Pkgs?|No\.?\s*of\s*Packages?)\s*[:：]?\s*(\d+)",
            r"(\d+)\s*(?:Packages?|Pkgs?|Pallets?|Cartons?|Drums?|Cases?)\s*(?:Total|in\s*Total)",
            r"(?:No\.?\s*of\s*)?(?:Packages?|Pkgs?)\s*[:：]?\s*(\d+)",
        ])
        data["total_packages"] = int(pkg_raw) if pkg_raw and pkg_raw.isdigit() else normalize_number(pkg_raw) if pkg_raw else None

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

        # Dimensions / CBM
        data["total_cbm"] = self.search_value(text, [
            r"(?:Total\s*)?(?:CBM|Measurement)\s*[:：]?\s*([0-9][0-9,.]*)",
        ])

        # Pallet details
        data["pallet_details"] = self.search_block(
            text, r"Pallet", max_lines=3
        )

        # Product line items
        items = extract_line_items(text)
        if items:
            data["product_details"] = items

        return prune_empty_fields(data)
