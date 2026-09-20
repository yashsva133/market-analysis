"""Pydantic schemas for documents and pages."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class DocumentPageRead(BaseModel):
    id: UUID
    page_number: int
    text: str
    image_path: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentBase(BaseModel):
    source_item_id: UUID
    mime_type: str
    sha256: str
    page_count: int = 1
    text_quality: float = 1.0
    storage_path: str


class DocumentCreate(DocumentBase):
    pass


class DocumentRead(DocumentBase):
    id: UUID
    extracted_at: datetime
    pages: List[DocumentPageRead] = []

    model_config = ConfigDict(from_attributes=True)
