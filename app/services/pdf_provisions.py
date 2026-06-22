"""Parse the PROGA Act PDF into structured provisions (sections).

Used as a one-off to seed the law's `provisions` from PROGA.pdf so the act
page can render the Act's sections (and a slide-in detail sheet) instead of a
hand-written accordion. Pure stdlib + pypdf.
"""
from __future__ import annotations

import re
from typing import List

from pypdf import PdfReader

CHAPTERS = {
    1: "Chapter I — Preliminary",
    2: "Chapter I — Preliminary",
    3: "Chapter II — Development and Recognition",
    4: "Chapter II — Development and Recognition",
    5: "Chapter III — Prohibition",
    6: "Chapter III — Prohibition",
    7: "Chapter III — Prohibition",
    8: "Chapter IV — Authority on Online Gaming",
    9: "Chapter V — Offences and Penalties",
    10: "Chapter V — Offences and Penalties",
    11: "Chapter V — Offences and Penalties",
    12: "Chapter V — Offences and Penalties",
    13: "Chapter VI — Miscellaneous",
    14: "Chapter VI — Miscellaneous",
    15: "Chapter VI — Miscellaneous",
    16: "Chapter VI — Miscellaneous",
    17: "Chapter VI — Miscellaneous",
    18: "Chapter VI — Miscellaneous",
    19: "Chapter VI — Miscellaneous",
    20: "Chapter VI — Miscellaneous",
}

_SECTION = re.compile(r"(?m)^(\d{1,2})\.\s+([^.\n]+?)\.\s*[—\-]")


def _tidy(s: str) -> str:
    """Fix PDF artefacts: hyphenated breaks, doubled spaces, stray newlines."""
    # Collapse spaces around a hyphen between word chars: "e -sport" / "e- sport"
    # / "e - sport" all become "e-sport".
    s = re.sub(r"(\w)\s*-\s*(\w)", r"\1-\2", s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{2,}", "\n", s)
    return s.strip()


def parse_proga_provisions(pdf_path: str) -> List[dict]:
    """Return a list of provision dicts: {num, title, text, rules}."""
    reader = PdfReader(pdf_path)
    full = "\n".join((p.extract_text() or "") for p in reader.pages)

    # Strip page headers + blank lines.
    lines = [
        ln.strip()
        for ln in full.splitlines()
        if ln.strip() and not re.match(r"^Page \d+ of \d+$", ln.strip())
    ]
    text = "\n".join(lines)

    # Body begins after the enacting formula.
    m = re.search(r"as\s+follows", text)
    body = text[m.end():] if m else text

    matches = list(_SECTION.finditer(body))
    provisions: List[dict] = []
    for i, mm in enumerate(matches):
        num = int(mm.group(1))
        title = _tidy(mm.group(2))
        start, end = mm.end(), (matches[i + 1].start() if i + 1 < len(matches) else len(body))
        text_body = _tidy(body[start:end])
        # Trim footnote tails that leaked into the chunk.
        text_body = re.split(r"\n\d+ Vide ", text_body)[0].strip()
        chapter = CHAPTERS.get(num, "")
        provisions.append(
            {
                "num": f"S. {num}",
                "title": title,
                "text": (f"{chapter}\n\n{text_body}" if chapter else text_body),
                "rules": [],
            }
        )
    return provisions
