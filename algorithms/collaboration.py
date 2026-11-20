"""
collaboration.py
----------------
Builds the verified co-authorship network with NetworkX.

  node   = one VJTI faculty member (from faculty.csv)
  edge   = two faculty are listed as authors of the SAME paper (authorship.csv)
  weight = how many papers they share

An edge is NEVER created from shared keywords. Only shared papers count.
If every paper has just one VJTI author, the graph correctly has zero edges.
"""
import csv
import io
import itertools

import networkx as nx

from algorithms.data_manager import clean_year


def build_graph(ds, year_from=None, year_to=None, min_weight=1):
    cleaned_year_from = clean_year(year_from) if year_from is not None else None
    cleaned_year_to = clean_year(year_to) if year_to is not None else None

    # Fall back if year_from is greater than year_to
    if cleaned_year_from is not None and cleaned_year_to is not None and cleaned_year_from > cleaned_year_to:
        cleaned_year_from, cleaned_year_to = None, None

    try:
        min_w = int(float(min_weight)) if min_weight is not None else 1
        if min_w < 1:
            min_w = 1
    except (TypeError, ValueError):
        min_w = 1

    graph = nx.Graph()
    for fac in ds.faculty:
        graph.add_node(fac["faculty_id"])

    year_filter_active = (cleaned_year_from is not None) or (cleaned_year_to is not None)

    # For each paper, pair up every two VJTI authors of that paper.
    for paper_id, author_ids in ds.paper_authors.items():
        if year_filter_active:
            paper = ds.papers_by_id.get(paper_id)
            if not paper or paper.get("year_num") is None:
                continue
            yr = paper["year_num"]
            if cleaned_year_from is not None and yr < cleaned_year_from:
                continue
            if cleaned_year_to is not None and yr > cleaned_year_to:
                continue

        for a, b in itertools.combinations(sorted(set(author_ids)), 2):
            if graph.has_edge(a, b):
                graph[a][b]["weight"] += 1
                graph[a][b]["papers"].append(paper_id)
            else:
                graph.add_edge(a, b, weight=1, papers=[paper_id])

    if min_w > 1:
        low_weight_edges = [(u, v) for u, v, d in graph.edges(data=True) if d.get("weight", 0) < min_w]
        graph.remove_edges_from(low_weight_edges)

    return graph


def network_stats(graph, ds):
    n, m = graph.number_of_nodes(), graph.number_of_edges()
    connected = sum(1 for node in graph if graph.degree(node) > 0)
    multi_author = sum(1 for ids in ds.paper_authors.values() if len(ids) > 1)
    pairs = []
    for a, b, data in graph.edges(data=True):
        pairs.append({
            "a": ds.faculty_by_id[a]["name"],
            "b": ds.faculty_by_id[b]["name"],
            "shared": data["weight"],
            "titles": [ds.papers_by_id[p]["title"] for p in data["papers"]],
        })
    pairs.sort(key=lambda p: (-p["shared"], p["a"]))
    return {
        "faculty": n,
        "links": m,
        "collaborating": connected,
        "isolated": n - connected,
        "multi_author_papers": multi_author,
        "density": round(nx.density(graph), 3) if n > 1 else 0,
        "top_pairs": pairs[:10],
    }


def collaborators_of(graph, ds, faculty_id):
    """[(faculty dict, shared paper count)] for one person."""
    if faculty_id not in graph:
        return []
    found = [(ds.faculty_by_id[other], graph[faculty_id][other]["weight"]) for other in graph[faculty_id]]
    found.sort(key=lambda item: (-item[1], item[0]["name"]))
    return found


def network_for_plot(graph, ds):
    """Plain dicts/lists describing the graph. The browser draws it with Plotly.js."""
    n = graph.number_of_nodes()
    if n == 0:
        return {"nodes": [], "edges": []}

    # Positions: spring layout when there are links, otherwise a tidy circle.
    if graph.number_of_edges() > 0:
        pos = nx.spring_layout(graph, seed=42, weight="weight")
    else:
        pos = nx.circular_layout(graph)

    centrality = nx.degree_centrality(graph) if n > 1 else {node: 0 for node in graph}

    nodes = []
    for fid in graph.nodes:
        fac = ds.faculty_by_id[fid]
        nodes.append({
            "id": fid,
            "name": fac["name"],
            "department": fac["department"],
            "paper_count": fac["paper_count"],
            "degree": graph.degree(fid),
            "size": round(16 + 34 * centrality[fid], 1),       # bigger = more collaborators
            "x": float(pos[fid][0]),
            "y": float(pos[fid][1]),
            "profile": "/faculty/" + fid,
            "collaborators": [{"name": f["name"], "shared": w} for f, w in collaborators_of(graph, ds, fid)],
        })

    edges = []
    for a, b, data in graph.edges(data=True):
        edges.append({
            "x0": float(pos[a][0]), "y0": float(pos[a][1]),
            "x1": float(pos[b][0]), "y1": float(pos[b][1]),
            "weight": data["weight"],
            "label": f'{ds.faculty_by_id[a]["name"]} and {ds.faculty_by_id[b]["name"]}: '
                     f'{data["weight"]} shared paper(s)',
        })
    return {"nodes": nodes, "edges": edges}


def centrality_table(graph, ds):
    """Return degree and betweenness centrality per faculty member.

    Sorted by betweenness descending. Handles empty graphs and single-node
    graphs (degree centrality for <= 1 node is returned as 0.0).
    Values are unrounded floats; rounding is handled in the template.
    """
    n = graph.number_of_nodes()
    if n == 0:
        return []

    if n == 1:
        degree_cent = {node: 0.0 for node in graph.nodes}
        between_cent = {node: 0.0 for node in graph.nodes}
    else:
        degree_cent = nx.degree_centrality(graph)
        between_cent = nx.betweenness_centrality(graph)

    table = []
    for fid in graph.nodes:
        fac = ds.faculty_by_id.get(fid, {})
        raw_name = fac.get("name", "")
        name = "Not listed" if (not raw_name or raw_name == "Name not listed") else raw_name
        department = fac.get("department") or "Not listed"

        table.append({
            "faculty_id": fid,
            "name": name,
            "faculty_name": name,
            "department": department,
            "degree_centrality": float(degree_cent.get(fid, 0.0)),
            "betweenness_centrality": float(between_cent.get(fid, 0.0)),
        })

    table.sort(key=lambda r: (-r["betweenness_centrality"], -r["degree_centrality"], r["name"].lower()))
    return table


def network_to_csv(graph, ds):
    """Generate CSV bytes (UTF-8 with BOM) for network edges.
    An empty result returns a file with the header row only.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Faculty A", "Faculty B", "Shared Papers", "Paper Titles"])
    for a, b, data in graph.edges(data=True):
        name_a = ds.faculty_by_id[a]["name"] if a in ds.faculty_by_id else a
        name_b = ds.faculty_by_id[b]["name"] if b in ds.faculty_by_id else b
        weight = data.get("weight", 1)
        paper_titles = "; ".join(
            ds.papers_by_id[p]["title"] for p in data.get("papers", []) if p in ds.papers_by_id
        )
        writer.writerow([name_a, name_b, weight, paper_titles])
    return output.getvalue().encode("utf-8-sig")

