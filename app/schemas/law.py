"""Schemas for laws — mirrors src/types/law.ts (Law, Provision, Penalty)."""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

LawFormat = Literal["PDF", "XML", "API"]


class Provision(BaseModel):
    num: str
    title: str
    text: str = ""
    rules: List[str] = Field(default_factory=list)


class Penalty(BaseModel):
    breach: str
    max: float
    unit: str = "crore"


class Law(BaseModel):
    id: str
    title: str
    year: int
    category: str
    icon: str = "scale"
    authority: str
    status: str = "In force"
    shortDesc: str
    sections: int
    lastUpdated: str
    formats: List[LawFormat] = Field(default_factory=lambda: ["PDF", "XML", "API"])
    apiSlug: str
    provisions: List[Provision] = Field(default_factory=list)
    penalties: List[Penalty] = Field(default_factory=list)


class LawCreate(BaseModel):
    """Payload for the admin 'Add Law' form (ports lawBuilder.LawDraft).

    `id`/`apiSlug` are derived server-side from title + year.
    """
    title: str
    year: int
    category: str
    icon: str = "scale"
    authority: str
    status: str = "In force"
    shortDesc: str
    sections: int
    lastUpdated: str = ""
    formats: List[LawFormat] = Field(default_factory=lambda: ["PDF", "XML", "API"])
    provisions: List[Provision] = Field(default_factory=list)
    penalties: List[Penalty] = Field(default_factory=list)


class LawUpdate(BaseModel):
    title: Optional[str] = None
    year: Optional[int] = None
    category: Optional[str] = None
    icon: Optional[str] = None
    authority: Optional[str] = None
    status: Optional[str] = None
    shortDesc: Optional[str] = None
    sections: Optional[int] = None
    lastUpdated: Optional[str] = None
    formats: Optional[List[LawFormat]] = None
    provisions: Optional[List[Provision]] = None
    penalties: Optional[List[Penalty]] = None
