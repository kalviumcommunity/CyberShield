import re
from typing import List


def clean_text(text: str) -> str:
    """
    Cleans and normalizes extracted text while preserving security terms,
    technical identifiers, IPs, hashes, CVEs, and paragraph boundaries.
    """
    if not text:
        return ""

    # 1. Normalize line breaks (\r\n -> \n, \r -> \n)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 2. Convert tabs and special whitespace to single spaces
    text = re.sub(r"[\t\f\v]", " ", text)

    # 3. Collapse multiple inline spaces into a single space
    lines = []
    for line in text.split("\n"):
        cleaned_line = re.sub(r"[ ]+", " ", line).strip()
        lines.append(cleaned_line)

    # 4. Join lines and limit consecutive newlines to maximum 2 (preserving paragraphs)
    rejoined = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", rejoined).strip()

    return cleaned


def chunk_text(
    text: str,
    target_chunk_size: int = 600,
    chunk_overlap: int = 60
) -> List[str]:
    """
    Splits text into chunks of approximately target_chunk_size words (500-800 words)
    with chunk_overlap words overlapping between consecutive chunks.
    
    Guarantees chunk order preservation and returns a list of chunk strings.
    """
    cleaned = clean_text(text)
    if not cleaned:
        return []

    words = cleaned.split()
    total_words = len(words)

    # If the document is within target size, return single chunk
    if total_words <= target_chunk_size:
        return [cleaned]

    chunks: List[str] = []
    start = 0
    step = target_chunk_size - chunk_overlap
    if step <= 0:
        step = target_chunk_size // 2 or 1

    while start < total_words:
        end = min(start + target_chunk_size, total_words)
        chunk_words = words[start:end]
        chunk_str = " ".join(chunk_words).strip()

        if chunk_str:
            chunks.append(chunk_str)

        if end >= total_words:
            break

        start += step

    return chunks
