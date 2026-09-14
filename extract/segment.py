"""Split a job description into responsibility / requirement / nice-to-have sections by header lines."""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel

HEADERS = {
    "responsibilities": [
        r"what you('|’)ll (do|be doing|work on|own|deliver)", r"what you will (do|be doing|own|work on)",
        r"responsibilities", r"the role", r"about the role", r"in this role", r"you will",
        r"day[- ]to[- ]day", r"key duties", r"duties",
        r"how you('|’)ll (contribute|make an impact)", r"the impact you (will have|('|’)ll have)",
        r"in this role,? you( will|('|’)ll)?", r"key responsibilities", r"main responsibilities",
        r"core responsibilities", r"your (responsibilities|role|mission|impact)",
        r"what you('|’)ll accomplish", r"a day in the life", r"what the job involves",
    ],
    "requirements": [
        r"what we('|’)re looking for", r"what we are looking for", r"requirements", r"qualifications",
        r"minimum qualifications", r"basic qualifications", r"required (skills|experience|qualifications)",
        r"you (have|bring|are)", r"about you", r"who you are", r"what you('|’)ll bring", r"what you bring",
        r"must[- ]haves?", r"skills (and|&) experience", r"experience", r"what we (require|value|need)",
        r"you might be a fit if", r"you('|’)re a fit if", r"ideal candidate", r"what we look for",
        r"you (might|may|could|would) be a (good |great |strong |perfect )?fit( for this role)? if( you)?( have)?",
        r"you may be a good fit if you", r"what you('|’)ll need", r"what you need",
        r"what you('|’)ll bring( to the (team|role))?", r"your (background|profile|experience|skills)",
        r"minimum requirements", r"basic requirements", r"required skills( and experience)?",
        r"must[- ]have (skills|qualifications)", r"the ideal candidate( will have)?", r"you should have",
        r"you('|’)ll (need|have)", r"we('|’)re looking for( someone who)?", r"we are looking for( someone who)?",
        r"experience (and|&) skills", r"technical (skills|requirements)",
        # observed in the collected corpus (task-13 audit): real header phrasings not covered above
        r"what you should have", r"ideally,? you('|’)?d? have", r"qualifications we value",
        r"desirable skills(,? knowledge,? and experience)?",
    ],
    "nice_to_have": [
        r"nice[- ]to[- ]haves?", r"bonus( points| skills| experience)?",
        r"preferred( qualifications| skills| experience| requirements)?",
        r"plus(es)?", r"it('|’)s a plus", r"extra credit", r"great if you", r"additional qualifications",
        r"even better( if)?", r"strong candidates (may|will|might)( also)? have",
        r"(it('|’)s a |it is a )?(big |huge )?plus if", r"we('|’)d love (it )?if( you)?",
        r"ideally,? you", r"you may also have", r"what would set you apart",
        r"stand[- ]out (skills|qualifications)",
    ],
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


def audit(postings) -> dict:
    """Corpus-level segmentation audit: for each posting, run segment() and tally quality plus,
    among "header"-quality postings, whether a requirements section was actually found. Used to
    check header-pattern coverage against the real posting corpus."""
    n = header = inferred = header_with_requirements = header_without_requirements = 0
    for p in postings:
        n += 1
        s = segment(p.full_text)
        if s.quality == "header":
            header += 1
            if s.requirements.strip():
                header_with_requirements += 1
            else:
                header_without_requirements += 1
        else:
            inferred += 1
    return {
        "n": n,
        "header": header,
        "inferred": inferred,
        "header_with_requirements": header_with_requirements,
        "header_without_requirements": header_without_requirements,
    }
