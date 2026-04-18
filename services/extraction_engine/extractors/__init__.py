"""
Extractors package — per document-type extraction modules.
"""
from services.extraction_engine.extractors.invoice import InvoiceExtractor
from services.extraction_engine.extractors.bill_of_lading import BillOfLadingExtractor
from services.extraction_engine.extractors.packing_list import PackingListExtractor
from services.extraction_engine.extractors.hss_agreement import HSSAgreementExtractor
from services.extraction_engine.extractors.freight_cert import FreightCertExtractor
from services.extraction_engine.extractors.weight_note import WeightNoteExtractor
from services.extraction_engine.extractors.certificate_of_origin import CertificateOfOriginExtractor
from services.extraction_engine.extractors.certificate_of_analysis import CertificateOfAnalysisExtractor
from services.extraction_engine.extractors.insurance_cert import InsuranceCertExtractor
from services.extraction_engine.extractors.base import BaseExtractor

EXTRACTOR_MAP = {
    "invoice": InvoiceExtractor,
    "bill_of_lading": BillOfLadingExtractor,
    "packing_list": PackingListExtractor,
    "high_seas_sale_agreement": HSSAgreementExtractor,
    "freight_certificate": FreightCertExtractor,
    "weight_note": WeightNoteExtractor,
    "certificate_of_origin": CertificateOfOriginExtractor,
    "certificate_of_analysis": CertificateOfAnalysisExtractor,
    "insurance_certificate": InsuranceCertExtractor,
}

class SupportDocExtractor(BaseExtractor):
    """Dummy extractor for support documents that don't need structured extraction."""
    def extract_fields(self, text: str) -> dict:
        return {"notes": "Support document captured"}

# Support documents that just pass through the pipeline
for doc_type in ["iec_certificate", "gst_certificate", "letter_of_authority", "hss_cover_letter", "customs_letter", "shipping_letter"]:
    EXTRACTOR_MAP[doc_type] = SupportDocExtractor

__all__ = [
    "EXTRACTOR_MAP",
    "InvoiceExtractor",
    "BillOfLadingExtractor",
    "PackingListExtractor",
    "HSSAgreementExtractor",
    "FreightCertExtractor",
    "WeightNoteExtractor",
    "CertificateOfOriginExtractor",
    "CertificateOfAnalysisExtractor",
]
