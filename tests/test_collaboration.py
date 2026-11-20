import csv

import pytest

from algorithms import collaboration, data_manager


@pytest.fixture
def ds(tmp_path, monkeypatch):
    """A small dataset with one genuine co-authored paper and one solo paper."""
    monkeypatch.setattr(data_manager, "DATA_DIR", str(tmp_path))
    tables = [
        ("faculty.csv", data_manager.FACULTY_COLUMNS, [
            {"faculty_id": "f1", "name": "Alice", "department": "IT"},
            {"faculty_id": "f2", "name": "Bob", "department": "IT"},
            {"faculty_id": "f3", "name": "Cara", "department": "EXTC"},
        ]),
        ("papers.csv", data_manager.PAPER_COLUMNS, [
            {"paper_id": "p1", "title": "Shared Paper", "year": "2024"},
            {"paper_id": "p2", "title": "Second Shared Paper", "year": "2025"},
            {"paper_id": "p3", "title": "Solo Paper", "year": "2023"},
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


def test_build_graph_creates_all_faculty_nodes_and_verified_edges(ds):
    graph = collaboration.build_graph(ds)
    assert set(graph.nodes) == {"f1", "f2", "f3"}
    assert graph.number_of_edges() == 1
    assert graph["f1"]["f2"]["weight"] == 2
    assert graph["f1"]["f2"]["papers"] == ["p1", "p2"]
    assert not graph.has_edge("f1", "f3")


def test_network_stats_reports_collaboration_counts(ds):
    graph = collaboration.build_graph(ds)
    stats = collaboration.network_stats(graph, ds)
    assert stats["faculty"] == 3
    assert stats["links"] == 1
    assert stats["collaborating"] == 2
    assert stats["isolated"] == 1
    assert stats["multi_author_papers"] == 2
    assert stats["top_pairs"][0]["titles"] == ["Shared Paper", "Second Shared Paper"]


def test_collaborators_of_returns_weighted_collaborators(ds):
    graph = collaboration.build_graph(ds)
    found = collaboration.collaborators_of(graph, ds, "f1")
    assert [(faculty["faculty_id"], weight) for faculty, weight in found] == [("f2", 2)]
    assert collaboration.collaborators_of(graph, ds, "unknown") == []


def test_network_for_plot_contains_nodes_and_edges(ds):
    graph = collaboration.build_graph(ds)
    result = collaboration.network_for_plot(graph, ds)
    assert len(result["nodes"]) == 3
    assert len(result["edges"]) == 1
    alice = next(node for node in result["nodes"] if node["id"] == "f1")
    assert alice["degree"] == 1
    assert alice["collaborators"] == [{"name": "Bob", "shared": 2}]


def test_empty_graph_helpers_are_safe():
    import networkx as nx

    class EmptyDataset:
        def __init__(self):
            self.faculty = []
            self.faculty_by_id = {}
            self.paper_authors = {}
            self.papers_by_id = {}

    graph = nx.Graph()
    stats = collaboration.network_stats(graph, EmptyDataset())
    assert stats["faculty"] == 0
    assert stats["links"] == 0
    assert stats["density"] == 0
    assert collaboration.network_for_plot(graph, EmptyDataset()) == {"nodes": [], "edges": []}


def test_build_graph_year_filtering(ds):
    # p1 is 2024, p2 is 2025. Both share f1 and f2.
    graph_all = collaboration.build_graph(ds)
    assert graph_all["f1"]["f2"]["weight"] == 2

    graph_2024 = collaboration.build_graph(ds, year_from=2024, year_to=2024)
    assert graph_2024["f1"]["f2"]["weight"] == 1
    assert graph_2024["f1"]["f2"]["papers"] == ["p1"]

    graph_2025 = collaboration.build_graph(ds, year_from=2025)
    assert graph_2025["f1"]["f2"]["weight"] == 1
    assert graph_2025["f1"]["f2"]["papers"] == ["p2"]

    graph_past = collaboration.build_graph(ds, year_to=2023)
    assert graph_past.number_of_edges() == 0
    assert set(graph_past.nodes) == {"f1", "f2", "f3"}


def test_build_graph_excludes_papers_with_no_year_when_year_filter_active(tmp_path, monkeypatch):
    monkeypatch.setattr(data_manager, "DATA_DIR", str(tmp_path))
    tables = [
        ("faculty.csv", data_manager.FACULTY_COLUMNS, [
            {"faculty_id": "f1", "name": "Alice"},
            {"faculty_id": "f2", "name": "Bob"},
        ]),
        ("papers.csv", data_manager.PAPER_COLUMNS, [
            {"paper_id": "p1", "title": "Paper No Year", "year": ""},
            {"paper_id": "p2", "title": "Paper 2024", "year": "2024"},
        ]),
        ("authorship.csv", data_manager.AUTHORSHIP_COLUMNS, [
            {"paper_id": "p1", "faculty_id": "f1"},
            {"paper_id": "p1", "faculty_id": "f2"},
            {"paper_id": "p2", "faculty_id": "f1"},
            {"paper_id": "p2", "faculty_id": "f2"},
        ]),
    ]
    for filename, columns, rows in tables:
        with (tmp_path / filename).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
    custom_ds = data_manager.Dataset()

    # Without year filter, both papers count -> weight 2
    g_unfiltered = collaboration.build_graph(custom_ds)
    assert g_unfiltered["f1"]["f2"]["weight"] == 2

    # With year filter, p1 (no year) is excluded -> weight 1
    g_filtered = collaboration.build_graph(custom_ds, year_from=2020)
    assert g_filtered["f1"]["f2"]["weight"] == 1
    assert g_filtered["f1"]["f2"]["papers"] == ["p2"]


def test_build_graph_min_weight(ds):
    # Weight of (f1, f2) is 2
    g_w2 = collaboration.build_graph(ds, min_weight=2)
    assert g_w2.number_of_edges() == 1

    # min_weight=3 should prune the edge, but keep all faculty nodes
    g_w3 = collaboration.build_graph(ds, min_weight=3)
    assert g_w3.number_of_edges() == 0
    assert set(g_w3.nodes) == {"f1", "f2", "f3"}


def test_build_graph_invalid_inputs_fallback(ds):
    # Non-numeric or negative inputs fall back cleanly
    g1 = collaboration.build_graph(ds, year_from="invalid", year_to=-10, min_weight="bad")
    assert g1.number_of_edges() == 1
    assert g1["f1"]["f2"]["weight"] == 2

    # year_from > year_to falls back to no year bounds
    g2 = collaboration.build_graph(ds, year_from=2025, year_to=2020)
    assert g2.number_of_edges() == 1
    assert g2["f1"]["f2"]["weight"] == 2


def test_centrality_table_normal_graph(ds):
    graph = collaboration.build_graph(ds)
    table = collaboration.centrality_table(graph, ds)
    assert len(table) == 3

    # Table contains dicts with expected keys
    first = table[0]
    assert "name" in first
    assert "department" in first
    assert "degree_centrality" in first
    assert "betweenness_centrality" in first
    assert isinstance(first["degree_centrality"], float)
    assert isinstance(first["betweenness_centrality"], float)

    # Sorted by betweenness descending
    for i in range(len(table) - 1):
        assert table[i]["betweenness_centrality"] >= table[i + 1]["betweenness_centrality"]


def test_centrality_table_handles_edgeless_graph(ds):
    import networkx as nx
    g = nx.Graph()
    for f in ds.faculty:
        g.add_node(f["faculty_id"])

    table = collaboration.centrality_table(g, ds)
    assert len(table) == 3
    for row in table:
        assert row["degree_centrality"] == 0.0
        assert row["betweenness_centrality"] == 0.0


def test_centrality_table_single_node():
    import networkx as nx

    class SingleNodeDS:
        def __init__(self):
            self.faculty_by_id = {"f1": {"name": "Solo", "department": ""}}

    g = nx.Graph()
    g.add_node("f1")
    table = collaboration.centrality_table(g, SingleNodeDS())
    assert len(table) == 1
    assert table[0]["degree_centrality"] == 0.0
    assert table[0]["betweenness_centrality"] == 0.0
    assert table[0]["department"] == "Not listed"


def test_centrality_table_empty_graph():
    import networkx as nx

    class EmptyDS:
        def __init__(self):
            self.faculty_by_id = {}

    g = nx.Graph()
    table = collaboration.centrality_table(g, EmptyDS())
    assert table == []


def test_network_route(ds):
    from app import app
    with app.test_client() as client:
        # Default load
        res = client.get("/network")
        assert res.status_code == 200
        html = res.get_data(as_text=True)
        assert "Faculty centrality" in html
        assert "Minimum shared papers" in html
        assert "Download CSV" in html

        # With valid filters
        res2 = client.get("/network?year_from=2024&year_to=2025&min_weight=1")
        assert res2.status_code == 200
        html2 = res2.get_data(as_text=True)
        assert "Papers with no publication year are excluded while a year filter is active." in html2

        # With invalid year range (year_from > year_to)
        res3 = client.get("/network?year_from=2025&year_to=2020")
        assert res3.status_code == 200
        html3 = res3.get_data(as_text=True)
        assert "cannot be greater than" in html3

