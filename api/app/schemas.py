from typing import Literal

from pydantic import BaseModel, Field

PageKind = Literal["digital", "scanned", "blank", "broken_text_layer"]
JobStatus = Literal["queued", "parsing", "embedding", "ready", "failed"]


class Chunk(BaseModel):
    """One retrievable unit: a leaf section, or a slice of an oversized one."""

    text: str
    heading_path: list[str] = Field(default_factory=list)
    page: int | None = None
    char_start: int = 0
    char_end: int = 0
    is_ocr: bool = False

    def embedding_text(self) -> str:
        """Heading path is prepended so short leaf sections stay findable.

        A section titled "4.2 Cuti Tahunan" whose body never repeats the word
        "cuti" is unreachable by dense search without this.
        """
        if not self.heading_path:
            return self.text
        return " > ".join(self.heading_path) + "\n\n" + self.text


class ParsedDocument(BaseModel):
    chunks: list[Chunk] = Field(default_factory=list)
    pages_total: int = 0
    pages_digital: int = 0
    pages_scanned: int = 0
    pages_blank: int = 0
    pages_broken: int = 0
    pages_ocr_done: int = 0
    pages_ocr_pending: int = 0

    def skipped_note(self) -> str | None:
        """Human-facing explanation for pages that produced no chunks."""
        unread = self.pages_scanned + self.pages_broken - self.pages_ocr_done
        if unread <= 0:
            return None
        return (
            f"{unread} dari {self.pages_total} halaman tampaknya hasil scan "
            "dan dilewati. Dukungan OCR menyusul."
        )


class DocumentSummary(BaseModel):
    doc_id: str
    doc_name: str
    status: JobStatus
    chunks: int = 0
    pages_total: int = 0
    pages_indexed: int = 0
    pages_skipped: int = 0
    note: str | None = None
    error: str | None = None


class UploadAccepted(BaseModel):
    doc_id: str
    doc_name: str
    status: JobStatus
    duplicate_of: str | None = None


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list["ChatTurn"] = Field(default_factory=list, max_length=20)
    # UI language. The model still mirrors the language of the question; this
    # only decides the language of replies the server writes itself.
    lang: Literal["ID", "EN"] = "ID"


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=8000)


class RetrievedChunk(BaseModel):
    """Sent to the client before generation so the trace panel fills immediately."""

    ref: int
    doc_name: str
    heading_path: list[str]
    page: int | None
    text: str
    dense_score: float | None = None
    sparse_score: float | None = None
    fusion_score: float | None = None
    rerank_score: float | None = None
    is_ocr: bool = False


class Citation(BaseModel):
    ref: int
    doc_name: str
    heading_path: list[str]
    page: int | None
    quote: str
    is_ocr: bool = False


ChatRequest.model_rebuild()
