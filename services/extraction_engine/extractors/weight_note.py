"""
Weight Note Extractor — Extracts fields from weight note / weight list documents.
"""
import re
from typing import Dict, Any
from services.extraction_engine.extractors.base import BaseExtractor
from services.extraction_engine.normalizer import prune_empty_fields


class WeightNoteExtractor(BaseExtractor):

    def extract_fields(self, text: str) -> Dict[str, Any]:
        fields: Dict[str, Any] = {}

        fields["document_number"] = self.search_value(text, [r"(?:Weight\s+Note|No\.?)\s*[:.]?\s*(\S+)"])
        fields["date"] = self.search_value(text, [r"(?:Date|Dated)\s*[:.]?\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})"])
        fields["product_name"] = self.search_value(text, [r"(?:INSTAPAK|MAKROLON|BAYBLEND|DESMODUR|APEC|DESMOPAN|PRODUCT\s*:?\s*)([A-Z][A-Z0-9\s]+(?:KG|LTR)?)"])
        fields["batch_number"] = self.search_value(text, [r"(?:Batch\s*(?:No\.?|Number)?)\s*[:.]?\s*([A-Z0-9]+)"])
        fields["country_of_origin"] = self.search_value(text, [r"(?:Country\s+of\s+[Oo]rigin)\s*[:.]?\s*(.+)"])
        fields["container_number"] = self.search_value(text, [r"(?:Container\s*(?:No\.?|Number)?)\s*[:.]?\s*([A-Z]{4}\d{6,7}-?\d?)"])
        fields["gross_weight"] = self._extract_weight(text, "gross")
        fields["net_weight"] = self._extract_weight(text, "net")
        fields["packages"] = self.search_value(text, [r"(\d+)\s*(?:PALLETS|DRUMS|BAGS|PACKAGES|CARTONS)"])
        fields["delivery_number"] = self.search_value(text, [r"(?:delivery\s*(?:no\.?|number)?)\s*[:.]?\s*(\d{8,})"])
        fields["order_number"] = self.search_value(text, [r"(?:order\s*number)\s*[:.]?\s*(\d{8,})"])

        return prune_empty_fields(fields)

    def _extract_weight(self, text: str, weight_type: str) -> Any:
        pattern = rf"(?:{weight_type})\s*[:\s]*\n?\s*([\d,]+\.?\d*)\s*(?:KG|KGS)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1).replace(",", ""))
            except ValueError:
                return match.group(1)
        return None
