import csv
import io

import pytest

from algorithms import data_manager
from app import app


@pytest.fixture
def export_dataset(tmp_path, monkeypatch):
    monkeypatch.setattr(data_manager, "DATA_DIR", str(tmp_path))
    tables = [
        ("faculty.csv", data_manager.FACULTY_COLUMNS, [
            {"faculty_id": "f1", "name": "Alice, Dr.", "department": "Computer Eng"},
            {"faculty_id": "f2", "name": 'Bob "The Builder"', "department": "IT"},
            {"faculty_id": "f3", "name": "Charlie", "department": "Mechanical"},
        ]),
        ("papers.csv", data_manager.PAPER_COLUMNS, [
            {
                "paper_id": "p1",
                "title": 'AI in Healthcare: A "Novel" Approach, Part 1',
                "year": "2024",
                "venue": "IEEE Conf, 2024",
                "doi": "10.1234/ai.2024",
                "keywords": "AI; Healthcare",
                "source_url": "https://example.com/p1",
            },
            {
                "paper_id": "p2",
                "title": "Robotics in Surgery",
                "year": "2025",
                "venue": "Nature Robotics",
                "doi": "10.1234/robotics.2025",
                "keywords": "Robotics; Surgery",
                "source_url": "https://example.com/p2",
            },
            {
                "paper_id": "p3",
                "title": "Quantum Computing",
                "year": "2023",
                "venue": "Quantum Journal",
                "doi": "",
                "keywords": "Quantum",
                "source_url": "https://example.com/p3",
            },
        ]),
        ("authorship.csv", data_manager.AUTHORSHIP_COLUMNS, [
            {"paper_id": "p1", "faculty_id": "f1", "author_order": "1"},
            {"paper_id": "p1", "faculty_id": "f2", "author_order": "2"},
            {"paper_id": "p2", "faculty_id": "f1", "author_order": "1"},
            {"paper_id": "p2", "faculty_id": "f2", "author_order": "2"},
            {"paper_id": "p3", "faculty_id": "f3", "author_order": "1"},
        ]),
    ]
    for filename, columns, rows in tables:
        with (tmp_path / filename).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
    return data_manager.Dataset()


def test_export_publications_csv_format_and_bom(export_dataset):
    with app.test_client() as client:
        res = client.get("/export/publications")
        assert res.status_code == 200
        assert "text/csv" in res.headers.get("Content-Type", "")
        assert 'attachment; filename="publications.csv"' in res.headers.get("Content-Disposition", "")

        # Verify UTF-8 BOM
        data = res.data
        assert data.startswith(b"\xef\xbb\xbf")

        # Parse CSV text
        text = data.decode("utf-8-sig")
        reader = list(csv.reader(io.StringIO(text)))
        assert len(reader) >= 4  # Header + 3 papers
        header = reader[0]
        assert header == ["Title", "Year", "Venue", "Faculty Authors", "Departments", "DOI", "Source URL"]

        # Check special characters and quotes preserved
        p1_row = next(r for r in reader[1:] if "Approach, Part 1" in r[0])
        assert p1_row[0] == 'AI in Healthcare: A "Novel" Approach, Part 1'
        assert p1_row[1] == "2024"
        assert "Alice, Dr." in p1_row[3]
        assert 'Bob "The Builder"' in p1_row[3]


def test_export_publications_filters(export_dataset):
    with app.test_client() as client:
        # Filter by year=2024
        res_year = client.get("/export/publications?year=2024")
        reader_year = list(csv.reader(io.StringIO(res_year.data.decode("utf-8-sig"))))
        assert len(reader_year) == 2  # Header + 1 paper
        assert reader_year[1][1] == "2024"

        # Filter by text search q=quantum
        res_q = client.get("/export/publications?q=quantum")
        reader_q = list(csv.reader(io.StringIO(res_q.data.decode("utf-8-sig"))))
        assert len(reader_q) == 2
        assert "Quantum Computing" in reader_q[1][0]

        # Filter by department
        res_dept = client.get("/export/publications?department=IT")
        reader_dept = list(csv.reader(io.StringIO(res_dept.data.decode("utf-8-sig"))))
        assert len(reader_dept) == 3  # Header + p1 and p2 (both have author f2 in IT)

        # Empty match returns header row only
        res_empty = client.get("/export/publications?q=nonexistentkeyword")
        reader_empty = list(csv.reader(io.StringIO(res_empty.data.decode("utf-8-sig"))))
        assert len(reader_empty) == 1
        assert reader_empty[0] == ["Title", "Year", "Venue", "Faculty Authors", "Departments", "DOI", "Source URL"]

        # Alias route /publications/export works identically
        res_alias = client.get("/publications/export?year=2024")
        assert res_alias.status_code == 200
        assert len(list(csv.reader(io.StringIO(res_alias.data.decode("utf-8-sig"))))) == 2


def test_export_network_csv(export_dataset):
    with app.test_client() as client:
        res = client.get("/export/network")
        assert res.status_code == 200
        assert "text/csv" in res.headers.get("Content-Type", "")
        assert 'attachment; filename="collaboration_network.csv"' in res.headers.get("Content-Disposition", "")

        # Verify UTF-8 BOM
        data = res.data
        assert data.startswith(b"\xef\xbb\xbf")

        reader = list(csv.reader(io.StringIO(data.decode("utf-8-sig"))))
        assert len(reader) == 2  # Header + 1 collaboration edge (f1 and f2)
        assert reader[0] == ["Faculty A", "Faculty B", "Shared Papers", "Paper Titles"]
        edge_row = reader[1]
        assert "2" in edge_row[2]  # weight = 2 shared papers
        assert "AI in Healthcare" in edge_row[3]
        assert "Robotics in Surgery" in edge_row[3]


def test_export_network_filters_and_empty(export_dataset):
    with app.test_client() as client:
        # Filter by year range (only 2024)
        res_filtered = client.get("/export/network?year_from=2024&year_to=2024")
        reader_filtered = list(csv.reader(io.StringIO(res_filtered.data.decode("utf-8-sig"))))
        assert len(reader_filtered) == 2
        assert reader_filtered[1][2] == "1"

        # min_weight=3 filters out the edge of weight 2 -> empty edge list returns header only
        res_empty = client.get("/export/network?min_weight=3")
        reader_empty = list(csv.reader(io.StringIO(res_empty.data.decode("utf-8-sig"))))
        assert len(reader_empty) == 1
        assert reader_empty[0] == ["Faculty A", "Faculty B", "Shared Papers", "Paper Titles"]

        # Alias route /network/export
        res_alias = client.get("/network/export")
        assert res_alias.status_code == 200
