/* publications.js - live search and filters for the publications table.
   The server renders every paper as a table row. This file only shows or hides rows:
   a row is visible when it passes ALL THREE tests (search words, year, department). */
(function () {
  // ---- pure logic (no page access, so it is easy to test) ----
  function normalise(text) {
    return (text || "").toLowerCase().replace(/\s+/g, " ").trim();
  }

  // row = {text, year, depts[]}; state = {query, year, dept}
  function matches(row, state) {
    var words = normalise(state.query).split(" ").filter(Boolean);
    for (var i = 0; i < words.length; i++) {            // every typed word must appear somewhere
      if (row.text.indexOf(words[i]) === -1) return false;
    }
    if (state.year && row.year !== state.year) return false;
    if (state.dept && row.depts.indexOf(state.dept) === -1) return false;
    return true;
  }

  window.RCPublications = { normalise: normalise, matches: matches };

  // ---- connect the logic to the page ----
  var root = document.querySelector("[data-pub-table]");
  if (!root) return;

  var input = root.querySelector("#pub-search"), clearBtn = root.querySelector("#pub-clear");
  var yearSel = root.querySelector("#pub-year"), deptSel = root.querySelector("#pub-dept");
  var resetBtn = root.querySelector("#pub-reset"), emptyReset = root.querySelector("#pub-empty-reset");
  var exportBtn = root.querySelector("#pub-export");
  var countEl = root.querySelector("#pub-count"), emptyBox = root.querySelector("#pub-empty");
  var wrap = root.querySelector("#pub-table-wrap");

  var trs = Array.prototype.slice.call(root.querySelectorAll("tbody tr"));
  var rows = trs.map(function (tr) {
    var depts = [];
    try { depts = JSON.parse(tr.getAttribute("data-depts") || "[]"); } catch (e) {}
    return { el: tr, text: tr.getAttribute("data-search") || "", year: tr.getAttribute("data-year") || "", depts: depts };
  });

  function apply() {
    var state = { query: input.value, year: yearSel.value, dept: deptSel.value };
    var shown = 0;
    rows.forEach(function (row) {
      var ok = matches(row, state);
      row.el.hidden = !ok;
      row.el.classList.toggle("row-alt", ok && shown % 2 === 1);   // zebra stripes among visible rows only
      if (ok) shown++;
    });
    countEl.textContent = "Showing " + shown + " of " + rows.length + (rows.length === 1 ? " publication" : " publications");
    clearBtn.hidden = input.value === "";
    emptyBox.hidden = shown !== 0;
    wrap.hidden = shown === 0;
    if (exportBtn) {
      var params = [];
      if (input.value) params.push("q=" + encodeURIComponent(input.value));
      if (yearSel.value) params.push("year=" + encodeURIComponent(yearSel.value));
      if (deptSel.value) params.push("department=" + encodeURIComponent(deptSel.value));
      exportBtn.href = "/export/publications" + (params.length ? "?" + params.join("&") : "");
    }
  }

  function resetAll() {
    input.value = ""; yearSel.value = ""; deptSel.value = "";
    apply();
  }

  input.addEventListener("input", apply);
  yearSel.addEventListener("change", apply);
  deptSel.addEventListener("change", apply);
  clearBtn.addEventListener("click", function () { input.value = ""; apply(); input.focus(); });
  resetBtn.addEventListener("click", resetAll);
  emptyReset.addEventListener("click", resetAll);
  input.addEventListener("keydown", function (e) { if (e.key === "Escape" && input.value) { input.value = ""; apply(); } });

  apply();
})();
