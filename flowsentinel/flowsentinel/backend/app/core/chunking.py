"""Heading-aware chunking for Markdown / plain-text runbooks."""
from __future__ import annotations

import re
from dataclasses import dataclass

_HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


@dataclass
class TextChunk:
    heading: str
    text: str


def _split_long(text: str, max_chars: int, overlap: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    paras = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    out: list[str] = []
    cur = ""
    for p in paras:
        if cur and len(cur) + len(p) + 2 > max_chars:
            out.append(cur.strip())
            tail = cur[-overlap:] if overlap else ""
            cur = (tail + "\n\n" + p) if tail else p
        else:
            cur = f"{cur}\n\n{p}" if cur else p
        while len(cur) > max_chars * 1.5:  # a single enormous paragraph
            out.append(cur[:max_chars].strip())
            cur = cur[max_chars - overlap:]
    if cur.strip():
        out.append(cur.strip())
    return out


def chunk_markdown(content: str, max_chars: int = 900, overlap: int = 120) -> list[TextChunk]:
    sections: list[tuple[str, list[str]]] = []
    path: list[str] = []
    current: list[str] = []
    heading = ""

    def flush():
        if any(line.strip() for line in current):
            sections.append((heading, current[:]))
        current.clear()

    for line in content.splitlines():
        m = _HEADING.match(line)
        if m:
            flush()
            level = len(m.group(1))
            path[:] = path[: level - 1] + [m.group(2)]
            heading = " > ".join(path)
        else:
            current.append(line)
    flush()

    chunks: list[TextChunk] = []
    for head, lines in sections:
        body = "\n".join(lines).strip()
        for piece in _split_long(body, max_chars, overlap):
            chunks.append(TextChunk(heading=head, text=piece))
    return chunks
