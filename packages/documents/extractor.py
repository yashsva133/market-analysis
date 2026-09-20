"""Document extraction, page segmentation, and text quality scoring."""
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from packages.common.logging import get_logger

logger = get_logger(__name__)


class DocumentExtractor:
    """Extracts text and page structure from PDF, HTML, and plain text filings."""

    def compute_sha256(self, file_bytes: bytes) -> str:
        return hashlib.sha256(file_bytes).hexdigest()

    def extract_pages_from_pdf(self, pdf_bytes: bytes) -> List[Tuple[int, str, float]]:
        """Extract pages: returns list of (page_number, page_text, quality_score)."""
        pages = []
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text") or ""
                # Quality score: ratio of non-whitespace characters
                char_count = len(text.strip())
                quality = min(1.0, char_count / 100.0) if char_count > 0 else 0.0
                pages.append((page_num + 1, text, quality))
            doc.close()
        except ImportError:
            logger.warning("PyMuPDF (fitz) not installed. Storing raw string fallback.")
            raw_text = pdf_bytes.decode("latin1", errors="ignore")
            pages.append((1, raw_text[:5000], 0.5))
        except Exception as e:
            logger.error(f"Error parsing PDF: {e}")
            pages.append((1, "Failed to parse PDF contents", 0.0))

        return pages

    def extract_text_from_html(self, html_bytes: bytes) -> Tuple[str, float]:
        """Extract plain text from HTML filing."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_bytes, "html.parser")
            # Remove scripts and styles
            for elem in soup(["script", "style", "head", "title", "meta"]):
                elem.extract()
            text = soup.get_text(separator="\n")
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            clean_text = "\n".join(lines)
            quality = 1.0 if len(clean_text) > 100 else 0.5
            return clean_text, quality
        except Exception as e:
            logger.warning(f"Error extracting HTML via BeautifulSoup: {e}")
            raw = html_bytes.decode("utf-8", errors="ignore")
            return raw, 0.5


    def extract_pages_from_text(self, text: str) -> List[Tuple[int, str, float]]:
        """Wraps raw text in a single page structure with quality evaluation."""
        clean = text.strip()
        quality = min(1.0, len(clean) / 100.0) if clean else 0.0
        return [(1, clean, quality)]

    def extract_document(self, content_bytes: bytes, mime_type: str = "text/plain") -> Dict:
        """Unified document extraction returning sha256, page count, and segmented pages."""
        sha256 = self.compute_sha256(content_bytes)
        if "pdf" in mime_type.lower():
            pages = self.extract_pages_from_pdf(content_bytes)
        elif "html" in mime_type.lower():
            text, quality = self.extract_text_from_html(content_bytes)
            pages = [(1, text, quality)]
        else:
            text = content_bytes.decode("utf-8", errors="ignore")
            pages = self.extract_pages_from_text(text)

        total_quality = sum(p[2] for p in pages) / max(1, len(pages))
        return {
            "sha256": sha256,
            "mime_type": mime_type,
            "page_count": len(pages),
            "text_quality": round(total_quality, 2),
            "pages": [{"page_number": p[0], "text": p[1], "quality": p[2]} for p in pages],
            "page_tuples": pages,
        }


document_extractor = DocumentExtractor()


def extract_document(raw_bytes: bytes, content_type: str = "text/plain", filename: str = "") -> Dict:
    """Convenience module function for extracting document text and page metadata."""
    return document_extractor.extract_document(raw_bytes, mime_type=content_type)

