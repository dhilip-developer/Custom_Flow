"""
Certificate of Analysis Extractor
"""
import re
from typing import Dict, Any, List
from services.extraction_engine.extractors.base import BaseExtractor
from services.extraction_engine.normalizer import prune_empty_fields


class CertificateOfAnalysisExtractor(BaseExtractor):

    def extract_fields(self, text: str) -> Dict[str, Any]:
        fields: Dict[str, Any] = {}

        fields["product_name"] = self.search_value(text, [r"Product\s*name\s*\n?\s*(.+?)(?:\n|$)"])
        fields["product_number"] = self.search_value(text, [r"Product\s*number\s*\n?\s*(\d+)"])
        fields["batch_number"] = self.search_value(text, [r"Batch\s*(?:no\.?|number)?\s*\n?\s*([A-Z0-9]+)"])
        fields["purchase_order"] = self.search_value(text, [r"Purchase\s*order\s*(?:no\.?)?\s*\n?\s*(\d{8,})"])
        fields["delivery_number"] = self.search_value(text, [r"Delivery\s*(?:no\.?)?\s*\n?\s*(\d{8,})"])
        fields["quantity_delivered"] = self.search_value(text, [r"Quantity\s+delivered\s*\n?\s*([\d,]+\s*(?:KG|KGS|LTR|MT))"])
        fields["date"] = self.search_value(text, [r"Date\s+(\d{4}-\d{2}-\d{2})"])

        # Extract test results table
        fields["test_results"] = self._extract_results(text)

        return prune_empty_fields(fields)

    def _extract_results(self, text: str) -> List[Dict[str, str]]:
        """Extract test parameter results."""
        results = []
        # Pattern: parameter name, method, result, specification, unit
        pattern = r"(NCO|Viscosity|Acidity|Color|Density|pH|Water|Moisture)[\s@°C]*\s+([\w-]+)\s+([\d.<>]+(?:\.\d+)?)\s+([\d.<>\s-]+)\s+(%|mPa\.s|mg/kg|APHA)"
        for match in re.finditer(pattern, text, re.IGNORECASE):
            results.append({
                "parameter": match.group(1).strip(),
                "method": match.group(2).strip(),
                "result": match.group(3).strip(),
                "specification": match.group(4).strip(),
                "unit": match.group(5).strip(),
            })
        return results if results else None
