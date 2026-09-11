import re


def sentences(text: str) -> list[str]:
    """English boundary heuristic shared by extraction and the exact verifier.

    Soft PDF line wraps are whitespace, not sentence boundaries. Protect common
    abbreviations and initials; this is deliberately not a full language parser.
    """
    parts: list[str] = []
    start = 0
    for match in re.finditer(r"[.!?](?:\s+|$)", text):
        prefix = text[start:match.start() + 1]
        if re.search(r"\b(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|vs|etc|e\.g|i\.e)\.$|\b[A-Z]\.$", prefix):
            continue
        value = text[start:match.start() + 1].strip()
        if value:
            parts.append(value)
        start = match.end()
    if text[start:].strip():
        parts.append(text[start:].strip())
    return parts


def chunk_page(text: str, max_chars: int = 1000, overlap_chars: int = 150) -> list[str]:
    """Lossless page-local windows, preferring sentence then word boundaries.

    Windows overlap for context. Very long sentences/tokens use a hard bound;
    snippets remain verbatim substrings of the extracted page text.
    """
    if max_chars < 1 or not 0 <= overlap_chars < max_chars:
        raise ValueError("Invalid chunk window configuration.")
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            region = text[start:end]
            boundaries = [match.end() for match in re.finditer(r"[.!?]\s+", region)]
            minimum = max(overlap_chars + 1, max_chars // 2)
            suitable = [boundary for boundary in boundaries if boundary >= minimum]
            if suitable:
                end = start + suitable[-1]
            else:
                boundary = region.rfind(" ")
                if boundary >= minimum:
                    end = start + boundary
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        next_start = max(start + 1, end - overlap_chars)
        # Prefer an overlap starting at a whole sentence, then a whole word.
        sentence_starts = [match.end() for match in re.finditer(r"[.!?]\s+", text[next_start:end])]
        if sentence_starts and next_start + sentence_starts[0] < end:
            next_start += sentence_starts[0]
        else:
            while next_start < end and next_start > 0 and not text[next_start - 1].isspace():
                next_start += 1
        start = next_start
    return chunks
