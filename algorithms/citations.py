"""
citations.py
------------
Builds APA, IEEE and BibTeX citations from the cleaned paper records.

Honesty rule: authorship.csv only lists VJTI faculty (external co-authors are left out
of the data on purpose). So the author list in a citation is "VJTI faculty authors only".
Nothing is invented: a blank year becomes "n.d.", blank venue / DOI are simply left out,
and a paper with no linked faculty gets a citation that starts with the title.
"""
import re

TITLES = {"dr", "prof", "mr", "mrs", "ms", "shri", "smt", "er", "engr"}
CONFERENCE_WORDS = ("conference", "proceedings", "symposium", "workshop", "conf.", "iccc", "icc ")


def split_name(full_name):
    """'Dr. Deepak S. Gavali' -> (['Deepak', 'S.'], 'Gavali'). Titles are dropped.
    Returns None when there is no usable name."""
    parts = [p for p in re.split(r"\s+", (full_name or "").strip()) if p]
    while parts and parts[0].strip(".").lower() in TITLES:
        parts.pop(0)
    if not parts or " ".join(parts).lower() == "name not listed":
        return None
    return parts[:-1], parts[-1]


def initials(given_names):
    out = []
    for g in given_names:
        letters = g.strip(".")
        if letters:
            out.append(letters[0].upper() + ".")
    return " ".join(out)


def _authors(paper):
    names = []
    for a in paper.get("authors", []):
        parsed = split_name(a.get("name", ""))
        if parsed:
            names.append(parsed)
    return names


def _doi_text(paper):
    return paper["doi_link"] or ""


def _year(paper):
    return str(paper["year_num"]) if paper.get("year_num") else ""


def apa(paper):
    names = _authors(paper)
    people = []
    for given, last in names:
        ini = initials(given)
        people.append(f"{last}, {ini}" if ini else last)
    if len(people) == 0:
        lead = ""
    elif len(people) == 1:
        lead = people[0]
    else:
        lead = ", ".join(people[:-1]) + ", & " + people[-1]
    year = _year(paper) or "n.d."
    title = paper["title"].rstrip(".")
    if lead:
        text = f"{lead} ({year}). {title}."
    else:                                   # APA puts the title first when there is no author
        text = f"{title}. ({year})."
    if paper.get("venue"):
        text += f" {paper['venue']}."
    if _doi_text(paper):
        text += f" {_doi_text(paper)}"
    return text.strip()


def ieee(paper):
    names = _authors(paper)
    people = []
    for given, last in names:
        ini = initials(given)
        people.append(f"{ini} {last}" if ini else last)
    if len(people) <= 2:
        lead = " and ".join(people)
    else:
        lead = ", ".join(people[:-1]) + ", and " + people[-1]
    title = paper["title"].rstrip(".")
    tail = []
    if paper.get("venue"):
        tail.append(paper["venue"])
    if _year(paper):
        tail.append(_year(paper))
    if paper.get("doi"):
        tail.append("doi: " + paper["doi"])
    text = (lead + ", " if lead else "") + f"\u201c{title},\u201d"
    if tail:
        return text + " " + ", ".join(tail) + "."
    return (lead + ", " if lead else "") + f"\u201c{title}.\u201d"


def bibtex_escape(value):
    for ch in "&%$#_":
        value = value.replace(ch, "\\" + ch)
    return value


def bibtex_key(paper):
    names = _authors(paper)
    base = re.sub(r"[^a-z0-9]", "", names[0][1].lower()) if names else ""
    first_word = ""
    for word in re.findall(r"[A-Za-z0-9]+", paper["title"]):
        if len(word) > 3:
            first_word = word.lower()
            break
    key = f"{base}{_year(paper)}{first_word}"
    return key or re.sub(r"[^A-Za-z0-9]", "", paper["paper_id"]) or "paper"


def bibtex(paper):
    venue = paper.get("venue", "")
    is_conf = any(w in venue.lower() for w in CONFERENCE_WORDS)
    if not venue:
        entry, venue_field = "misc", None
    elif is_conf:
        entry, venue_field = "inproceedings", "booktitle"
    else:
        entry, venue_field = "article", "journal"
    fields = []
    names = _authors(paper)
    if names:
        fields.append(("author", " and ".join(
            f"{last}, {' '.join(given)}".strip().rstrip(",") for given, last in names)))
    fields.append(("title", "{" + paper["title"] + "}"))
    if venue_field:
        fields.append((venue_field, venue))
    if _year(paper):
        fields.append(("year", _year(paper)))
    if paper.get("doi"):
        fields.append(("doi", paper["doi"]))
    lines = [f"@{entry}{{{bibtex_key(paper)},"]
    for name, value in fields:
        if name == "title":
            value = "{" + bibtex_escape(paper["title"]) + "}"
        elif name != "doi":
            value = bibtex_escape(value)
        lines.append(f"  {name} = {{{value}}},")
    lines.append("}")
    return "\n".join(lines)


def citations_for(paper):
    return {
        "apa": apa(paper),
        "ieee": ieee(paper),
        "bibtex": bibtex(paper),
        "has_authors": bool(_authors(paper)),
    }
