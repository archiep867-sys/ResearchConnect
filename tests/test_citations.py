from algorithms import citations


def paper(**over):
    base = {
        "paper_id": "P1", "title": "Graph Research & Networks", "year_num": 2025,
        "venue": "Test Journal", "doi": "10.1234/graph", "doi_link": "https://doi.org/10.1234/graph",
        "authors": [{"name": "Dr. Alice B. Smith"}, {"name": "Prof. Raj Kumar"}],
    }
    base.update(over)
    return base


def test_split_name_drops_titles():
    assert citations.split_name("Dr. Deepak S. Gavali") == (["Deepak", "S."], "Gavali")
    assert citations.split_name("Ravindra Kumar Maurya") == (["Ravindra", "Kumar"], "Maurya")
    assert citations.split_name("Name not listed") is None
    assert citations.split_name("") is None


def test_apa_and_ieee_formats():
    assert citations.apa(paper()) == (
        "Smith, A. B., & Kumar, R. (2025). Graph Research & Networks. Test Journal. https://doi.org/10.1234/graph")
    assert citations.ieee(paper()).startswith("A. B. Smith and R. Kumar, \u201cGraph Research & Networks,\u201d Test Journal, 2025, doi: 10.1234/graph")


def test_bibtex_escapes_and_picks_entry_type():
    bib = citations.bibtex(paper())
    assert bib.startswith("@article{smith2025graph,")
    assert "Smith, Alice B. and Kumar, Raj" in bib
    assert "Research \\& Networks" in bib
    conf = citations.bibtex(paper(venue="International Conference on Data"))
    assert conf.startswith("@inproceedings") and "booktitle" in conf


def test_missing_fields_are_left_out_not_invented():
    bare = paper(authors=[], year_num=None, venue="", doi="", doi_link="")
    assert citations.apa(bare) == "Graph Research & Networks. (n.d.)."
    assert "doi" not in citations.bibtex(bare) and "year" not in citations.bibtex(bare)
    assert citations.bibtex(bare).startswith("@misc{")
    assert citations.citations_for(bare)["has_authors"] is False
