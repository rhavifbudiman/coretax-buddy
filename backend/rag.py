import os
import re
from pathlib import Path


def load_knowledge_base(kb_dir: str) -> list[dict]:
    """Load all .md files from kb_dir, split into chunks by ## headings."""
    chunks = []
    kb_path = Path(kb_dir)

    for md_file in sorted(kb_path.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        file_chunks = _split_into_chunks(text, md_file.name)
        chunks.extend(file_chunks)

    return chunks


def _split_into_chunks(text: str, source_name: str) -> list[dict]:
    """Split markdown text into chunks at ## headings."""
    chunks = []
    lines = text.splitlines()

    current_heading = "Intro"
    current_lines = []

    for line in lines:
        if line.startswith("## "):
            # Save previous chunk if it has content
            if current_lines:
                body = "\n".join(current_lines).strip()
                if body:
                    chunks.append({
                        "source": source_name,
                        "heading": current_heading,
                        "text": body,
                    })
            current_heading = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)

    # Save last chunk
    if current_lines:
        body = "\n".join(current_lines).strip()
        if body:
            chunks.append({
                "source": source_name,
                "heading": current_heading,
                "text": body,
            })

    return chunks


def _tokenize(text: str) -> list[str]:
    """Lowercase and split on non-alphanumeric chars (works for ID and EN)."""
    return re.findall(r"[a-z0-9]+", text.lower())


def retrieve(query: str, chunks: list[dict], top_k: int = 3) -> list[dict]:
    """Return top_k chunks most relevant to query using token overlap scoring."""
    query_tokens = set(_tokenize(query))
    if not query_tokens:
        return chunks[:top_k]

    scored = []
    for chunk in chunks:
        chunk_tokens = set(_tokenize(chunk["text"] + " " + chunk["heading"]))
        overlap = len(query_tokens & chunk_tokens)
        score = overlap / len(query_tokens)
        scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [chunk for _, chunk in scored[:top_k]]


def build_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into a context string for the LLM prompt."""
    if not chunks:
        return "(No relevant context found.)"

    parts = []
    for chunk in chunks:
        parts.append(
            f"[Source: {chunk['source']} | {chunk['heading']}]\n{chunk['text']}"
        )
    return "\n\n---\n\n".join(parts)
