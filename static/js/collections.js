/* collections.js - draws the "Saved publications" and "Faculty shortlist" pages.
   The server embeds a small JSON list of every paper / faculty member (id -> details).
   This file keeps only the ones whose IDs are in this browser's saved list. */
(function () {
  var dataEl = document.getElementById("rc-data"), root = document.getElementById("rc-collection");
  if (!dataEl || !root || !window.RC) return;
  var kind = root.getAttribute("data-kind");
  var all = JSON.parse(dataEl.textContent);

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  }
  function link(text, href, cls) { var a = el("a", cls, text); a.href = href; return a; }

  function selected() {
    var ids = RC.store.list(kind), byId = {};
    all.forEach(function (item) { byId[item.id] = item; });
    return ids.filter(function (id) { return byId[id]; }).map(function (id) { return byId[id]; });
  }

  function removeButton(item, label) {
    var b = el("button", "btn rc-btn-ghost btn-sm", label);
    b.type = "button";
    b.addEventListener("click", function () { RC.store.remove(kind, item.id); RC.toast("Removed"); render(); });
    return b;
  }

  function paperCard(p) {
    var card = el("article", "rc-card");
    card.appendChild(el("div", "paper-year", p.year || "Year not listed"));
    var h = el("h3", "paper-title"); h.appendChild(link(p.title, p.url)); card.appendChild(h);
    card.appendChild(el("p", "paper-meta", p.venue || "Venue not listed"));
    if (p.authors) card.appendChild(el("p", "paper-meta", "VJTI faculty: " + p.authors));
    var row = el("div", "d-flex flex-wrap gap-2 mt-2");
    row.appendChild(removeButton(p, "Remove"));
    card.appendChild(row);
    return card;
  }

  function facultyCard(f) {
    var card = el("article", "rc-card h-100");
    var h = el("h3", "faculty-name"); h.appendChild(link(f.name, f.url)); card.appendChild(h);
    card.appendChild(el("p", "muted mb-2", f.department || "Department not listed"));
    var chips = el("div", "mb-2");
    (f.keywords.length ? f.keywords.slice(0, 6) : []).forEach(function (k) { chips.appendChild(el("span", "chip", k)); });
    if (!f.keywords.length) chips.appendChild(el("span", "muted small", "No keywords listed"));
    card.appendChild(chips);
    card.appendChild(el("p", "count-line", f.papers + (f.papers === 1 ? " paper" : " papers")));
    card.appendChild(removeButton(f, "Remove"));
    return card;
  }

  function renderCompare(items) {
    var box = document.getElementById("rc-compare");
    if (!box) return;
    box.hidden = items.length < 2;
    if (items.length < 2) return;
    ["a", "b"].forEach(function (key, idx) {
      var sel = document.getElementById("cmp-" + key), keep = sel.value;
      sel.innerHTML = "";
      items.forEach(function (f, i) {
        var o = el("option", "", f.name); o.value = f.id;
        if (keep ? keep === f.id : i === idx) o.selected = true;
        sel.appendChild(o);
      });
    });
  }

  function render() {
    var items = selected(), list = document.getElementById("rc-items"), empty = document.getElementById("rc-none");
    list.innerHTML = "";
    empty.hidden = items.length > 0;
    document.getElementById("rc-tools").hidden = items.length === 0;
    document.getElementById("rc-total").textContent = items.length + (items.length === 1 ? " item" : " items");
    items.forEach(function (item) {
      if (kind === "papers") list.appendChild(paperCard(item));
      else { var col = el("div", "col-md-6 col-xl-4"); col.appendChild(facultyCard(item)); list.appendChild(col); }
    });
    if (kind === "faculty") renderCompare(items);
  }

  // ---- toolbar actions ----
  var clear = document.getElementById("rc-clear");
  clear.addEventListener("click", function () {
    if (window.confirm("Remove everything from this list? This only affects this browser.")) {
      RC.store.clear(kind); RC.toast("List cleared"); render();
    }
  });
  var copyBib = document.getElementById("rc-copy-bib"), dlBib = document.getElementById("rc-download-bib");
  function bibText() { return selected().map(function (p) { return p.bibtex; }).join("\n\n") + "\n"; }
  if (copyBib) copyBib.addEventListener("click", function () { RC.copyText(bibText(), "BibTeX copied"); });
  if (dlBib) dlBib.addEventListener("click", function () {
    var blob = new Blob([bibText()], { type: "text/plain" }), a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = "researchconnect-saved.bib";
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
    RC.toast("Downloaded researchconnect-saved.bib");
  });

  render();
})();
