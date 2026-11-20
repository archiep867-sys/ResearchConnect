import csv
import os
import time

import pandas as pd
import pytest

from algorithms import data_manager


def write_csv(path, columns, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def test_clean_year_accepts_valid_integer_and_decimal_strings():
    assert data_manager.clean_year("2024") == 2024
    assert data_manager.clean_year("2024.0") == 2024
    assert data_manager.clean_year("1899") is None
    assert data_manager.clean_year("2101") is None
    assert data_manager.clean_year("unknown") is None
    assert data_manager.clean_year("") is None


def test_clean_int_uses_default_for_invalid_values():
    assert data_manager.clean_int("2") == 2
    assert data_manager.clean_int("2.0") == 2
    assert data_manager.clean_int("bad") == 9999
    assert data_manager.clean_int("bad", default=-1) == -1


@pytest.mark.parametrize("text,expected", [
    ("AI; IoT; Robotics", ["AI", "IoT", "Robotics"]),
    ("AI; ai;  IoT  ", ["AI", "IoT"]),
    ("Deep Learning, Computer Vision", ["Deep Learning", "Computer Vision"]),
    ("", []),
    (None, []),
])
def test_split_keywords(text, expected):
    assert data_manager.split_keywords(text) == expected


def test_split_keywords_can_parse_comma_separated_query():
    assert data_manager.split_keywords("AI, IoT; Robotics", semicolon_first=False) == ["AI", "IoT", "Robotics"]


def test_safe_url_only_allows_http_and_https():
    assert data_manager.safe_url(" https://example.com ") == "https://example.com"
    assert data_manager.safe_url("http://example.com") == "http://example.com"
    assert data_manager.safe_url("javascript:alert(1)") == ""
    assert data_manager.safe_url("") == ""


def test_doi_to_url_handles_blank_url_and_existing_url():
    assert data_manager.doi_to_url("") == ""
    assert data_manager.doi_to_url("10.1234/example") == "https://doi.org/10.1234/example"
    assert data_manager.doi_to_url("https://doi.org/10.1234/example") == "https://doi.org/10.1234/example"


def test_read_csv_safe_returns_expected_columns_and_stripped_values(tmp_path, monkeypatch):
    monkeypatch.setattr(data_manager, "DATA_DIR", str(tmp_path))
    write_csv(tmp_path / "faculty.csv", ["faculty_id", "name"], [
        {"faculty_id": " f1 ", "name": " Alice "},
    ])
    result = data_manager.read_csv_safe("faculty.csv", data_manager.FACULTY_COLUMNS)
    assert list(result.columns) == data_manager.FACULTY_COLUMNS
    assert result.iloc[0]["faculty_id"] == "f1"
    assert result.iloc[0]["name"] == "Alice"
    assert result.iloc[0]["department"] == ""


def test_read_csv_safe_missing_file_returns_empty_table(tmp_path, monkeypatch):
    monkeypatch.setattr(data_manager, "DATA_DIR", str(tmp_path))
    result = data_manager.read_csv_safe("missing.csv", data_manager.PAPER_COLUMNS)
    assert isinstance(result, pd.DataFrame)
    assert result.empty
    assert list(result.columns) == data_manager.PAPER_COLUMNS


def test_dataset_links_papers_authors_and_keywords(tmp_path, monkeypatch):
    monkeypatch.setattr(data_manager, "DATA_DIR", str(tmp_path))
    write_csv(tmp_path / "faculty.csv", data_manager.FACULTY_COLUMNS, [
        {"faculty_id": "f1", "name": "Alice", "expertise": "Networks"},
    ])
    write_csv(tmp_path / "papers.csv", data_manager.PAPER_COLUMNS, [
        {"paper_id": "p1", "title": "Research Paper", "year": "2024", "keywords": "AI; IoT"},
    ])
    write_csv(tmp_path / "authorship.csv", data_manager.AUTHORSHIP_COLUMNS, [
        {"paper_id": "p1", "faculty_id": "f1", "author_order": "1"},
    ])

    ds = data_manager.Dataset()
    assert ds.faculty_by_id["f1"]["paper_count"] == 1
    assert ds.papers_by_id["p1"]["authors"][0]["name"] == "Alice"
    assert ds.faculty_by_id["f1"]["paper_keywords"] == ["AI", "IoT"]
    assert ds.keyword_options() == [("ai", "AI"), ("iot", "IoT"), ("networks", "Networks")]


def test_get_dataset_returns_cached_instance_when_files_untouched(tmp_path):
    write_csv(tmp_path / "faculty.csv", data_manager.FACULTY_COLUMNS, [
        {"faculty_id": "f1", "name": "Alice"},
    ])
    write_csv(tmp_path / "papers.csv", data_manager.PAPER_COLUMNS, [])
    write_csv(tmp_path / "authorship.csv", data_manager.AUTHORSHIP_COLUMNS, [])

    ds1 = data_manager.get_dataset(data_dir=str(tmp_path))
    ds2 = data_manager.get_dataset(data_dir=str(tmp_path))

    # Consecutive calls return the exact same instance
    assert ds1 is ds2
    assert "f1" in ds1.faculty_by_id


def test_get_dataset_rebuilds_when_csv_modified(tmp_path):
    fac_path = tmp_path / "faculty.csv"
    write_csv(fac_path, data_manager.FACULTY_COLUMNS, [
        {"faculty_id": "f1", "name": "Alice"},
    ])
    write_csv(tmp_path / "papers.csv", data_manager.PAPER_COLUMNS, [])
    write_csv(tmp_path / "authorship.csv", data_manager.AUTHORSHIP_COLUMNS, [])

    ds1 = data_manager.get_dataset(data_dir=str(tmp_path))
    assert "f2" not in ds1.faculty_by_id

    # Append new row and ensure timestamp updates
    new_mtime = time.time() + 10
    with fac_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=data_manager.FACULTY_COLUMNS)
        writer.writerow({"faculty_id": "f2", "name": "Bob"})
    os.utime(str(fac_path), (new_mtime, new_mtime))

    ds2 = data_manager.get_dataset(data_dir=str(tmp_path))

    # Should be a freshly rebuilt Dataset object
    assert ds2 is not ds1
    assert "f2" in ds2.faculty_by_id
    assert ds2.faculty_by_id["f2"]["name"] == "Bob"


