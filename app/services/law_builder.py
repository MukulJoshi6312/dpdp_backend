"""Law id derivation and draft -> Law conversion — ports src/lib/lawBuilder.ts."""
from __future__ import annotations

import re
from datetime import date
from typing import List, Set

from app.schemas.law import Law, LawCreate, Penalty, Provision


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return re.sub(r"^-+|-+$", "", value)


def derive_law_id(title: str, year: int, existing_ids: Set[str]) -> str:
    """Derive a unique law id from title + year (e.g. 'dpdp-act-2023')."""
    base = slugify(title) or "law"
    with_year = f"{base}-{year}" if year else base
    law_id = with_year
    n = 2
    while law_id in existing_ids:
        law_id = f"{with_year}-{n}"
        n += 1
    return law_id


def build_law(draft: LawCreate, existing_ids: Set[str]) -> Law:
    """Convert a validated draft into a fully-formed Law record."""
    law_id = derive_law_id(draft.title, draft.year, existing_ids)

    provisions: List[Provision] = [
        Provision(
            num=p.num.strip(),
            title=p.title.strip(),
            text=p.text.strip(),
            rules=[r.strip() for r in p.rules if r.strip()],
        )
        for p in draft.provisions
        if p.num.strip() or p.title.strip()
    ]

    penalties: List[Penalty] = [
        Penalty(
            breach=p.breach.strip(),
            max=p.max or 0,
            unit=(p.unit.strip() or "crore"),
        )
        for p in draft.penalties
        if p.breach.strip()
    ]

    return Law(
        id=law_id,
        title=draft.title.strip(),
        year=draft.year,
        category=draft.category.strip(),
        icon=draft.icon,
        authority=draft.authority.strip(),
        status=draft.status.strip() or "In force",
        shortDesc=draft.shortDesc.strip(),
        sections=draft.sections,
        lastUpdated=draft.lastUpdated.strip() or date.today().isoformat(),
        formats=draft.formats,
        apiSlug=law_id,
        provisions=provisions,
        penalties=penalties,
    )
