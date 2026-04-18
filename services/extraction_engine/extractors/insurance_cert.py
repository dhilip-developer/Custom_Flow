"""
Insurance Certificate Extractor — Extracts structured fields from Insurance Certificate OCR text.
Required by the cross-verifier and customs clearance flow per requirement diagram.
"""
from typing import Any, Dict
from services.extraction_engine.extractors.base import BaseExtractor
from services.extraction_engine.normalizer import (
    normalize_number, normalize_date, prune_empty_fields,
)


class InsuranceCertExtractor(BaseExtractor):

    def extract_fields(self, text: str) -> Dict[str, Any]:
        data: Dict[str, Any] = {}

        # Policy / Certificate number
        data["policy_number"] = self.search_value(text, [
            r"Policy\s*(?:No\.?|Number|#)\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            r"Certificate\s*(?:No\.?|Number|#)\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            r"Cover\s*Note\s*(?:No\.?|#)\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ])

        # Issue date
        data["issue_date"] = normalize_date(self.search_value(text, [
            r"(?:Date\s*of\s*Issue|Policy\s*Date|Date)\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ]))

        data["gst_uin_number"] = self.search_value(text, [
            r"GST\s*(?:/UIN)?\s*(?:No\.?|Number)\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ])

        # Invoice reference
        data["invoice_number"] = self.search_value(text, [
            r"Invoice\s*(?:No\.?|Number|#|Ref)\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ])

        data["invoice_date"] = normalize_date(self.search_value(text, [
            r"Invoice\s*Date\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ]))

        data["address"] = self.search_block(text, r"Address", max_lines=3)
        data["description"] = self.search_block(text, r"Description", max_lines=3)

        data["po_number"] = self.search_value(text, [
            r"P\.?O\.?\s*(?:No\.?|Number|#)\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ])

        # Sum insured / Invoice total value
        amt_raw = self.search_value(text, [
            r"(?:Sum\s*Insured|Insured\s*(?:Amount|Value)|Invoice\s*(?:Total\s*)?Value)\s*[:：]?\s*(?:(?:USD|INR|EUR)[\s]?)?([0-9][0-9,.]*)",
            r"(?:Total|Amount)\s*[:：]?\s*(?:(?:USD|INR|EUR)[\s]?)?([0-9][0-9,.]*)",
        ])
        data["insured_amount"] = normalize_number(amt_raw) if amt_raw else None

        # Currency
        data["currency"] = self.find_currency(text)

        data["pod"] = self.search_value(text, [
            r"POD\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            r"Destination\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ])

        data["pol"] = self.search_value(text, [
            r"POL\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
            r"From\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ])

        data["exchange_rate"] = normalize_number(self.search_value(text, [
            r"Exchange\s*Rate\s*[:：]?\s*(.+?)(?:\s{2,}|\n|$)",
        ]))

        # Description of goods
        data["description_of_goods"] = self.search_block(
            text, r"Description\s*of\s*Goods", max_lines=5
        )

        return prune_empty_fields(data)
