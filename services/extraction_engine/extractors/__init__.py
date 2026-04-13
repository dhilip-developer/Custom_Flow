"""
Extractors package — per document-type extraction modules.
"""
from services.extraction_engine.extractors.invoice import InvoiceExtractor
from services.extraction_engine.extractors.bill_of_lading import BillOfLadingExtractor
from services.extraction_engine.extractors.packing_list import PackingListExtractor
from services.extraction_engine.extractors.hss_agreement import HSSAgreementExtractor
from services.extraction_engine.extractors.freight_cert import FreightCertExtractor

EXTRACTOR_MAP = {
    "invoice": InvoiceExtractor,
    "bill_of_lading": BillOfLadingExtractor,
    "packing_list": PackingListExtractor,
    "high_seas_sale_agreement": HSSAgreementExtractor,
    "freight_certificate": FreightCertExtractor,
}

__all__ = [
    "EXTRACTOR_MAP",
    "InvoiceExtractor",
    "BillOfLadingExtractor",
    "PackingListExtractor",
    "HSSAgreementExtractor",
    "FreightCertExtractor",
]
