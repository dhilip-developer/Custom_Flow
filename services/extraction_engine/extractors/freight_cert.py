"""
Freight Certificate Extractor — Extracts structured fields from Freight Certificate OCR text.
"""
from typing import Any, Dict
from services.extraction_engine.extractors.base import BaseExtractor
from services.extraction_engine.normalizer import (
    normalize_number, prune_empty_fields,
)


class FreightCertExtractor(BaseExtractor):

    def extract_fields(self, text: str) -> Dict[str, Any]:
        data: Dict[str, Any] = {}

        data["bl_number"] = self.search_value(text, [
            r"(?:H?B/?L|Bill)\s*(?:No\.?|Number|#)\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            r"HBL\s*(?:No\.?|#)\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            r"MBL\s*(?:No\.?|#)\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ])

        # Freight charges
        amt_raw = self.search_value(text, [
            r"(?:Total|Net)\s*(?:Freight|Amount)\s*[:：]?\s*(?:(?:USD|US\s*\$|\$)\s*)?([0-9][0-9,.]*)",
            r"(?:Ocean\s*)?Freight\s*(?:Charges?|Amount)?\s*[:：]?\s*(?:(?:USD|US\s*\$|\$)\s*)?([0-9][0-9,.]*)",
        ])
        data["freight_charges"] = normalize_number(amt_raw) if amt_raw else None

        data["currency"] = self.find_currency(text) or "USD"

        # Weight
        wt_raw = self.search_value(text, [
            r"(?:Gross\s*)?Weight\s*[:：]?\s*([0-9][0-9,.\s]*(?:KGS?|MT)?)",
            r"(?:C\.?WT|Chargeable\s*Weight)\s*[:：]?\s*([0-9][0-9,.\s]*(?:KGS?|MT)?)",
        ])
        data["weight"] = normalize_number(wt_raw) if wt_raw else None

        data["incoterms"] = self.search_value(text, [
            r"\b(FOB|CIF|CFR|CNF|EXW|Ex\s*works|FCA|DAP|DDP|CPT|CIP)\b",
        ])

        # Packages
        data["packages"] = self.search_value(text, [
            r"(?:No\.?\s*of\s*)?Packages?\s*[:：]?\s*(\d+)",
            r"(\d+)\s*(?:Packages?|Pkgs?)",
        ])

        data["pol"] = self.search_value(text, [
            r"POL\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            r"Port\s*of\s*Loading\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ])

        data["pod"] = self.search_value(text, [
            r"POD\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            r"Port\s*of\s*Discharge\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            r"Port\s*of\s*Destination\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ])

        data["consignee"] = self.search_block(text, r"Consignee", max_lines=3)

        data["excharge_charges"] = self.search_value(text, [
            r"Excharge\s*Charges?\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            r"Extra\s*Charges?\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ])

        data["container_type"] = self.search_value(text, [
            r"Container\s*Type\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            r"(20FT|40FT|40HQ|45FT|REF|FR|OT)",
        ])

        data["date"] = normalize_date(self.search_value(text, [
            r"Date\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ]))

        return prune_empty_fields(data)
