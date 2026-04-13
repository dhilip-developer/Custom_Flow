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

        data["vessel_name"] = self.search_value(text, [
            r"Vessel\s*(?:Name)?\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            r"(?:Ocean\s*)?Vessel\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ])

        # Freight amount — primary extraction target
        amt_raw = self.search_value(text, [
            r"(?:Total|Net)\s*(?:Freight|Amount)\s*[:：]?\s*(?:(?:USD|US\s*\$|\$)\s*)?([0-9][0-9,.]*)",
            r"(?:Ocean\s*)?Freight\s*(?:Charges?|Amount)?\s*[:：]?\s*(?:(?:USD|US\s*\$|\$)\s*)?([0-9][0-9,.]*)",
            r"(?:Grand\s*)?Total\s*[:：]?\s*(?:(?:USD|US\s*\$|\$)\s*)?([0-9][0-9,.]*)",
        ])
        data["total_amount"] = normalize_number(amt_raw) if amt_raw else None

        # Freight certificates are almost always in USD
        data["currency"] = self.find_currency(text) or "USD"

        data["container_number"] = self.search_value(text, [
            r"Container\s*(?:No\.?|Number|#)\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ])

        # Weight
        wt_raw = self.search_value(text, [
            r"(?:Gross\s*)?Weight\s*[:：]?\s*([0-9][0-9,.\s]*(?:KGS?|MT)?)",
        ])
        if wt_raw:
            data["weight"] = normalize_number(wt_raw)

        # Packages
        data["packages"] = self.search_value(text, [
            r"(?:No\.?\s*of\s*)?Packages?\s*[:：]?\s*(\d+)",
            r"(\d+)\s*(?:Packages?|Pkgs?)",
        ])

        data["description_of_goods"] = self.search_block(
            text, r"Description\s*(?:of\s*(?:Goods|Cargo))?", max_lines=5
        )

        # Local charges breakdown (common in freight certs)
        data["local_charges"] = self.search_value(text, [
            r"Local\s*Charges?\s*[:：]?\s*(?:(?:USD|US\s*\$|\$)\s*)?([0-9][0-9,.]*)",
        ])

        data["terminal_handling"] = self.search_value(text, [
            r"(?:THC|Terminal\s*Handling)\s*[:：]?\s*(?:(?:USD|US\s*\$|\$)\s*)?([0-9][0-9,.]*)",
        ])

        return prune_empty_fields(data)
