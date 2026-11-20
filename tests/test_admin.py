import csv

import pytest

from algorithms import data_manager
from app import app


@pytest.fixture
def admin_dataset(tmp_path, monkeypatch):
    monkeypatch.setattr(data_manager, "DATA_DIR", str(tmp_path))
    tables = [
        ("faculty.csv", data_manager.FACULTY_COLUMNS, [
            {"faculty_id": "f1", "name": "Alice", "department": "IT"},
        ]),
        ("papers.csv", data_manager.PAPER_COLUMNS, [
            {"paper_id": "p1", "title": "Paper 1", "year": "2024"},
        ]),
        ("authorship.csv", data_manager.AUTHORSHIP_COLUMNS, [
            {"paper_id": "p1", "faculty_id": "f1", "author_order": "1"},
        ]),
    ]
    for filename, columns, rows in tables:
        with (tmp_path / filename).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
    return data_manager.Dataset()


def test_admin_route_disabled_by_default():
    # ADMIN_ENABLED is False by default
    app.config["ADMIN_ENABLED"] = False
    with app.test_client() as client:
        res = client.get("/admin")
        assert res.status_code == 404


def test_admin_route_requires_password_env(monkeypatch):
    app.config["ADMIN_ENABLED"] = True
    monkeypatch.delenv("RC_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    with app.test_client() as client:
        res = client.get("/admin")
        assert res.status_code == 403


def test_admin_route_wrong_password_rejected(admin_dataset, monkeypatch):
    app.config["ADMIN_ENABLED"] = True
    monkeypatch.setenv("RC_ADMIN_PASSWORD", "secret123")
    with app.test_client() as client:
        res = client.post("/admin", data={
            "password": "wrong_password",
            "table_type": "faculty",
            "faculty_id": "f2",
            "name": "Bob",
        })
        assert res.status_code == 200
        html = res.get_data(as_text=True)
        assert "Invalid admin password" in html


def test_dataset_add_faculty_creates_backup_and_validates(tmp_path, monkeypatch):
    monkeypatch.setattr(data_manager, "DATA_DIR", str(tmp_path))
    tables = [
        ("faculty.csv", data_manager.FACULTY_COLUMNS, [{"faculty_id": "f1", "name": "Alice"}]),
        ("papers.csv", data_manager.PAPER_COLUMNS, []),
        ("authorship.csv", data_manager.AUTHORSHIP_COLUMNS, []),
    ]
    for filename, columns, rows in tables:
        with (tmp_path / filename).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)

    ds = data_manager.Dataset()

    # Blank ID rejected
    with pytest.raises(ValueError, match="blank"):
        ds.add_faculty({"faculty_id": "", "name": "No ID"})

    # Duplicate ID rejected
    with pytest.raises(ValueError, match="already exists"):
        ds.add_faculty({"faculty_id": "f1", "name": "Duplicate Alice"})

    # Valid add creates backup and appends row
    ds.add_faculty({"faculty_id": "f2", "name": "Bob", "department": "EXTC"})

    backups = list(tmp_path.glob("faculty.csv.*.bak"))
    assert len(backups) == 1
    assert "f2" in ds.faculty_by_id
    assert ds.faculty_by_id["f2"]["name"] == "Bob"

    # Verify written file
    rows = list(csv.DictReader((tmp_path / "faculty.csv").open(encoding="utf-8-sig")))
    assert len(rows) == 2
    assert rows[1]["faculty_id"] == "f2"


def test_dataset_add_paper_creates_backup_and_validates(tmp_path, monkeypatch):
    monkeypatch.setattr(data_manager, "DATA_DIR", str(tmp_path))
    tables = [
        ("faculty.csv", data_manager.FACULTY_COLUMNS, []),
        ("papers.csv", data_manager.PAPER_COLUMNS, [{"paper_id": "p1", "title": "Paper 1"}]),
        ("authorship.csv", data_manager.AUTHORSHIP_COLUMNS, []),
    ]
    for filename, columns, rows in tables:
        with (tmp_path / filename).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)

    ds = data_manager.Dataset()

    with pytest.raises(ValueError, match="already exists"):
        ds.add_paper({"paper_id": "p1", "title": "Dup"})

    ds.add_paper({"paper_id": "p2", "title": "Paper 2", "year": "2025"})
    backups = list(tmp_path.glob("papers.csv.*.bak"))
    assert len(backups) == 1
    assert "p2" in ds.papers_by_id