def test_get_dataset_custom_data_dir_isolation(tmp_path):
    dir_a = tmp_path / "dir_a"
    dir_b = tmp_path / "dir_b"
    dir_a.mkdir()
    dir_b.mkdir()

    write_csv(dir_a / "faculty.csv", data_manager.FACULTY_COLUMNS, [{"faculty_id": "fA", "name": "Faculty A"}])
    write_csv(dir_a / "papers.csv", data_manager.PAPER_COLUMNS, [])
    write_csv(dir_a / "authorship.csv", data_manager.AUTHORSHIP_COLUMNS, [])

    write_csv(dir_b / "faculty.csv", data_manager.FACULTY_COLUMNS, [{"faculty_id": "fB", "name": "Faculty B"}])
    write_csv(dir_b / "papers.csv", data_manager.PAPER_COLUMNS, [])
    write_csv(dir_b / "authorship.csv", data_manager.AUTHORSHIP_COLUMNS, [])

    ds_a = data_manager.get_dataset(data_dir=str(dir_a))
    ds_b = data_manager.get_dataset(data_dir=str(dir_b))

    assert ds_a is not ds_b
    assert "fA" in ds_a.faculty_by_id and "fB" not in ds_a.faculty_by_id
    assert "fB" in ds_b.faculty_by_id and "fA" not in ds_b.faculty_by_id


def test_get_dataset_rebuilds_on_file_removal_or_recreation(tmp_path):
    pap_path = tmp_path / "papers.csv"
    write_csv(tmp_path / "faculty.csv", data_manager.FACULTY_COLUMNS, [])
    write_csv(pap_path, data_manager.PAPER_COLUMNS, [{"paper_id": "p1", "title": "First Paper"}])
    write_csv(tmp_path / "authorship.csv", data_manager.AUTHORSHIP_COLUMNS, [])

    ds1 = data_manager.get_dataset(data_dir=str(tmp_path))
    assert "p1" in ds1.papers_by_id

    # Remove the file
    pap_path.unlink()
    ds2 = data_manager.get_dataset(data_dir=str(tmp_path))
    assert ds2 is not ds1
    assert "p1" not in ds2.papers_by_id

