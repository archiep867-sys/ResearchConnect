import csv

import pytest

from algorithms import data_manager, faculty_filters
from algorithms.data_manager import Dataset
import app as app_module


def write_csv(path, columns, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def ds(tmp_path, monkeypatch):
    monkeypatch.setattr(data_manager, "DATA_DIR", str(tmp_path))
    write_csv(tmp_path / "faculty.csv", data_manager.FACULTY_COLUMNS, [
        {"faculty_id": "f1", "name": "Alice", "department": "IT", "expertise": "AI; Vision"},
        {"faculty_id": "f2", "name": "Bob", "department": "Physics", "expertise": ""},
        {"faculty_id": "f3", "name": "Carol", "department": "IT", "expertise": ""},
    ])
    write_csv(tmp_path / "papers.csv", data_manager.PAPER_COLUMNS, [
        {"paper_id": "p1", "title": "T1", "year": "2024", "keywords": "hydrogen; catalysis"},
        {"paper_id": "p2", "title": "T2", "year": "2025", "keywords": "hydrogen"},
        {"paper_id": "p3", "title": "T3", "year": "2025", "keywords": "ai"},
    ])
    write_csv(tmp_path / "authorship.csv", data_manager.AUTHORSHIP_COLUMNS, [
        {"paper_id": "p1", "faculty_id": "f2", "author_order": "1"},
        {"paper_id": "p2", "faculty_id": "f2", "author_order": "1"},
        {"paper_id": "p3", "faculty_id": "f3", "author_order": "1"},
    ])
    return Dataset()


def names(people):
    return [p["name"] for p in people]


def test_keyword_uses_expertise_and_paper_keywords(ds):
    assert names(faculty_filters.filter_faculty(ds, keyword="hydrogen")) == ["Bob"]
    assert names(faculty_filters.filter_faculty(ds, keyword="VISION")) == ["Alice"]   # case-insensitive
    assert names(faculty_filters.filter_faculty(ds, keyword="ai")) == ["Alice", "Carol"]


def test_filters_combine(ds):
    assert names(faculty_filters.filter_faculty(ds, dept="IT", keyword="ai")) == ["Alice", "Carol"]
    assert names(faculty_filters.filter_faculty(ds, dept="Physics", keyword="ai")) == []
    assert names(faculty_filters.filter_faculty(ds, min_papers=2)) == ["Bob"]
    assert names(faculty_filters.filter_faculty(ds, q="ali")) == ["Alice"]


def test_sort_by_papers_keeps_ties_alphabetical(ds):
    assert names(faculty_filters.filter_faculty(ds, sort="papers")) == ["Bob", "Carol", "Alice"]


def test_parse_min_papers_is_safe():
    assert faculty_filters.parse_min_papers("abc") == 0
    assert faculty_filters.parse_min_papers("-4") == 0
    assert faculty_filters.parse_min_papers("2") == 2


def test_faculty_route_applies_filters_and_ignores_bad_input(ds):
    client = app_module.app.test_client()
    html = client.get("/faculty?keyword=hydrogen&sort=papers").get_data(as_text=True)
    assert "Bob" in html and "Alice" not in html
    assert client.get("/faculty?min_papers=zzz&sort=evil").status_code == 200
    assert "Showing 0 of 3" in client.get("/faculty?department=Nope").get_data(as_text=True)


def test_new_pages_render(ds):
    client = app_module.app.test_client()
    assert client.get("/saved").status_code == 200
    short = client.get("/shortlist").get_data(as_text=True)
    assert "Alice" in short and 'id="rc-data"' in short
    paper = client.get("/publications/p1").get_data(as_text=True)
    assert "Cite this paper" in paper and "@" in paper
