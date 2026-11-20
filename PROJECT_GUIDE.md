# ResearchConnect: project guide for the viva

## Run it
    pip install -r requirements.txt
    python app.py          # open http://127.0.0.1:5000

Keep `faculty.csv`, `papers.csv`, `authorship.csv` next to `app.py`, and your images in `static/images/`
(`logo.png`, `background.png`). The app only reads the CSV files. It never writes to them.
Plotly is used as **Plotly.js** loaded from a CDN, so the Python `plotly` package is not needed, but the
browser needs internet access to load Plotly, Bootstrap and the fonts.

## How the pieces fit
    Browser  ->  app.py (route)  ->  algorithms/*.py (logic)  ->  template (HTML)  ->  Browser

| File | Job |
|---|---|
| `app.py` | One function per page (route). Reads the search box/filters, calls the algorithms, renders a template. |
| `algorithms/data_manager.py` | Reads the 3 CSVs with pandas, cleans blanks/years/keywords/URLs, links papers to faculty through `authorship.csv`. |
| `algorithms/expertise.py` | Keyword sets and Jaccard similarity. |
| `algorithms/collaboration.py` | Builds the NetworkX graph from shared papers only. |
| `algorithms/faculty_filters.py` | Faculty search, department / keyword / minimum-papers filters and sorting. |
| `algorithms/citations.py` | APA, IEEE and BibTeX text built from paper data (VJTI authors only, nothing invented). |
| `algorithms/analytics.py` | Counts papers by year, department, keyword and faculty. |
| `templates/` | Jinja HTML. `base.html` holds the top navigation; `_macros.html` holds reusable pieces (empty state, paper card). |
| `static/css/style.css` | Navy and violet theme. |
| `static/js/app.js`, `collections.js` | Toasts, copy buttons, back-to-top, and the Saved / Shortlist lists (browser `localStorage`, IDs only). |
| `static/js/charts.js`, `network.js` | Draw the charts and the clickable network with Plotly.js. |

## The two algorithms
**Jaccard similarity**: `J(A,B) = |A ∩ B| / |A ∪ B| × 100`.
A is the set of keywords typed in the search box. B is one faculty member's keyword set
(their listed expertise plus the keywords of their own papers). Python's `&` and `|` operators on sets
give the intersection and union directly. Example: A = {ai, iot}, B = {ai, robotics, vision}:
intersection = 1, union = 4, so J = 25%.

**Collaboration graph**: one node per faculty member. For every paper, `itertools.combinations` makes each pair
of its VJTI authors, and each pair becomes an edge. If the pair already has an edge, its `weight` goes up by 1.
Keywords are never used here.

## Likely viva questions
- **Why is the network empty?** Every paper in `authorship.csv` currently has one VJTI author. An edge needs
  two VJTI authors on one paper. Adding such rows makes edges appear with no code change.
- **Why do keyword results not prove collaboration?** Jaccard compares word lists. Two people can share topics
  without ever co-authoring. That is why the two features are kept separate.
- **Where does a faculty member's keyword set come from when `expertise` is blank?** From the keywords of their
  own papers in `papers.csv`. Nothing is typed in by hand, and the page says where each list comes from.
- **Why CSV and not a database?** The dataset is small, CSV is easy to inspect and edit, and pandas reads it in one line.
- **Why is a `Dataset` object built on every request?** The files are tiny, and it means edits to the CSVs show up
  after a browser refresh without restarting Flask.
- **What happens with bad data?** Blank cells stay blank and the page says "not listed". Authorship rows pointing
  to unknown IDs are skipped and reported on the dashboard. Only `http(s)` links are ever rendered.

## Saved papers and shortlist (new)
- **Where is the list stored?** In the visitor's browser (`localStorage`), as a list of IDs only. The server never
  writes anything, which keeps the "app only reads the CSV files" rule true.
- **Why are citations incomplete?** `authorship.csv` omits external co-authors on purpose, so citations list VJTI
  faculty only and the page says so. Blank year / venue / DOI are left out (year shows `n.d.`), never guessed.
- **Why is there no collaboration path finder?** Every paper has one VJTI author, so the graph has no edges and a
  path finder could only answer "no path". Add multi-author rows to `authorship.csv` first.
