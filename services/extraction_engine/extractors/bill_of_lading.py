"""
Bill of Lading Extractor — Extracts structured fields from BOL OCR text.
"""
import re
from typing import Any, Dict
from services.extraction_engine.extractors.base import BaseExtractor
from services.extraction_engine.normalizer import (
    normalize_number, normalize_weight, normalize_date,
    normalize_container_number, prune_empty_fields,
)


class BillOfLadingExtractor(BaseExtractor):

    def extract_fields(self, text: str) -> Dict[str, Any]:
        data: Dict[str, Any] = {}

        data["bl_number"] = self.search_value(text, [
            r"B/?L\s*(?:No\.?|Number|#)\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            r"Bill\s*(?:of\s*Lading)?\s*(?:No\.?|Number|#)\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            r"HBL\s*(?:No\.?|#)\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            r"MBL\s*(?:No\.?|#)\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            r"BILL\s+NO\.?\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ])

        data["bl_date"] = normalize_date(self.search_value(text, [
            r"B/?L\s*Date\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            r"Date\s*of\s*Issue\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            r"Shipped\s*on\s*Board\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            r"On\s*Board\s*Date\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ]))

        data["shipper"] = (
            self.search_value(text, [
                r"Shipper\s*[:：]\s*(.+?)(?:\s{2,}|\n|$)",
            ])
            or self.search_block(text, r"Shipper", max_lines=3)
        )

        data["consignee"] = (
            self.search_value(text, [
                r"Consignee\s*[:：]\s*(.+?)(?:\s{2,}|\n|$)",
            ])
            or self.search_block(text, r"Consignee", max_lines=3)
        )

        data["notify_party"] = self.search_block(text, r"Notify\s*Party", max_lines=3)

        data["vessel_name"] = self.search_value(text, [
            r"(?:Ocean\s*)?Vessel\s*(?:Name)?\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            r"(?:Pre.?Carriage|Mother)\s*Vessel\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            r"Vessel\s*/\s*Voyage\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ])

        data["voyage_no"] = self.search_value(text, [
            r"Voyage\s*(?:No\.?)?\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            r"Voy\.?\s*(?:No\.?)?\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ])

        data["port_of_loading"] = self.search_value(text, [
            r"Port\s*of\s*Load(?:ing)?\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            r"Loading\s*Port\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            r"Place\s*of\s*Receipt\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ])

        data["port_of_destination"] = self.search_value(text, [
            r"Port\s*of\s*Disch(?:arge)?\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            r"Port\s*of\s*Destination\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            r"Destination\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            r"Place\s*of\s*Delivery\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            r"Final\s*Destination\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ])

        # Container number (ISO 6346: XXXX1234567)
        container_raw = self.search_value(text, [
            r"Container\s*(?:No\.?|Number|#)\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ])
        if not container_raw:
            # Direct pattern match
            m = re.search(r"([A-Z]{4}\d{7})", text)
            container_raw = m.group(1) if m else None
        data["container_number"] = normalize_container_number(container_raw) if container_raw else None

        data["seal_number"] = self.search_value(text, [
            r"Seal\s*(?:No\.?|Number|#)\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ])

        # Weights
        gross_raw = self.search_value(text, [
            r"Gross\s*Weight\s*[:：]?\s*([0-9][0-9,.\s]*(?:KGS?|MT|LBS?)?)",
            r"Gr(?:oss)?\.?\s*W(?:ei)?g(?:h)?t\.?\s*[:：]?\s*([0-9][0-9,.\s]*(?:KGS?|MT)?)",
        ])
        data["gross_weight"] = normalize_weight(gross_raw) if gross_raw else None

        net_raw = self.search_value(text, [
            r"Net\s*Weight\s*[:：]?\s*([0-9][0-9,.\s]*(?:KGS?|MT|LBS?)?)",
        ])
        data["net_weight"] = normalize_weight(net_raw) if net_raw else None

        # Package count
        pkg_raw = self.search_value(text, [
            r"(\d+)\s*(?:Packages?|Pkgs?|Pallets?|Cartons?|Drums?|Bags?|Cases?|Bundles?|Pieces?|Pcs?)",
            r"(?:No\.?\s*of\s*)?(?:Packages?|Pkgs?)\s*[:：]?\s*(\d+)",
            r"Total\s*(?:Packages?|Pkgs?)\s*[:：]?\s*(\d+)",
        ])
        data["package_count"] = int(pkg_raw) if pkg_raw and pkg_raw.isdigit() else normalize_number(pkg_raw) if pkg_raw else None

        data["freight_terms"] = self.search_value(text, [
            r"Freight\s*(Prepaid|Collect|As\s*Arranged)",
            r"(FREIGHT\s+PREPAID|FREIGHT\s+COLLECT)",
        ])

        data["description_of_goods"] = self.search_block(
            text, r"Description\s*of\s*(?:Goods|Packages|Cargo)", max_lines=5
        )

        return prune_empty_fields(data)