def test_dataset_add_authorship_creates_backup_and_validates(tmp_path, monkeypatch):
    monkeypatch.setattr(data_manager, "DATA_DIR", str(tmp_path))
    tables = [
        ("faculty.csv", data_manager.FACULTY_COLUMNS, [{"faculty_id": "f1", "name": "Alice"}]),
        ("papers.csv", data_manager.PAPER_COLUMNS, [{"paper_id": "p1", "title": "Paper 1"}]),
        ("authorship.csv", data_manager.AUTHORSHIP_COLUMNS, []),
    ]
    for filename, columns, rows in tables:
        with (tmp_path / filename).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)

    ds = data_manager.Dataset()

    # Nonexistent paper rejected
    with pytest.raises(ValueError, match="Referenced paper ID 'p999' does not exist"):
        ds.add_authorship({"paper_id": "p999", "faculty_id": "f1"})

    # Nonexistent faculty rejected
    with pytest.raises(ValueError, match="Referenced faculty ID 'f999' does not exist"):
        ds.add_authorship({"paper_id": "p1", "faculty_id": "f999"})

    # Valid add
    ds.add_authorship({"paper_id": "p1", "faculty_id": "f1", "author_order": "1"})
    backups = list(tmp_path.glob("authorship.csv.*.bak"))
    assert len(backups) == 1
    assert ds.paper_authors.get("p1") == ["f1"]


def test_write_aborts_if_backup_fails(admin_dataset, monkeypatch):
    def broken_backup(filename):
        raise RuntimeError("Simulated disk error during backup")

    monkeypatch.setattr(admin_dataset, "create_backup", broken_backup)

    with pytest.raises(RuntimeError, match="Simulated disk error"):
        admin_dataset.add_faculty({"faculty_id": "f99", "name": "Should Not Write"})

    # Faculty was not added
    assert "f99" not in admin_dataset.faculty_by_id


def test_admin_route_successful_post(admin_dataset, tmp_path, monkeypatch):
    app.config["ADMIN_ENABLED"] = True
    monkeypatch.setenv("RC_ADMIN_PASSWORD", "mypassword")
    with app.test_client() as client:
        res = client.post("/admin", data={
            "password": "mypassword",
            "table_type": "faculty",
            "faculty_id": "f100",
            "name": "Dr. New Faculty",
            "department": "Civil",
            "expertise": "Structures; Concrete",
        })
        assert res.status_code == 200
        html = res.get_data(as_text=True)
        assert "f100" in html
        assert "added successfully" in html
        assert "backup created" in html


def test_admin_route_post_paper_and_authorship(admin_dataset, tmp_path, monkeypatch):
    app.config["ADMIN_ENABLED"] = True
    monkeypatch.setenv("RC_ADMIN_PASSWORD", "mypassword")
    with app.test_client() as client:
        # Add paper
        res_paper = client.post("/admin", data={
            "password": "mypassword",
            "table_type": "paper",
            "paper_id": "p200",
            "title": "Quantum Computing Advances",
            "year": "2026",
            "venue": "IEEE Quantum",
        })
        assert res_paper.status_code == 200
        html_p = res_paper.get_data(as_text=True)
        assert "p200" in html_p
        assert "added successfully" in html_p
        assert len(list(tmp_path.glob("papers.csv.*.bak"))) >= 1

        # Add authorship link between p200 and existing faculty f1
        res_auth = client.post("/admin", data={
            "password": "mypassword",
            "table_type": "authorship",
            "paper_id": "p200",
            "faculty_id": "f1",
            "author_order": "1",
        })
        assert res_auth.status_code == 200
        html_a = res_auth.get_data(as_text=True)
        assert "p200" in html_a
        assert "f1" in html_a
        assert "added successfully" in html_a
        assert len(list(tmp_path.glob("authorship.csv.*.bak"))) >= 1


def test_admin_route_validation_errors(admin_dataset, monkeypatch):
    app.config["ADMIN_ENABLED"] = True
    monkeypatch.setenv("RC_ADMIN_PASSWORD", "mypassword")
    with app.test_client() as client:
        # Duplicate faculty ID
        res_dup = client.post("/admin", data={
            "password": "mypassword",
            "table_type": "faculty",
            "faculty_id": "f1",
            "name": "Duplicate Alice",
        })
        assert res_dup.status_code == 200
        assert "already exists" in res_dup.get_data(as_text=True)

        # Non-existent reference in authorship
        res_ref = client.post("/admin", data={
            "password": "mypassword",
            "table_type": "authorship",
            "paper_id": "p_does_not_exist",
            "faculty_id": "f1",
        })
        assert res_ref.status_code == 200
        assert "does not exist" in res_ref.get_data(as_text=True)

