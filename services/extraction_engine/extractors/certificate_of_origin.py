"""
Certificate of Origin Extractor
"""
import re
from typing import Dict, Any
from services.extraction_engine.extractors.base import BaseExtractor
from services.extraction_engine.normalizer import prune_empty_fields


class CertificateOfOriginExtractor(BaseExtractor):

    def extract_fields(self, text: str) -> Dict[str, Any]:
        fields: Dict[str, Any] = {}

        fields["invoice_number"] = self.search_value(text, [r"(?:Invoice)\s*[:.]?\s*(\d{5,})"])
        fields["country_of_origin"] = self.search_value(text, [r"(?:made\s+in|origin)\s*[:.]?\s*(.+?)(?:\n|$)"])
        fields["product_name"] = self.search_value(text, [r"(?:INSTAPAK|MAKROLON|BAYBLEND|DESMODUR|APEC|DESMOPAN)[\s\w]+"])
        fields["batch_number"] = self.search_value(text, [r"(?:Batch\s*(?:number)?)\s*[:.]?\s*([A-Z0-9]+)"])
        fields["net_weight"] = self.search_value(text, [r"N\.?W\.?\s*[:.]?\s*([\d,]+\.?\d*)\s*(?:KG|KGS)"])
        fields["date"] = self.search_value(text, [r"(?:Date|Shanghai|Mumbai)\s*,?\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})"])

        return prune_empty_fields(fields)
