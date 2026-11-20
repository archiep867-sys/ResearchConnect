/* app.js - small helpers shared by every page:
   toast messages, the saved-papers list, the faculty shortlist, copy buttons, back-to-top.
   Saved papers and the shortlist live in this browser only (localStorage). They hold IDs,
   never data, so the real details always come from the CSV files. */
(function () {
  var KEYS = { papers: "rc.savedPapers", faculty: "rc.shortlist" };
  var memory = { papers: [], faculty: [] };       // fallback when storage is blocked

  function read(kind) {
    try {
      var list = JSON.parse(localStorage.getItem(KEYS[kind]) || "[]");
      return Array.isArray(list) ? list.filter(function (v) { return typeof v === "string"; }) : [];
    } catch (e) { return memory[kind].slice(); }
  }
  function write(kind, list) {
    memory[kind] = list.slice();
    try { localStorage.setItem(KEYS[kind], JSON.stringify(list)); } catch (e) { /* private mode: keep in memory */ }
  }

  var store = {
    list: read,
    has: function (kind, id) { return read(kind).indexOf(id) !== -1; },
    toggle: function (kind, id) {
      var list = read(kind), i = list.indexOf(id);
      if (i === -1) list.push(id); else list.splice(i, 1);
      write(kind, list);
      sync();
      return i === -1;                              // true = now saved
    },
    remove: function (kind, id) { write(kind, read(kind).filter(function (x) { return x !== id; })); sync(); },
    clear: function (kind) { write(kind, []); sync(); }
  };

  // ---- toasts ----
  function toast(message) {
    var box = document.getElementById("rc-toasts");
    if (!box) return;
    var el = document.createElement("div");
    el.className = "rc-toast";
    el.textContent = message;
    box.appendChild(el);
    setTimeout(function () { el.classList.add("rc-toast-out"); }, 2600);
    setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, 3100);
  }

  // ---- copy to clipboard (with a fallback for non-secure pages) ----
  function copyText(text, doneMessage) {
    function done() { toast(doneMessage || "Copied to clipboard"); }
    function fallback() {
      var ta = document.createElement("textarea");
      ta.value = text; ta.setAttribute("readonly", ""); ta.style.position = "fixed"; ta.style.opacity = "0";
      document.body.appendChild(ta); ta.select();
      try { document.execCommand("copy") ? done() : toast("Could not copy. Select the text and copy it manually."); }
      catch (e) { toast("Could not copy. Select the text and copy it manually."); }
      document.body.removeChild(ta);
    }
    if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(text).then(done, fallback);
    else fallback();
  }

  // ---- keep every save / shortlist button and nav badge in step with storage ----
  var LABELS = { papers: ["Save", "Saved"], faculty: ["Shortlist", "Shortlisted"] };
  function sync() {
    document.querySelectorAll("[data-store]").forEach(function (btn) {
      var kind = btn.getAttribute("data-store"), on = store.has(kind, btn.getAttribute("data-id"));
      btn.setAttribute("aria-pressed", on ? "true" : "false");
      btn.classList.toggle("is-on", on);
      var label = btn.querySelector(".store-label");
      if (label) label.textContent = LABELS[kind][on ? 1 : 0];
    });
    ["papers", "faculty"].forEach(function (kind) {
      var n = read(kind).length;
      document.querySelectorAll('[data-count="' + kind + '"]').forEach(function (b) { b.textContent = n; b.hidden = n === 0; });
    });
  }

  document.addEventListener("click", function (e) {
    var btn = e.target.closest("[data-store]");
    if (btn) {
      var kind = btn.getAttribute("data-store"), nowOn = store.toggle(kind, btn.getAttribute("data-id"));
      var what = kind === "papers" ? "Saved publications" : "faculty shortlist";
      toast(nowOn ? "Added to " + (kind === "papers" ? "saved publications" : "your shortlist")
                  : "Removed from " + (kind === "papers" ? "saved publications" : "your shortlist"));
      document.dispatchEvent(new CustomEvent("rc:store", { detail: { kind: kind, what: what } }));
      return;
    }
    var copy = e.target.closest("[data-copy]");
    if (copy) {
      var target = document.getElementById(copy.getAttribute("data-copy"));
      if (target) copyText(target.textContent.trim(), copy.getAttribute("data-copied") || "Copied to clipboard");
    }
  });

  // ---- back to top ----
  var top = document.getElementById("rc-top");
  if (top) {
    window.addEventListener("scroll", function () { top.hidden = window.scrollY < 600; }, { passive: true });
    top.addEventListener("click", function () { window.scrollTo({ top: 0, behavior: "smooth" }); });
  }

  window.RC = { store: store, toast: toast, copyText: copyText };
  sync();
})();
