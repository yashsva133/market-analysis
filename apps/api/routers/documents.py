"""Documents and Filing Diff API Router.

Provides endpoints to inspect extracted documents, page text citations,
and perform differential analysis between consecutive corporate filings.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from packages.documents.diff import DocumentDiffEngine, DocumentDiffResult

router = APIRouter(prefix="/api/documents", tags=["documents"])


class DocumentDiffRequest(BaseModel):
    previous_doc_id: Optional[str] = None
    current_doc_id: Optional[str] = None
    previous_text: Optional[str] = None
    current_text: Optional[str] = None


@router.get("/list")
async def list_documents(
    company_symbol: Optional[str] = Query(None, description="Filter by company symbol (e.g. RELIANCE, LT)"),
    doc_type: Optional[str] = Query(None, description="ANNUAL_REPORT, RESULTS, PRESENTATION, etc."),
    limit: int = Query(20, ge=1, le=100),
):
    """List extracted documents with checksums, page counts, and metadata."""
    # Return representative registered document records
    docs = [
        {
            "id": "doc-lt-q3-fy26",
            "company_symbol": "LT",
            "company_name": "Larsen & Toubro Ltd",
            "title": "L&T Q3 FY26 Financial Results & Investor Presentation",
            "doc_type": "RESULTS",
            "published_at": "2026-01-28T14:30:00+05:30",
            "source": "NSE",
            "page_count": 24,
            "sha256": "4b2e8812cfa88390b1e1564f9b2d8e4f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d",
            "url": "https://nsearchives.nseindia.com/corporate/LT_28012026.pdf",
        },
        {
            "id": "doc-lt-q2-fy26",
            "company_symbol": "LT",
            "company_name": "Larsen & Toubro Ltd",
            "title": "L&T Q2 FY26 Financial Results & Investor Presentation",
            "doc_type": "RESULTS",
            "published_at": "2025-10-25T15:00:00+05:30",
            "source": "NSE",
            "page_count": 22,
            "sha256": "9a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b",
            "url": "https://nsearchives.nseindia.com/corporate/LT_25102025.pdf",
        },
        {
            "id": "doc-reliance-q3-fy26",
            "company_symbol": "RELIANCE",
            "company_name": "Reliance Industries Ltd",
            "title": "RIL Media Release Q3 FY26 Financial & Operational Performance",
            "doc_type": "RESULTS",
            "published_at": "2026-01-19T18:00:00+05:30",
            "source": "BSE",
            "page_count": 32,
            "sha256": "8f7e6d5c4b3a291807f6e5d4c3b2a1908f7e6d5c4b3a291807f6e5d4c3b2a190",
            "url": "https://www.bseindia.com/xml-data/corpfiling/AttachLive/RELIANCE_19012026.pdf",
        },
    ]

    if company_symbol:
        docs = [d for d in docs if d["company_symbol"].upper() == company_symbol.upper()]
    if doc_type:
        docs = [d for d in docs if d["doc_type"].upper() == doc_type.upper()]

    return {"status": "ok", "count": len(docs), "documents": docs[:limit]}


@router.post("/diff", response_model=DocumentDiffResult)
async def diff_documents(request: DocumentDiffRequest):
    """Compare two filing texts or document IDs, identifying section differences,

    numerical shifts (e.g. margin/revenue deltas), and updated guidance.
    """
    prev_text = request.previous_text
    curr_text = request.current_text

    # If texts are omitted but document IDs provided, load representative filing text
    if not prev_text and request.previous_doc_id == "doc-lt-q2-fy26":
        prev_text = """
# Financial Performance
Revenue from operations stood at Rs. 61,554 cr for Q2 FY26, registering an 18% growth year-on-year.
EBITDA margin was reported at 10.2%. Order inflow for the quarter was Rs. 80,045 cr.
Total order book reached Rs. 510,400 cr as of September 30, 2025.

# Guidance and Outlook
Management maintains order inflow guidance of 12-15% growth for FY26.
Operating margin guidance is expected to remain between 10.0% to 10.5%.
Working capital as a percentage of revenue is targeted at 16.5%.
"""

    if not curr_text and request.current_doc_id == "doc-lt-q3-fy26":
        curr_text = """
# Financial Performance
Revenue from operations stood at Rs. 65,420 cr for Q3 FY26, registering a 19.5% growth year-on-year.
EBITDA margin improved to 10.6%. Order inflow for the quarter was Rs. 89,200 cr.
Total order book reached Rs. 535,000 cr as of December 31, 2025.

# International Expansion
International orders constituted 38% of total order inflow during Q3 FY26, driven by Middle East energy transition projects.

# Guidance and Outlook
Management updates order inflow guidance upwards to 15-18% growth for FY26.
Operating margin guidance is upgraded to 10.5% to 11.0%.
Working capital as a percentage of revenue is optimized to 15.8%.
"""

    if not prev_text or not curr_text:
        raise HTTPException(
            status_code=400,
            detail="Must provide either valid document IDs with stored text or raw 'previous_text' and 'current_text'."
        )

    result = DocumentDiffEngine.compare_documents(
        previous_text=prev_text,
        current_text=curr_text,
        previous_doc_id=request.previous_doc_id,
        current_doc_id=request.current_doc_id,
    )
    return result
