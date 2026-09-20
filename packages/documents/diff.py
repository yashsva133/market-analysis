"""Document Diff and Filing Comparison Engine.

Enables comparative analysis across repeated corporate filings (e.g. Q3 vs Q4 results,
annual reports, investor presentations, BRSR) to highlight what changed:
- Added / removed sections
- Numerical changes (revenue, EBITDA, order book, debt, margins)
- Guidance and outlook shifts
- Management statement shifts
"""
from typing import Dict, List, Any, Optional
import re
from difflib import SequenceMatcher
from pydantic import BaseModel, Field


class NumericalChange(BaseModel):
    context: str = Field(description="Sentence or line containing the metric")
    previous_value: Optional[str] = None
    current_value: Optional[str] = None
    change_type: str = Field(description="INCREASE, DECREASE, REVISED, or NEW")


class SectionDiff(BaseModel):
    section_name: str
    status: str = Field(description="ADDED, REMOVED, MODIFIED, UNCHANGED")
    previous_snippet: Optional[str] = None
    current_snippet: Optional[str] = None
    similarity: float = 1.0


class DocumentDiffResult(BaseModel):
    previous_doc_id: Optional[str] = None
    current_doc_id: Optional[str] = None
    similarity_score: float
    sections_added: List[str] = []
    sections_removed: List[str] = []
    sections_modified: List[SectionDiff] = []
    numerical_changes: List[NumericalChange] = []
    guidance_shifts: List[Dict[str, str]] = []
    summary: str


class DocumentDiffEngine:
    """Deterministic filing comparator comparing text across reporting periods."""

    GUIDANCE_KEYWORDS = [
        "guidance", "outlook", "target", "expect", "forecast", "project", "anticipate",
        "aim", "plan to achieve", "estimate", "margin guidance", "capex guidance"
    ]

    SECTION_PATTERNS = [
        r"(?:^|\n)(#{1,4}\s+[^\n]+)",
        r"(?:^|\n)([A-Z\s]{4,40}:)",
        r"(?:^|\n)(\d+\.\s+[A-Z][^\n]+)",
    ]

    @classmethod
    def segment_sections(cls, text: str) -> Dict[str, str]:
        """Split document text into logical sections based on headings."""
        if not text or not text.strip():
            return {"Overview": ""}

        lines = text.split("\n")
        sections: Dict[str, List[str]] = {}
        current_section = "Overview"
        sections[current_section] = []

        for line in lines:
            trimmed = line.strip()
            # Detect section heading
            is_header = False
            if trimmed.startswith("#"):
                current_section = trimmed.lstrip("#").strip()
                is_header = True
            elif trimmed.isupper() and 4 < len(trimmed) < 60 and not trimmed.endswith("."):
                current_section = trimmed.title()
                is_header = True
            elif re.match(r"^\d+\.\s+[A-Z]", trimmed):
                current_section = trimmed
                is_header = True

            if is_header:
                if current_section not in sections:
                    sections[current_section] = []
            else:
                sections[current_section].append(line)

        return {k: "\n".join(v).strip() for k, v in sections.items() if "\n".join(v).strip()}

    @classmethod
    def extract_numbers(cls, text: str) -> List[Dict[str, str]]:
        """Extract monetary and percentage figures with surrounding context."""
        results = []
        pattern = re.compile(
            r"((?:Rs\.?|INR|₹)?\s*\d+(?:,\d+)*(?:\.\d+)?(?:\s*(?:cr(?:ore)?s?|lakhs?|mn|bn|%))?)",
            re.IGNORECASE
        )
        for line in text.split("\n"):
            line_clean = line.strip()
            if not line_clean:
                continue
            matches = pattern.findall(line_clean)
            for m in matches:
                m_str = m.strip()
                if any(c.isdigit() for c in m_str):
                    results.append({"number": m_str, "context": line_clean})
        return results

    @classmethod
    def compare_documents(
        cls,
        previous_text: str,
        current_text: str,
        previous_doc_id: Optional[str] = None,
        current_doc_id: Optional[str] = None,
    ) -> DocumentDiffResult:
        """Compare two document texts and produce structured diff."""
        prev_sections = cls.segment_sections(previous_text)
        curr_sections = cls.segment_sections(current_text)

        prev_names = set(prev_sections.keys())
        curr_names = set(curr_sections.keys())

        added = sorted(list(curr_names - prev_names))
        removed = sorted(list(prev_names - curr_names))
        common = sorted(list(prev_names & curr_names))

        modified_diffs: List[SectionDiff] = []
        overall_sim = SequenceMatcher(None, previous_text, current_text).ratio()

        for name in common:
            p_text = prev_sections[name]
            c_text = curr_sections[name]
            sim = SequenceMatcher(None, p_text, c_text).ratio()
            if sim < 0.95:
                status = "MODIFIED"
            else:
                status = "UNCHANGED"

            modified_diffs.append(
                SectionDiff(
                    section_name=name,
                    status=status,
                    previous_snippet=p_text[:200] + ("..." if len(p_text) > 200 else ""),
                    current_snippet=c_text[:200] + ("..." if len(c_text) > 200 else ""),
                    similarity=round(sim, 3),
                )
            )

        # Detect numerical differences
        prev_nums = cls.extract_numbers(previous_text)
        curr_nums = cls.extract_numbers(current_text)

        numerical_changes: List[NumericalChange] = []
        # Find new or changed figures in current
        prev_num_set = {n["number"] for n in prev_nums}
        for c in curr_nums:
            if c["number"] not in prev_num_set:
                numerical_changes.append(
                    NumericalChange(
                        context=c["context"][:150],
                        previous_value=None,
                        current_value=c["number"],
                        change_type="NEW_OR_CHANGED",
                    )
                )

        # Detect guidance statements
        guidance_shifts: List[Dict[str, str]] = []
        curr_lines = [line.strip() for line in current_text.split("\n") if line.strip()]
        for line in curr_lines:
            if any(k in line.lower() for k in cls.GUIDANCE_KEYWORDS):
                guidance_shifts.append({
                    "statement": line[:200],
                    "signal": "CURRENT_OUTLOOK",
                })

        summary = (
            f"Filing Comparison: {len(added)} sections added, {len(removed)} removed, "
            f"{len([m for m in modified_diffs if m.status == 'MODIFIED'])} modified. "
            f"Overall text similarity: {round(overall_sim * 100, 1)}%."
        )

        return DocumentDiffResult(
            previous_doc_id=previous_doc_id,
            current_doc_id=current_doc_id,
            similarity_score=round(overall_sim, 4),
            sections_added=added,
            sections_removed=removed,
            sections_modified=modified_diffs,
            numerical_changes=numerical_changes[:20],  # cap to top 20
            guidance_shifts=guidance_shifts[:10],
            summary=summary,
        )
