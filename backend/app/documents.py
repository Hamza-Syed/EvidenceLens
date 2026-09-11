from threading import Lock
from uuid import UUID, uuid4

import pymupdf

from .models import ChunkedPassage, Document, Passage
from .text import chunk_page, sentences


class DocumentError(ValueError):
    pass


def extract_pdf(name: str, content: bytes, *, max_chars: int = 1000,
                overlap_chars: int = 150) -> tuple[Document, list[Passage]]:
    document_id = uuid4()
    try:
        with pymupdf.open(stream=content, filetype="pdf") as pdf:
            if pdf.needs_pass:
                raise DocumentError("Encrypted PDFs are not supported.")
            if not 1 <= len(pdf) <= 200:
                raise DocumentError("PDF must have between 1 and 200 pages.")
            passages = []
            total_characters = 0
            for page_number, page in enumerate(pdf, start=1):
                text = page.get_text("text", sort=True).strip()
                total_characters += len(text)
                if total_characters > 2_000_000:
                    raise DocumentError("PDF exceeds the extracted text limit.")
                page_sentences = sentences(text)
                for chunk in chunk_page(text, max_chars, overlap_chars):
                    passages.append(ChunkedPassage(
                        document_id=document_id, document_name=name, page_number=page_number,
                        text=chunk, complete_sentences=tuple(sentence for sentence in page_sentences if sentence in chunk),
                    ))
            if not passages:
                raise DocumentError("PDF has no extractable text. OCR is not available.")
            return Document(id=document_id, name=name, page_count=len(pdf),
                            passage_count=len(passages)), passages
    except DocumentError:
        raise
    except (RuntimeError, ValueError) as exc:
        raise DocumentError("Unable to read this PDF.") from exc


class DocumentStore:
    def __init__(self) -> None:
        self._items: dict[UUID, tuple[Document, list[Passage]]] = {}
        self._lock = Lock()

    def add_batch(self, items: list[tuple[Document, list[Passage]]]) -> None:
        with self._lock:
            if len(self._items) + len(items) > 100:
                raise DocumentError("Workspace capacity reached. Restart the backend to clear documents.")
            self._items.update({document.id: (document, passages) for document, passages in items})

    def passages(self, ids: list[UUID]) -> list[Passage]:
        with self._lock:
            return [passage for document_id in dict.fromkeys(ids)
                    for passage in self._items[document_id][1]]
