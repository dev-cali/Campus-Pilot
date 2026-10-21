"""Split already-extracted page text without database or AI service calls."""

import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class DocumentChunk:
    """One passage and the information needed to trace it to its source.

    Offsets refer to normalized text: text[start_char:end_char].
    chunk_index is zero-based and starts again for each processing call.
    This is a plain Python result, not the database's DocumentChunk model.
    """

    document_id: int
    page_no: int
    source_reference: str
    title: str
    version: Optional[str]
    chunk_index: int
    chunk_text: str
    start_char: int
    end_char: int


def normalize_document_text(text: str) -> str:
    """Collapse whitespace within paragraphs; keep blank-line boundaries.

    Single line breaks become spaces. One or more blank lines become two
    newlines. Words, punctuation, and Unicode characters remain unchanged.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string of already-extracted text")

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = re.split(r"\n\s*\n", text)
    cleaned = [" ".join(paragraph.split()) for paragraph in paragraphs]
    return "\n\n".join(paragraph for paragraph in cleaned if paragraph)


def split_document_text(
    text: str,
    *,
    document_id: int,
    page_no: int,
    source_reference: str,
    title: str,
    version: Optional[str] = None,
    max_chars: int = 1000,
) -> List[DocumentChunk]:
    """Return ordered chunks for ONE page, retaining source metadata.

    IDs, page numbers, and max_chars must be positive integers (not bools).
    Required text metadata must be nonblank strings. version may be None
    or a nonblank string. Metadata values are copied exactly, not cleaned.
    Empty text returns an empty list after all inputs have been validated.

    Prefer paragraph boundaries, then whitespace, then a hard character cut
    for an oversized word. Boundary whitespace is omitted from chunk edges;
    offsets show where each chunk belongs in normalize_document_text(text).
    The character limit counts Python Unicode code points, not model tokens.
    """
    normalized = normalize_document_text(text)

    for name, value in (
        ("document_id", document_id), ("page_no", page_no),
        ("max_chars", max_chars),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} must be an integer")
        if value <= 0:
            raise ValueError(f"{name} must be greater than zero")

    for name, value in (("source_reference", source_reference), ("title", title)):
        if not isinstance(value, str):
            raise TypeError(f"{name} must be a string")
        if not value.strip():
            raise ValueError(f"{name} must not be blank")
    if version is not None:
        if not isinstance(version, str):
            raise TypeError("version must be a string or None")
        if not version.strip():
            raise ValueError("version must not be blank")

    chunks = []
    start = 0
    while start < len(normalized):
        # Skip only whitespace separating chunks, never letters or punctuation.
        while start < len(normalized) and normalized[start].isspace():
            start += 1
        if start == len(normalized):
            break

        end = min(start + max_chars, len(normalized))
        if end < len(normalized):
            # If the next character is whitespace, the whole window fits.
            # Otherwise find a boundary inside the window before cutting a word.
            window = normalized[start:end]
            paragraph_end = window.rfind("\n\n")
            if paragraph_end > 0:
                end = start + paragraph_end
            elif not normalized[end].isspace():
                boundaries = list(re.finditer(r"\s+", window))
                if boundaries:
                    end = start + boundaries[-1].start()

        # No leading or trailing whitespace in a returned passage.
        while end > start and normalized[end - 1].isspace():
            end -= 1

        chunks.append(DocumentChunk(
            document_id=document_id,
            page_no=page_no,
            source_reference=source_reference,
            title=title,
            version=version,
            chunk_index=len(chunks),
            chunk_text=normalized[start:end],
            start_char=start,
            end_char=end,
        ))
        start = end

    return chunks
