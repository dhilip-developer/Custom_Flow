"""
High Seas Sale Agreement Extractor — Extracts structured fields from HSS Agreement OCR text.
"""
from typing import Any, Dict
from services.extraction_engine.extractors.base import BaseExtractor
from services.extraction_engine.normalizer import (
    normalize_number, normalize_date, prune_empty_fields,
)


class HSSAgreementExtractor(BaseExtractor):

    def extract_fields(self, text: str) -> Dict[str, Any]:
        data: Dict[str, Any] = {}

        data["hss_ref_no"] = self.search_value(text, [
            r"(?:HSS|Agreement)\s*(?:Ref(?:erence)?)\s*(?:No\.?|#)?\s*[:：]?\s*(?:No\.?\s*[:：]?\s*)?(.+?)(?:\s{2,}|\n|$)",
            r"Ref(?:erence)?\s*(?:No\.?|#)\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ])

        data["agreement_date"] = normalize_date(self.search_value(text, [
            r"(?:Agreement\s*)?Date(?:d)?\s*[:：]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
            r"Date\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ]))

        data["buyer"] = (
            self.search_value(text, [
                r"(?:Buyer|Transferee|Purchaser)\s*(?:\(Transferee\))?\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            ])
            or self.search_block(text, r"(?:Buyer|Transferee|Purchaser)", max_lines=2)
        )

        data["seller"] = (
            self.search_value(text, [
                r"(?:Seller|Transferor|Vendor)\s*(?:\(Transferor\))?\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            ])
            or self.search_block(text, r"(?:Seller|Transferor|Vendor)", max_lines=2)
        )

        # Re-use BOL patterns for shared fields
        data["bl_number"] = self.search_value(text, [
            r"B/?L\s*(?:No\.?|Number|#)\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            r"Bill\s*(?:of\s*Lading)?\s*(?:No\.?|Number)\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ])

        data["vessel_name"] = self.search_value(text, [
            r"Vessel\s*(?:Name)?\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ])

        data["port_of_loading"] = self.search_value(text, [
            r"Port\s*of\s*Load(?:ing)?\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ])

        data["port_of_destination"] = self.search_value(text, [
            r"Port\s*of\s*(?:Disch(?:arge)?|Destination)\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ])

        # Foreign invoice details
        data["foreign_invoice_number"] = self.search_value(text, [
            r"(?:Foreign|Original|Supplier)\s*Invoice\s*(?:No\.?|Number|#)\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ])

        data["foreign_invoice_date"] = normalize_date(self.search_value(text, [
            r"(?:Foreign|Original|Supplier)\s*Invoice\s*Date\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ]))

        amt_raw = self.search_value(text, [
            r"(?:Foreign|Original|Supplier)\s*Invoice\s*(?:Amount|Value)\s*[:：]?\s*(?:(?:USD|INR|EUR)[\s]?)?([0-9][0-9,.]*)",
            r"Invoice\s*(?:Amount|Value)\s*[:：]?\s*(?:(?:USD|INR|EUR)[\s]?)?([0-9][0-9,.]*)",
        ])
        data["foreign_invoice_amount"] = normalize_number(amt_raw) if amt_raw else None

        data["currency"] = self.find_currency(text)

        data["incoterms"] = self.search_value(text, [
            r"\b(FOB|CIF|CFR|CNF|EXW|FCA|DAP|DDP|CPT|CIP|DAT|DPU|FAS)\b",
        ])

        data["buyer_po_number"] = self.search_value(text, [
            r"(?:Buyer'?s?\s*)?P\.?O\.?\s*(?:No\.?|Number|#)\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            r"Purchase\s*Order\s*(?:No\.?|#)?\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ])

        data["buyer_po_date"] = normalize_date(self.search_value(text, [
            r"(?:Buyer'?s?\s*)?P\.?O\.?\s*Date\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ]))

        return prune_empty_fields(data)
