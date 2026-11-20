"""
faculty_filters.py
------------------
Search, filter and sort the faculty directory.

A faculty member "has" a keyword if it is in their listed expertise OR in the keywords of
their own papers (the same two sources the Expertise Finder uses). Nothing is guessed.
"""

SORTS = {"name": "Name (A to Z)", "papers": "Most papers"}


def faculty_keywords(fac):
    """Listed expertise first, then paper keywords not already listed (case-insensitive)."""
    seen, result = set(), []
    for k in list(fac["expertise_list"]) + list(fac["paper_keywords"]):
        if k.lower() not in seen:
            seen.add(k.lower())
            result.append(k)
    return result


def keyword_options(ds):
    """[(label, number_of_faculty)] for the keyword dropdown, A-Z."""
    counts, labels = {}, {}
    for fac in ds.faculty:
        for k in faculty_keywords(fac):
            counts[k.lower()] = counts.get(k.lower(), 0) + 1
            labels.setdefault(k.lower(), k)
    return sorted(((labels[k], n) for k, n in counts.items()), key=lambda item: item[0].lower())


def parse_min_papers(value):
    try:
        return max(0, min(int(value), 999))
    except (TypeError, ValueError):
        return 0


def filter_faculty(ds, q="", dept="", keyword="", min_papers=0, sort="name"):
    people = list(ds.faculty)
    q = (q or "").strip().lower()
    keyword = (keyword or "").strip().lower()
    min_papers = parse_min_papers(min_papers)

    if q:
        people = [f for f in people if q in f["name"].lower()]
    if dept:
        people = [f for f in people if f["department"] == dept]
    if keyword:
        people = [f for f in people if keyword in {k.lower() for k in faculty_keywords(f)}]
    if min_papers:
        people = [f for f in people if f["paper_count"] >= min_papers]

    people.sort(key=lambda f: f["name"].lower())
    if sort == "papers":
        people.sort(key=lambda f: -f["paper_count"])      # stable: ties stay A-Z
    return people
