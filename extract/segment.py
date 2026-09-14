"""Split a job description into responsibility / requirement / nice-to-have sections by header lines."""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel

HEADERS = {
    "responsibilities": [r"what you('|’)ll (do|be doing|work on)", r"what you will (do|be doing)", r"responsibilities", r"the role", r"your role", r"about the role", r"in this role", r"you will", r"what you('|’)ll own", r"day[- ]to[- ]day", r"key duties", r"duties", r"what you('|’)ll be doing", r"how you('|’)ll (contribute|make an impact)", r"the impact you (will have|('|’)ll have)", r"in this role,? you will", r"key responsibilities", r"main responsibilities"],
    "requirements": [r"what we('|’)re looking for", r"what we are looking for", r"requirements", r"qualifications", r"minimum qualifications", r"basic qualifications", r"required (skills|experience|qualifications)", r"you (have|bring|are)", r"about you", r"who you are", r"what you('|’)ll bring", r"what you bring", r"must[- ]haves?", r"skills (and|&) experience", r"experience", r"what we (require|value|need)", r"you might be a fit if", r"you('|’)re a fit if", r"ideal candidate", r"what we look for"],
    "nice_to_have": [r"nice[- ]to[- ]haves?", r"bonus( points)?", r"preferred( qualifications| skills| experience)?", r"plus(es)?", r"it('|’)s a plus", r"extra credit", r"great if you", r"additional qualifications", r"even better if"],
    "other": [r"about (us|the (company|team))", r"benefits", r"perks", r"compensation", r"salary", r"what we offer", r"why join", r"our (mission|values)", r"equal opportunity", r"how to apply", r"interview process", r"location", r"the team"],
}
_HEADER_RES = [(sec, re.compile(rf"^\W*(?:{p})\W*$", re.I)) for sec, pats in HEADERS.items() for p in pats]


class Segments(BaseModel):
    responsibilities: str = ""
    requirements: str = ""
    nice_to_have: str = ""
    other: str = ""
    quality: Literal["header", "inferred"] = "inferred"


def _classify(line: str) -> str | None:
    if len(line) > 60:
        return None
    for sec, r in _HEADER_RES:
        if r.match(line):
            return sec
    return None


def segment(text: str) -> Segments:
    buckets = {"responsibilities": [], "requirements": [], "nice_to_have": [], "other": []}
    current, hit = "other", False
    for line in text.splitlines():
        sec = _classify(line.strip())
        if sec:
            current = sec
            hit = hit or sec != "other"
            continue
        buckets[current].append(line)
    out = {k: "\n".join(v).strip() for k, v in buckets.items()}
    quality = "header" if hit and (out["responsibilities"] or out["requirements"]) else "inferred"
    if quality == "inferred":  # nothing reliable: put everything in other
        out = {"responsibilities": "", "requirements": "", "nice_to_have": "", "other": text.strip()}
    return Segments(**out, quality=quality)
