"""
app.py - ResearchConnect: VJTI Faculty Research Collaboration and Expertise Mapper

This file only connects web pages (routes) to the logic in the algorithms/ folder:
    data_manager.py  -> reads and cleans the CSV files
    expertise.py     -> Jaccard keyword matching
    collaboration.py -> NetworkX co-authorship graph
    analytics.py     -> counts and chart data

Run it with:   python app.py      then open  http://127.0.0.1:5000
"""
<<<<<<< ours
import os
from flask import Flask, abort, render_template, request, url_for, Response

from algorithms import analytics, collaboration, data_manager, expertise, quality
from algorithms.data_manager import Dataset, clean_year

# Load environment configuration from .env if present
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env_path):
    with open(_env_path, "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip().strip("'\""))
=======
from flask import Flask, abort, render_template, request, url_for

from algorithms import analytics, citations, collaboration, expertise, faculty_filters, quality
from algorithms.data_manager import Dataset
>>>>>>> theirs

app = Flask(__name__)
app.config["ADMIN_ENABLED"] = os.environ.get("RC_ADMIN_ENABLED", "False").lower() in ("1", "true", "yes")


def publication_table_context(ds, q="", year="", dept=""):
    """Everything the shared publications table needs. q / year / dept only set the
    starting values of the controls (so a link like /publications?year=2023 works)."""
    years = ds.years()
    departments = ds.publication_departments()
    return {
        "pub_rows": ds.publication_rows(),
        "pub_years": years,
        "pub_departments": departments,
        "init_q": q,
        "init_year": year if year in [str(y) for y in years] else "",
        "init_dept": dept if dept in departments else "",
    }


# ---------- Dashboard ----------
@app.route("/")
def dashboard():
    ds = Dataset()
    graph = collaboration.build_graph(ds)
    return render_template(
        "index.html",
        stats=analytics.dashboard_stats(ds, graph),
        year_chart=analytics.publications_by_year(ds),
        dept_chart=analytics.publications_by_department(ds),
        keyword_chart=analytics.top_keywords(ds, 10),
        year_missing=analytics.data_coverage(ds)["papers_without_year"],
        recent=ds.recent_papers(5),
        warnings=ds.warnings,
        **publication_table_context(ds),
    )


# ---------- Faculty directory ----------
@app.route("/faculty")
def faculty_list():
    ds = Dataset()
    q = request.args.get("q", "").strip()
    dept = request.args.get("department", "").strip()
    keyword = request.args.get("keyword", "").strip()
    min_papers = faculty_filters.parse_min_papers(request.args.get("min_papers", ""))
    sort = request.args.get("sort", "name")
    if sort not in faculty_filters.SORTS:
        sort = "name"

    people = faculty_filters.filter_faculty(ds, q, dept, keyword, min_papers, sort)
    for f in people:                       # chips shown on each card (see faculty.html)
        f["card_keywords"] = faculty_filters.faculty_keywords(f)
    filters_active = bool(q or dept or keyword or min_papers or sort != "name")

    return render_template("faculty.html", people=people, q=q, dept=dept, keyword=keyword,
                           min_papers=min_papers, sort=sort, sorts=faculty_filters.SORTS,
                           filters_active=filters_active, departments=ds.departments(),
                           keyword_options=faculty_filters.keyword_options(ds),
                           max_papers=max([f["paper_count"] for f in ds.faculty] + [0]),
                           total=len(ds.faculty))


@app.route("/faculty/<faculty_id>")
def faculty_detail(faculty_id):
    ds = Dataset()
    person = ds.faculty_by_id.get(faculty_id)
    if person is None:
        abort(404)
    graph = collaboration.build_graph(ds)
    return render_template("faculty_detail.html", person=person,
                           collaborators=collaboration.collaborators_of(graph, ds, faculty_id))


@app.get("/compare")
def faculty_compare():
    ds = Dataset()
    a = request.args.get("a", "").strip()
    b = request.args.get("b", "").strip()
    result, error = None, ""
    if "a" in request.args or "b" in request.args:
        if not a or not b:
            error = "Select both faculty members to compare."
        elif a not in ds.faculty_by_id or b not in ds.faculty_by_id:
            error = "Unknown faculty selection. Select two known faculty members."
        else:
            result = expertise.compare_faculty(ds, a, b)
    return render_template("compare.html", people=ds.faculty, a=a, b=b,
                           result=result, error=error)


@app.get("/department/<name>")
def department_detail(name):
    summary = analytics.department_summary(Dataset(), name)
    if summary is None:
        abort(404)
    return render_template("department.html", department=summary)


# ---------- Data quality report ----------
@app.route("/data-quality")
def data_quality():
    ds = Dataset()
    report = quality.quality_report(ds)
    issue_count = sum(len(items) for items in report.values())
    return render_template("data_quality.html", report=report, issue_count=issue_count)


# ---------- Publication detail ----------
@app.route("/publications/<paper_id>")
def publication_detail(paper_id):
    ds = Dataset()
    paper = ds.get_paper(paper_id)
    if paper is None:
        abort(404)
    return render_template("paper_detail.html", paper=paper, cite=citations.citations_for(paper))


# ---------- Publications ----------
@app.route("/publications")
def publications():
    ds = Dataset()
    q = request.args.get("q", "").strip()
    year = request.args.get("year", "").strip()
    dept = request.args.get("department", "").strip()
    if not q:                                   # older links used ?keyword=...
        q = request.args.get("keyword", "").strip()
    return render_template("publications.html", **publication_table_context(ds, q, year, dept))


# ---------- Expertise Finder ----------
@app.route("/expertise")
def expertise_finder():
    ds = Dataset()
    q = request.args.get("q", "").strip()
    query_set = expertise.parse_query(q)

    results, unknown = [], []
    if query_set:
        results = expertise.find_matches(query_set, expertise.build_profiles(ds), ds.keyword_labels)
        unknown = sorted(k for k in query_set if k not in ds.keyword_labels)

    return render_template("expertise.html", q=q, searched=bool(query_set), results=results,
                           unknown=unknown, keywords=ds.keyword_options())


# ---------- Collaboration network ----------
@app.route("/network")
def network():
    ds = Dataset()
    raw_year_from = request.args.get("year_from", "").strip()
    raw_year_to = request.args.get("year_to", "").strip()
    raw_min_weight = request.args.get("min_weight", "").strip()

    filter_messages = []
    year_from = None
    year_to = None
    min_weight = 1

    if raw_year_from:
        parsed = clean_year(raw_year_from)
        if parsed is None:
            filter_messages.append("Invalid 'Year from' input; defaulted.")
        else:
            year_from = parsed

    if raw_year_to:
        parsed = clean_year(raw_year_to)
        if parsed is None:
            filter_messages.append("Invalid 'Year to' input; defaulted.")
        else:
            year_to = parsed

    if year_from is not None and year_to is not None and year_from > year_to:
        filter_messages.append("'Year from' cannot be greater than 'Year to'; year filters reset.")
        year_from, year_to = None, None

    if raw_min_weight:
        try:
            mw = int(float(raw_min_weight))
            if mw < 1:
                filter_messages.append("Minimum shared papers must be at least 1; defaulted to 1.")
                min_weight = 1
            else:
                min_weight = mw
        except (ValueError, TypeError):
            filter_messages.append("Invalid minimum shared papers; defaulted to 1.")
            min_weight = 1

    year_filter_active = (year_from is not None) or (year_to is not None)
    graph = collaboration.build_graph(ds, year_from=year_from, year_to=year_to, min_weight=min_weight)
    plot = collaboration.network_for_plot(graph, ds)
    for node in plot["nodes"]:                        # build profile links with url_for
        node["profile"] = url_for("faculty_detail", faculty_id=node["id"])

    centrality = collaboration.centrality_table(graph, ds)

    return render_template(
        "network.html",
        plot=plot,
        stats=collaboration.network_stats(graph, ds),
        centrality=centrality,
        year_from=year_from if year_from is not None else "",
        year_to=year_to if year_to is not None else "",
        min_weight=min_weight,
        year_filter_active=year_filter_active,
        filter_message=" ".join(filter_messages) if filter_messages else "",
    )


# ---------- Export endpoints ----------
@app.route("/export/publications")
@app.route("/publications/export")
def export_publications():
    ds = Dataset()
    q = request.args.get("q", "").strip()
    year = request.args.get("year", "").strip()
    dept = request.args.get("department", "").strip()
    if not q:
        q = request.args.get("keyword", "").strip()
    rows = data_manager.filter_publication_rows(ds.publication_rows(), q=q, year=year, dept=dept)
    csv_bytes = data_manager.publications_to_csv(rows)
    return Response(
        csv_bytes,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="publications.csv"'},
    )


@app.route("/export/network")
@app.route("/network/export")
def export_network():
    ds = Dataset()
    raw_year_from = request.args.get("year_from", "").strip()
    raw_year_to = request.args.get("year_to", "").strip()
    raw_min_weight = request.args.get("min_weight", "").strip()

    year_from = clean_year(raw_year_from) if raw_year_from else None
    year_to = clean_year(raw_year_to) if raw_year_to else None
    if year_from is not None and year_to is not None and year_from > year_to:
        year_from, year_to = None, None

    try:
        min_weight = int(float(raw_min_weight)) if raw_min_weight else 1
        if min_weight < 1:
            min_weight = 1
    except (ValueError, TypeError):
        min_weight = 1

    graph = collaboration.build_graph(ds, year_from=year_from, year_to=year_to, min_weight=min_weight)
    csv_bytes = collaboration.network_to_csv(graph, ds)
    return Response(
        csv_bytes,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="collaboration_network.csv"'},
    )


# ---------- Admin data entry ----------
@app.route("/admin", methods=["GET", "POST"])
def admin_page():
    if not app.config.get("ADMIN_ENABLED", False):
        abort(404)

    env_password = os.environ.get("RC_ADMIN_PASSWORD") or os.environ.get("ADMIN_PASSWORD")
    if not env_password:
        return render_template(
            "admin.html",
            error="Admin password is not configured in the environment.",
            success="",
            faculty=[],
            papers=[],
        ), 403

    ds = Dataset()
    error = ""
    success = ""

    if request.method == "POST":
        entered_password = request.form.get("password", "")
        if entered_password != env_password:
            error = "Invalid admin password."
        else:
            table_type = request.form.get("table_type", "").strip()
            try:
                if table_type == "faculty":
                    row = {col: request.form.get(col, "") for col in data_manager.FACULTY_COLUMNS}
                    ds.add_faculty(row)
                    success = f"Faculty member '{row.get('faculty_id')}' added successfully (backup created)."
                elif table_type == "paper":
                    row = {col: request.form.get(col, "") for col in data_manager.PAPER_COLUMNS}
                    ds.add_paper(row)
                    success = f"Paper '{row.get('paper_id')}' added successfully (backup created)."
                elif table_type == "authorship":
                    row = {col: request.form.get(col, "") for col in data_manager.AUTHORSHIP_COLUMNS}
                    ds.add_authorship(row)
                    success = f"Authorship link ({row.get('paper_id')}, {row.get('faculty_id')}) added successfully (backup created)."
                else:
                    error = "Invalid table type selected."
            except (ValueError, RuntimeError) as exc:
                error = str(exc)

    return render_template(
        "admin.html",
        error=error,
        success=success,
        faculty=ds.faculty,
        papers=ds.papers,
    )


# ---------- Analytics ----------
@app.route("/analytics")
def analytics_page():
    ds = Dataset()
    graph = collaboration.build_graph(ds)
    return render_template(
        "analytics.html",
        year_chart=analytics.publications_by_year(ds),
        dept_chart=analytics.publications_by_department(ds),
        keyword_chart=analytics.top_keywords(ds, 15),
        faculty_chart=analytics.faculty_paper_counts(ds),
        collab=collaboration.network_stats(graph, ds),
        coverage=analytics.data_coverage(ds),
        total_papers=len(ds.papers),
        total_faculty=len(ds.faculty),
    )


# ---------- Saved publications and faculty shortlist ----------
# Which items are saved lives in the visitor's browser (localStorage). The server only
# supplies the details for every paper / faculty member, as JSON, and the page picks out the saved ones.
@app.route("/saved")
def saved_publications():
    ds = Dataset()
    items = []
    for p in ds.papers:
        cite = citations.citations_for(p)
        items.append({
            "id": p["paper_id"], "title": p["title"], "year": p["year_num"] or "",
            "venue": p["venue"], "authors": ", ".join(a["name"] for a in p["authors"]),
            "url": url_for("publication_detail", paper_id=p["paper_id"]), "bibtex": cite["bibtex"],
        })
    return render_template("saved.html", items=items)


@app.route("/shortlist")
def faculty_shortlist():
    ds = Dataset()
    items = [{
        "id": f["faculty_id"], "name": f["name"], "department": f["department"],
        "keywords": faculty_filters.faculty_keywords(f), "papers": f["paper_count"],
        "url": url_for("faculty_detail", faculty_id=f["faculty_id"]),
    } for f in ds.faculty]
    return render_template("shortlist.html", items=items)


@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)
