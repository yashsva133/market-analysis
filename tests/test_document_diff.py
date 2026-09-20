"""Tests for Document Diff and Filing Comparison Engine."""
import pytest
from packages.documents.diff import DocumentDiffEngine


def test_document_diff_segment_sections():
    text = """
# Financial Performance
Revenue for Q3 was Rs 10,000 Cr.

# Guidance
We expect 15% revenue growth.
"""
    sections = DocumentDiffEngine.segment_sections(text)
    assert "Financial Performance" in sections
    assert "Guidance" in sections
    assert "Rs 10,000 Cr" in sections["Financial Performance"]


def test_document_diff_extract_numbers():
    text = "Revenue reached Rs. 65,420 cr with EBITDA margin of 10.6% and debt of Rs 12,000 cr."
    numbers = DocumentDiffEngine.extract_numbers(text)
    extracted_nums = [n["number"] for n in numbers]
    assert any("65,420" in n for n in extracted_nums)
    assert any("10.6%" in n for n in extracted_nums)


def test_document_diff_comparison():
    prev_text = """
# Financial Performance
Revenue from operations was Rs 60,000 cr with margin at 10.0%.

# Guidance
Management maintains guidance at 12%.
"""
    curr_text = """
# Financial Performance
Revenue from operations was Rs 68,000 cr with margin at 10.8%.

# International Projects
New projects won in Middle East.

# Guidance
Management updates guidance upward to 15%.
"""
    diff = DocumentDiffEngine.compare_documents(
        previous_text=prev_text,
        current_text=curr_text,
        previous_doc_id="doc_prev",
        current_doc_id="doc_curr",
    )

    assert "International Projects" in diff.sections_added
    assert len(diff.sections_removed) == 0
    assert any(m.status == "MODIFIED" for m in diff.sections_modified)
    assert len(diff.numerical_changes) > 0
    assert len(diff.guidance_shifts) > 0
    assert diff.similarity_score > 0.5
