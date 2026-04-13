"""
Insurance Requirement Detection Agent – Orchestrator.

Accepts raw JSON (or a dict), validates it into ShippingDocuments,
runs the detection engine, and returns an AgentResult.
Includes high-precision AI routing for triple-text input.
"""

from __future__ import annotations
from typing import Any, Dict

from app.models.schemas import ShippingDocuments, AgentResult
from app.engine.detector import detect_insurance_requirement, detect_insurance_ai, is_ai_enabled


class InsuranceAgent:
    """High-level agent that ties parsing → detection → result."""

    def analyze(self, data: Dict[str, Any]) -> AgentResult:
        """
        Standard structured analysis for validated JSON/ShippingDocuments.
        """
        docs = ShippingDocuments(**data)
        result = detect_insurance_requirement(docs)
        return result

    def analyze_triple_text(self, invoice: str, pl: str, bol: str) -> AgentResult:
        """
        Specialized analysis for the Triple-Input UI. 
        Uses AI for maximum precision if configured.
        """
        if is_ai_enabled():
            try:
                return detect_insurance_ai(invoice, pl, bol)
            except Exception as exc:
                print(f"Agent 1 AI Analysis failed ({exc}), falling back to heuristic...")
        
        # Fallback to standard extraction + heuristic
        from app.engine.pdf_extractor import extract_data_from_text
        inv_data = extract_data_from_text(invoice)
        pl_data = extract_data_from_text(pl)
        bol_data = extract_data_from_text(bol)
        
        combined_payload = {
            "invoice": inv_data.get("invoice", {}),
            "packing_list": pl_data.get("packing_list", {}),
            "bill_of_lading": bol_data.get("bill_of_lading", {})
        }
        
        return self.analyze(combined_payload)
