"use strict";

/* ═══════════════════════════════════════════════════════════════════════
   Kiroku Viewer — P2.2 Interactive SPA
   Zero dependencies. No innerHTML with memory data.
   ═══════════════════════════════════════════════════════════════════════ */

/* ── API Client ──────────────────────────── */

const API = {
  async get(path) {
    const res = await fetch(path);
    if (!res.ok) {
      let msg = `HTTP ${res.status}`;
      try { const e = await res.json(); msg = e.error.message; } catch (_) {}
      throw new Error(msg);
    }
    return res.json();
  },

  meta()       { return this.get("/api/v1/meta"); },
  records(qs)  { return this.get("/api/v1/records" + (qs ? "?" + qs : "")); },
  record(id)   { return this.get("/api/v1/records/" + encodeURIComponent(id)); },
  sources(qs)  { return this.get("/api/v1/sources" + (qs ? "?" + qs : "")); },
  source(id)   { return this.get("/api/v1/sources/" + encodeURIComponent(id)); },
  runs(qs)     { return this.get("/api/v1/runs" + (qs ? "?" + qs : "")); },
  run(id)      { return this.get("/api/v1/runs/" + encodeURIComponent(id)); },
};

/* ── DOM Helpers ──────────────────────────── */

const dom = {
  el(tag, attrs, ...children) {
    const node = document.createElement(tag);
    if (attrs) for (const [k, v] of Object.entries(attrs)) {
      if (k === "className") node.className = v;
      else if (k === "textContent") node.textContent = v;
      else if (k === "href") node.setAttribute("href", v);
      else if (k === "id") node.id = v;
      else if (k === "htmlFor") node.setAttribute("for", v);
      else if (k === "type") node.type = v;
      else if (k === "placeholder") node.placeholder = v;
      else if (k === "value") node.value = v;
      else if (k === "tabIndex") node.tabIndex = v;
      else if (k === "name") node.name = v;
      else if (k === "role") node.setAttribute("role", v);
      else if (k === "aria") for (const [ak, av] of Object.entries(v)) node.setAttribute("aria-" + ak, av);
      else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2).toLowerCase(), v);
      else if (k === "disabled") { if (v) node.setAttribute("disabled", ""); }
      else node.setAttribute(k, v);
    }
    for (const child of children) {
      if (child != null && child !== false) node.appendChild(
        typeof child === "string" ? document.createTextNode(child) : child
      );
    }
    return node;
  },

  clear(node) { while (node.firstChild) node.removeChild(node.firstChild); },

  badge(text, cls) { return dom.el("span", { className: "badge " + cls, textContent: text }); },
  tagE(text) { return dom.el("span", { className: "tag", textContent: text }); },
};

/* ── Router ───────────────────────────────── */

const Router = {
  _routes: [],
  _rendering: false,
  on(pattern, handler) { this._routes.push({ pattern, handler }); },

  dispatch() {
    if (this._rendering) return;
    this._rendering = true;
    try {
      renderNav();
      const path = window.location.pathname;
      for (const { pattern, handler } of this._routes) {
        const match = path.match(pattern);
        if (match) return handler(match.slice(1));
      }
      this.show404();
    } finally {
      this._rendering = false;
    }
  },

  navigate(url) {
    history.pushState(null, "", url);
    this.dispatch();
  },

  syncURL(url) {
    history.replaceState(null, "", url);
  },

  show404() {
    const m = document.getElementById("viewer-main");
    dom.clear(m);
    m.appendChild(dom.el("div", { className: "state-msg" },
      dom.el("div", { className: "icon", textContent: "404" }),
      dom.el("p", { textContent: "Page not found." }),
      dom.el("a", { href: "/", textContent: "Return to dashboard", onClick: (e) => { e.preventDefault(); Router.navigate("/"); } }),
    ));
  },
};

window.addEventListener("popstate", () => Router.dispatch());

/* ── Navigation ───────────────────────────── */

function renderNav() {
  const nav = document.getElementById("top-nav");
  dom.clear(nav);

  nav.appendChild(dom.el("a", { className: "brand", href: "/", textContent: "Kiroku Viewer", onClick: (e) => { e.preventDefault(); Router.navigate("/"); } }));

  const links = [
    ["/records", "Records"],
    ["/sources", "Sources"],
    ["/runs", "Runs"],
  ];
  for (const [url, label] of links) {
    const a = dom.el("a", { href: url, textContent: label, onClick: (e) => { e.preventDefault(); Router.navigate(url); } });
    if (window.location.pathname === url || window.location.pathname.startsWith(url + "/")) {
      a.setAttribute("aria-current", "page");
    }
    nav.appendChild(a);
  }
}

/* ── Shared state ─────────────────────────── */

let _metaCache = null;

async function loadMeta() {
  if (!_metaCache) _metaCache = await API.meta();
  return _metaCache;
}

function badgeStatus(status) {
  const map = { active: "badge-active", completed: "badge-completed", proposed: "badge-proposed", superseded: "badge-superseded" };
  return dom.badge(status, map[status] || "badge-proposed");
}

function badgeVerification(vs) {
  const map = { verified: "badge-verified", unverified: "badge-unverified" };
  return dom.badge(vs, map[vs] || "badge-proposed");
}

function badgeConfidence(conf) {
  const map = { confirmed: "badge-confirmed" };
  return dom.badge(conf, map[conf] || "badge-medium");
}

/* ── Pagination Component ─────────────────── */

function renderPagination(page, onPage) {
  if (!page || page.total <= page.limit) return dom.el("div");
  const totalPages = Math.ceil(page.total / page.limit);
  const current = Math.floor(page.offset / page.limit) + 1;
  const div = dom.el("div", { className: "pagination" },
    dom.el("button", { textContent: "‹ Prev", disabled: page.offset === 0, onClick: () => onPage(page.offset - page.limit) }),
    dom.el("span", { textContent: "Page " + current + " of " + totalPages + " (" + page.total + " total)" }),
    dom.el("button", { textContent: "Next ›", disabled: page.offset + page.limit >= page.total, onClick: () => onPage(page.offset + page.limit) }),
  );
  return div;
}

/* ── Dashboard ────────────────────────────── */

async function renderDashboard() {
  const m = document.getElementById("viewer-main");
  dom.clear(m);
  m.appendChild(loadingMsg());

  try {
    const meta = await loadMeta();
    const p = meta.data.project;
    const c = meta.data.counts;

    dom.clear(m);
    m.appendChild(dom.el("div", { className: "page-header" },
      dom.el("h1", { textContent: p.name }),
      dom.el("div", { className: "subtitle", textContent: p.domain + "  ·  " + p.status }),
    ));

    m.appendChild(dom.el("div", { className: "info-block" },
      dom.el("h3", { textContent: "Goal" }),
      dom.el("p", { className: "goal-text", textContent: p.goal }),
    ));

    if (p.scope && p.scope.length) {
      m.appendChild(dom.el("div", { className: "info-block" },
        dom.el("h3", { textContent: "Scope" }),
        dom.el("div", null, ...p.scope.map(function(s) { return dom.tagE(s); })),
      ));
    }

    m.appendChild(dom.el("h2", { className: "section-heading", textContent: "Overview" }));
    m.appendChild(dom.el("div", { className: "stats-grid" },
      statCard(c.records, "Records"),
      statCard(c.sources, "Sources"),
      statCard(c.runs, "Runs"),
      statCard(meta.data.validation_warnings.length, "Warnings"),
    ));

    m.appendChild(distributionBlock("By Type", c.by_type));
    m.appendChild(distributionBlock("By Status", c.by_status));
    m.appendChild(distributionBlock("By Verification", c.by_verification_status));

    if (meta.data.validation_warnings.length) {
      m.appendChild(dom.el("div", { className: "warning-banner" },
        dom.el("strong", { textContent: "Validation Warnings: " }),
        ...meta.data.validation_warnings.map(function(w) { return dom.el("div", { textContent: w }); }),
      ));
    }
  } catch (err) {
    showError(m, err);
  }
}

function statCard(value, label) {
  return dom.el("div", { className: "stat-card" },
    dom.el("div", { className: "stat-value", textContent: String(value) }),
    dom.el("div", { className: "stat-label", textContent: label }),
  );
}

function distributionBlock(title, dist) {
  return dom.el("div", { className: "info-block" },
    dom.el("h3", { textContent: title }),
    dom.el("div", { className: "distribution-list" },
      ...Object.entries(dist || {}).map(function(entry) {
        return dom.el("div", null, dom.el("span", { textContent: String(entry[1]) }), " " + entry[0]);
      }),
    ),
  );
}

/* ── Record Explorer ──────────────────────── */

async function renderRecordExplorer() {
  var m = document.getElementById("viewer-main");
  dom.clear(m);
  m.appendChild(loadingMsg());

  try {
    var meta = await loadMeta();
    var sf = meta.data.supported_filters;
    var params = new URLSearchParams(window.location.search);

    dom.clear(m);
    m.appendChild(dom.el("div", { className: "page-header" },
      dom.el("h1", { textContent: "Records" }),
    ));

    /* Filter bar with all supported filters */
    var filterBar = dom.el("div", { className: "filter-bar" });

    var searchId = "flt-search"; var keyId = "flt-key";
    var typeId = "flt-type"; var statusId = "flt-status";
    var tagId = "flt-tag"; var scopeId = "flt-scope"; var confId = "flt-confidence";
    var verifId = "flt-verification"; var relationTargetId = "flt-relation-target";
    var relationTypeId = "flt-relation-type"; var sortId = "flt-sort";
    var sortDirId = "flt-sortdir";

    var search = dom.el("input", {
      id: searchId,
      name: "search",
      type: "search",
      placeholder: "Search records…",
      value: params.get("search") || "",
    });
    var keyInp = dom.el("input", {
      id: keyId,
      name: "key",
      type: "text",
      placeholder: "Exact record key",
      value: params.get("key") || "",
    });
    var tagInp = dom.el("input", {
      id: tagId,
      name: "tag",
      type: "text",
      placeholder: "Tag",
      value: params.get("tag") || "",
    });
    var scopeInp = dom.el("input", {
      id: scopeId,
      name: "scope",
      type: "text",
      placeholder: "Scope",
      value: params.get("scope") || "",
    });
    var typeSel = selectFilter(
      typeId, "type", params.get("type") || "", sf.types
    );
    var statusSel = selectFilter(
      statusId, "status", params.get("status") || "", sf.statuses
    );
    var confSel = selectFilter(
      confId, "confidence", params.get("confidence") || "", sf.confidence
    );
    var verifSel = selectFilter(
      verifId,
      "verification_status",
      params.get("verification_status") || "",
      sf.verification_statuses
    );
    var relationTargetInp = dom.el("input", {
      id: relationTargetId,
      name: "relation_target",
      type: "text",
      placeholder: "Target record ID or key",
      value: params.get("relation_target") || "",
    });
    var relationTypeSel = selectFilter(
      relationTypeId,
      "relation_type",
      params.get("relation_type") || "",
      sf.relation_types
    );
    var sortSel = selectFilter(
      sortId, "sort", params.get("sort") || "title", sf.sort_fields
    );
    var sortDirSel = selectFilter(
      sortDirId,
      "sort_dir",
      params.get("sort_dir") || "asc",
      sf.sort_directions
    );

    var applyBtn = dom.el("button", { className: "btn-primary", textContent: "Apply" });
    var resetBtn = dom.el("button", { className: "btn-secondary", textContent: "Reset", onClick: function() { Router.navigate("/records"); } });

    filterBar.appendChild(labelInput(searchId, "Search"));
    filterBar.appendChild(search);
    filterBar.appendChild(labelInput(keyId, "Key"));
    filterBar.appendChild(keyInp);
    filterBar.appendChild(labelInput(typeId, "Type"));
    filterBar.appendChild(typeSel);
    filterBar.appendChild(labelInput(statusId, "Status"));
    filterBar.appendChild(statusSel);
    filterBar.appendChild(labelInput(tagId, "Tag"));
    filterBar.appendChild(tagInp);
    filterBar.appendChild(labelInput(scopeId, "Scope"));
    filterBar.appendChild(scopeInp);
    filterBar.appendChild(labelInput(confId, "Confidence"));
    filterBar.appendChild(confSel);
    filterBar.appendChild(labelInput(verifId, "Verification"));
    filterBar.appendChild(verifSel);
    filterBar.appendChild(labelInput(relationTargetId, "Relation target"));
    filterBar.appendChild(relationTargetInp);
    filterBar.appendChild(labelInput(relationTypeId, "Relation type"));
    filterBar.appendChild(relationTypeSel);
    filterBar.appendChild(labelInput(sortId, "Sort"));
    filterBar.appendChild(sortSel);
    filterBar.appendChild(sortDirSel);
    filterBar.appendChild(applyBtn);
    filterBar.appendChild(resetBtn);
    m.appendChild(filterBar);

    var activeFilters = [
      searchId, keyId, typeId, statusId, tagId, scopeId, confId, verifId,
      relationTargetId, relationTypeId, sortId, sortDirId
    ];
    function buildQuery(offset) {
      var q = new URLSearchParams();
      for (var i = 0; i < activeFilters.length; i++) {
        var el = document.getElementById(activeFilters[i]);
        if (el && el.value) q.set(el.name || activeFilters[i].replace("flt-", ""), el.value);
      }
      q.set("offset", String(offset));
      q.set("limit", "50");
      return q.toString();
    }

    var resultsArea = dom.el("div");
    m.appendChild(resultsArea);

    var state = {
      container: resultsArea,
      meta: meta,
      buildQuery: buildQuery,
    };

    applyBtn.addEventListener("click", function() { loadExplorerData(state, 0); });
    var textFilters = [search, keyInp, tagInp, scopeInp, relationTargetInp];
    for (var textIndex = 0; textIndex < textFilters.length; textIndex++) {
      textFilters[textIndex].addEventListener("keydown", function(e) {
        if (e.key === "Enter") loadExplorerData(state, 0);
      });
    }
    var initOffset = parseInt(params.get("offset") || "0");
    loadExplorerData(state, initOffset);
  } catch (err) {
    showError(m, err);
  }
}

function labelInput(forId, text) {
  return dom.el("label", { className: "filter-label", htmlFor: forId, textContent: text });
}

function loadExplorerData(state, offset) {
  var q = state.buildQuery(offset);
  Router.syncURL("/records?" + q);
  var area = state.container;
  dom.clear(area);
  area.appendChild(loadingMsg());
  API.records(q).then(function(data) {
    renderResults(area, data, function(newOffset) { loadExplorerData(state, newOffset); }, state.meta);
  }).catch(function(err) {
    dom.clear(area);
    area.appendChild(dom.el("div", { className: "error-banner", textContent: err.message }));
  });
}

function selectFilter(id, name, value, options) {
  var sel = dom.el("select", { id: id, name: name });
  sel.appendChild(dom.el("option", { value: "", textContent: "Any" }));
  for (var i = 0; i < options.length; i++) {
    var opt = options[i];
    var o = dom.el("option", { value: opt, textContent: opt });
    if (opt === value) o.setAttribute("selected", "");
    sel.appendChild(o);
  }
  return sel;
}

/* sortable columns: only those supported by core */
var SORTABLE_COLUMNS = { title: 1, type: 1, status: 1 };

function renderResults(area, data, onPage, meta) {
  dom.clear(area);

  if (!data.data || !data.data.length) {
    area.appendChild(dom.el("div", { className: "state-msg" },
      dom.el("div", { className: "icon", textContent: "\u2205" }),
      dom.el("p", { textContent: "No records match the current filters." }),
    ));
    return;
  }

  var tbl = dom.el("table", { className: "result-table" });
  var thead = dom.el("thead");
  var headerRow = dom.el("tr");

  var columns = [
    ["Title", "title"],
    ["Type", "type"],
    ["Status", "status"],
    ["Scope", null],
    ["Verification", null],
  ];
  for (var i = 0; i < columns.length; i++) {
    var col = columns[i][0];
    var field = columns[i][1];
    if (field && SORTABLE_COLUMNS[field]) {
      var btn = dom.el("button", {
        className: "th-btn",
        textContent: col,
        tabIndex: 0,
        onClick: function(f) { return function() {
          var params = new URLSearchParams(window.location.search);
          if (params.get("sort") === f) {
            params.set("sort_dir", params.get("sort_dir") === "asc" ? "desc" : "asc");
          } else {
            params.set("sort", f);
            params.set("sort_dir", "asc");
          }
          params.set("offset", "0");
          Router.navigate("/records?" + params.toString());
        }; }(field),
      });
      headerRow.appendChild(dom.el("th", null, btn));
    } else {
      headerRow.appendChild(dom.el("th", { textContent: col }));
    }
  }
  thead.appendChild(headerRow);
  tbl.appendChild(thead);

  var tbody = dom.el("tbody");
  for (var j = 0; j < data.data.length; j++) {
    var r = data.data[j];
    var tr = dom.el("tr");
    tr.appendChild(dom.el("td", null,
      dom.el("a", { href: "/records/" + r.id, textContent: r.title, onClick: (function(id) { return function(e) { e.preventDefault(); Router.navigate("/records/" + id); }; })(r.id) }),
      dom.el("br"),
      dom.el("small", { className: "muted", textContent: r.summary }),
    ));
    tr.appendChild(dom.el("td", null, dom.el("code", { className: "code-sm", textContent: r.type })));
    tr.appendChild(dom.el("td", null, badgeStatus(r.status)));
    tr.appendChild(dom.el("td", null, ...(r.scope || []).map(function(s) { return dom.tagE(s); })));
    tr.appendChild(dom.el("td", null, badgeVerification(r.verification_status)));
    tbody.appendChild(tr);
  }
  tbl.appendChild(tbody);
  area.appendChild(tbl);
  area.appendChild(renderPagination(data.page, onPage));
}

/* ── Record Detail ────────────────────────── */

async function renderRecordDetail(recordId) {
  var m = document.getElementById("viewer-main");
  dom.clear(m);
  m.appendChild(loadingMsg());

  try {
    var data = await API.record(recordId);
    var r = data.data.record;
    dom.clear(m);

    m.appendChild(dom.el("div", { className: "page-header" },
      dom.el("h1", { textContent: r.title }),
      dom.el("div", { className: "subtitle" }, badgeStatus(r.status), " ", badgeConfidence(r.confidence), " ", badgeVerification(r.verification_status)),
    ));

    m.appendChild(dom.el("p", { className: "detail-summary", textContent: r.summary }));

    /* Envelope */
    m.appendChild(detailSection("Envelope", kvGrid([
      ["ID", dom.el("code", { className: "code-sm", textContent: r.id })],
      ["Key", dom.el("code", { className: "code-sm", textContent: r.key })],
      ["Type", dom.el("code", { className: "code-sm", textContent: r.type })],
      ["Status", String(r.status)],
      ["Confidence", String(r.confidence)],
      ["Verification", String(r.verification_status)],
      ["Scope", dom.el("div", null, ...(r.scope || []).map(function(s) { return dom.tagE(s); }))],
      ["Tags", dom.el("div", null, ...(r.tags || []).map(function(t) { return dom.tagE(t); }))],
      ["Created", String(r.created_at)],
      ["Updated", String(r.updated_at)],
      ["Generated by", dom.el("a", { href: "/runs/" + r.generated_by, textContent: r.generated_by, onClick: (function(id) { return function(e) { e.preventDefault(); Router.navigate("/runs/" + id); }; })(r.generated_by) })],
    ])));

    /* Payload */
    m.appendChild(detailSection("Payload", renderPayload(r.payload)));

    /* Evidence with locator, target, observed_at */
    if (r.evidence && r.evidence.length) {
      var evSection = dom.el("div", { className: "detail-section" });
      evSection.appendChild(dom.el("h2", { textContent: "Evidence (" + r.evidence.length + ")" }));
      for (var i = 0; i < r.evidence.length; i++) {
        var ev = r.evidence[i];
        var src = (data.data.evidence_sources || []).find(function(s) { return s.id === ev.source_id; });
        var evDiv = dom.el("div", { className: "evidence-item" });

        evDiv.appendChild(dom.el("div", { className: "evidence-header" },
          dom.el("strong", { textContent: ev.relation }),
          " via ", dom.el("em", { textContent: ev.method }),
        ));

        evDiv.appendChild(dom.el("div", { className: "evidence-source" },
          dom.el("span", { textContent: "Source: " }),
          dom.el("a", { href: "/sources/" + ev.source_id, textContent: (src ? src.title : ev.source_id), onClick: (function(id) { return function(e) { e.preventDefault(); Router.navigate("/sources/" + id); }; })(ev.source_id) }),
          dom.el("code", { className: "code-xs", textContent: " " + ev.source_id }),
        ));

        if (ev.target) {
          evDiv.appendChild(dom.el("div", { className: "evidence-meta" },
            dom.el("span", { className: "kv-label", textContent: "Target: " }),
            dom.el("code", { className: "code-xs", textContent: ev.target }),
          ));
        }

        if (ev.locator) {
          evDiv.appendChild(dom.el("div", { className: "evidence-meta" },
            dom.el("span", { className: "kv-label", textContent: "Locator: " }),
            dom.el("code", {
              className: "code-xs",
              textContent: formatLocator(ev.locator),
            }),
          ));
        }

        if (ev.observed_at) {
          evDiv.appendChild(dom.el("div", { className: "evidence-meta" },
            dom.el("span", { className: "kv-label", textContent: "Observed: " }),
            dom.el("code", { className: "code-xs", textContent: ev.observed_at }),
          ));
        }

        if (ev.note) {
          evDiv.appendChild(dom.el("div", { className: "evidence-note", textContent: ev.note }));
        }

        evSection.appendChild(evDiv);
      }
      m.appendChild(evSection);
    }

    /* Outgoing relations */
    if (r.relations && r.relations.length) {
      var ol = dom.el("ul", { className: "relation-list" });
      for (var j = 0; j < r.relations.length; j++) {
        var rel = r.relations[j];
        ol.appendChild(dom.el("li", null,
          dom.el("code", { className: "code-sm", textContent: rel.type + " " }),
          dom.el("a", { href: "/records/" + rel.target_id, textContent: rel.target_id, onClick: (function(id) { return function(e) { e.preventDefault(); Router.navigate("/records/" + id); }; })(rel.target_id) }),
          rel.note ? dom.el("span", { className: "muted", textContent: " — " + rel.note }) : null,
        ));
      }
      m.appendChild(detailSection("Outgoing Relations", ol));
    }

    /* Incoming relations */
    if (data.data.incoming_relations && data.data.incoming_relations.length) {
      var il = dom.el("ul", { className: "relation-list" });
      for (var k = 0; k < data.data.incoming_relations.length; k++) {
        var irel = data.data.incoming_relations[k];
        il.appendChild(dom.el("li", null,
          dom.el("code", { className: "code-sm", textContent: irel.type + " " }),
          dom.el("a", { href: "/records/" + irel.source_id, textContent: irel.source_id, onClick: (function(id) { return function(e) { e.preventDefault(); Router.navigate("/records/" + id); }; })(irel.source_id) }),
        ));
      }
      m.appendChild(detailSection("Incoming Relations", il));
    }
  } catch (err) {
    showError(m, err);
  }
}

function renderPayload(payload) {
  var div = dom.el("div");
  var keys = Object.keys(payload);
  for (var i = 0; i < keys.length; i++) {
    var k = keys[i];
    var v = payload[k];
    var label = k.replace(/_/g, " ").replace(/\b\w/g, function(l) { return l.toUpperCase(); });
    if (Array.isArray(v)) {
      div.appendChild(dom.el("p", null, dom.el("strong", { textContent: label + ": " })));
      var ul = dom.el("ul", { className: "payload-list" });
      for (var j = 0; j < v.length; j++) {
        var item = v[j];
        ul.appendChild(dom.el("li", { textContent: typeof item === "object" ? JSON.stringify(item) : String(item) }));
      }
      div.appendChild(ul);
    } else if (v != null && typeof v === "object") {
      div.appendChild(dom.el("p", null,
        dom.el("strong", { textContent: label + ": " }),
        dom.el("code", { className: "code-sm", textContent: JSON.stringify(v) }),
      ));
    } else {
      div.appendChild(dom.el("p", { className: "payload-row", textContent: label + ": " + String(v) }));
    }
  }
  return div;
}

function formatLocator(locator) {
  var parts = [locator.kind];
  var fields = [
    "start_line",
    "end_line",
    "message_id",
    "section",
    "selector",
    "command",
    "fragment",
  ];
  for (var i = 0; i < fields.length; i++) {
    var field = fields[i];
    if (locator[field] != null && locator[field] !== "") {
      parts.push(field + "=" + locator[field]);
    }
  }
  return parts.join(" ");
}

function detailSection(title, content) {
  var sec = dom.el("div", { className: "detail-section" });
  sec.appendChild(dom.el("h2", { textContent: title }));
  sec.appendChild(content);
  return sec;
}

function kvGrid(pairs) {
  var grid = dom.el("div", { className: "kv-grid" });
  for (var i = 0; i < pairs.length; i++) {
    grid.appendChild(dom.el("div", { className: "k", textContent: pairs[i][0] }));
    grid.appendChild(dom.el("div", { className: "v" }, pairs[i][1]));
  }
  return grid;
}

/* ── Sources ──────────────────────────────── */

async function renderSources() {
  var m = document.getElementById("viewer-main");
  dom.clear(m);
  m.appendChild(loadingMsg());

  try {
    var params = new URLSearchParams(window.location.search);
    var offset = parseInt(params.get("offset") || "0");
    var data = await API.sources("offset=" + offset + "&limit=50");
    dom.clear(m);

    m.appendChild(dom.el("div", { className: "page-header" },
      dom.el("h1", { textContent: "Sources" }),
    ));

    if (!data.data || !data.data.length) {
      m.appendChild(dom.el("div", { className: "state-msg" },
        dom.el("div", { className: "icon", textContent: "\u2205" }),
        dom.el("p", { textContent: "No sources registered." }),
      ));
      return;
    }

    var tbl = dom.el("table", { className: "result-table" });
    var thead = dom.el("thead");
    var hrow = dom.el("tr");
    var headers = ["Title", "Kind", "URI", "Integrity"];
    for (var i = 0; i < headers.length; i++) hrow.appendChild(dom.el("th", { textContent: headers[i] }));
    thead.appendChild(hrow); tbl.appendChild(thead);

    var tbody = dom.el("tbody");
    for (var j = 0; j < data.data.length; j++) {
      var s = data.data[j];
      var tr = dom.el("tr");
      tr.appendChild(dom.el("td", null,
        dom.el("a", { href: "/sources/" + s.id, textContent: s.title, onClick: (function(id) { return function(e) { e.preventDefault(); Router.navigate("/sources/" + id); }; })(s.id) }),
      ));
      tr.appendChild(dom.el("td", null, dom.el("code", { className: "code-sm", textContent: s.kind })));
      tr.appendChild(dom.el("td", null, dom.el("code", { className: "code-uri", textContent: s.uri })));
      tr.appendChild(dom.el("td", null, dom.el("code", { className: "code-sm", textContent: s.integrity })));
      tbody.appendChild(tr);
    }
    tbl.appendChild(tbody); m.appendChild(tbl);
    m.appendChild(renderPagination(data.page, function(o) { Router.navigate("/sources?offset=" + o); }));
  } catch (err) {
    showError(m, err);
  }
}

async function renderSourceDetail(sourceId) {
  var m = document.getElementById("viewer-main");
  dom.clear(m); m.appendChild(loadingMsg());
  try {
    var data = await API.source(sourceId);
    var s = data.data.source;
    dom.clear(m);

    m.appendChild(dom.el("div", { className: "page-header" },
      dom.el("h1", { textContent: s.title }),
      dom.el("div", { className: "subtitle" }, dom.el("code", { className: "code-sm", textContent: s.id })),
    ));

    m.appendChild(detailSection("Details", kvGrid([
      ["Kind", dom.el("code", { className: "code-sm", textContent: s.kind })],
      ["URI", dom.el("code", { className: "code-sm", textContent: s.uri })],
      ["Revision", dom.el("code", { className: "code-sm", textContent: String(s.revision || "\u2014") })],
      ["Integrity", dom.el("code", { className: "code-sm", textContent: s.integrity })],
      ["Captured", String(s.captured_at || "\u2014")],
    ])));

    if (s.metadata && Object.keys(s.metadata).length) {
      var metaPairs = Object.entries(s.metadata).map(function(entry) { return [entry[0], String(entry[1])]; });
      m.appendChild(detailSection("Metadata", kvGrid(metaPairs)));
    }

    if (data.data.record_ids && data.data.record_ids.length) {
      var ul = dom.el("ul", { className: "relation-list" });
      for (var i = 0; i < data.data.record_ids.length; i++) {
        var rid = data.data.record_ids[i];
        ul.appendChild(dom.el("li", null,
          dom.el("a", { href: "/records/" + rid, textContent: rid, onClick: (function(id) { return function(e) { e.preventDefault(); Router.navigate("/records/" + id); }; })(rid) }),
        ));
      }
      m.appendChild(detailSection("Records Using This Source (" + data.data.record_ids.length + ")", ul));
    }
  } catch (err) { showError(m, err); }
}

/* ── Runs ─────────────────────────────────── */

async function renderRuns() {
  var m = document.getElementById("viewer-main");
  dom.clear(m); m.appendChild(loadingMsg());

  try {
    var params = new URLSearchParams(window.location.search);
    var offset = parseInt(params.get("offset") || "0");
    var data = await API.runs("offset=" + offset + "&limit=50");
    dom.clear(m);

    m.appendChild(dom.el("div", { className: "page-header" },
      dom.el("h1", { textContent: "Runs" }),
    ));

    if (!data.data || !data.data.length) {
      m.appendChild(dom.el("div", { className: "state-msg" },
        dom.el("div", { className: "icon", textContent: "\u2205" }),
        dom.el("p", { textContent: "No runs recorded." }),
      ));
      return;
    }

    var tbl = dom.el("table", { className: "result-table" });
    var thead = dom.el("thead");
    var hrow = dom.el("tr");
    var headers = ["ID", "Operation", "Status", "Actor", "Started", "Summary"];
    for (var i = 0; i < headers.length; i++) hrow.appendChild(dom.el("th", { textContent: headers[i] }));
    thead.appendChild(hrow); tbl.appendChild(thead);

    var tbody = dom.el("tbody");
    for (var j = 0; j < data.data.length; j++) {
      var run = data.data[j];
      var tr = dom.el("tr");
      tr.appendChild(dom.el("td", null,
        dom.el("a", { href: "/runs/" + run.id, textContent: run.id.slice(0, 24) + "\u2026", onClick: (function(id) { return function(e) { e.preventDefault(); Router.navigate("/runs/" + id); }; })(run.id) }),
      ));
      tr.appendChild(dom.el("td", null, dom.el("code", { className: "code-sm", textContent: run.operation })));
      tr.appendChild(dom.el("td", null, badgeStatus(run.status)));
      tr.appendChild(dom.el("td", null, dom.el("code", { className: "code-sm", textContent: run.actor && run.actor.name ? run.actor.name : "\u2014" })));
      tr.appendChild(dom.el("td", null, dom.el("code", { className: "code-sm", textContent: (run.started_at || "").slice(0, 19) })));
      tr.appendChild(dom.el("td", { className: "cell-wrap", textContent: run.summary || "\u2014" }));
      tbody.appendChild(tr);
    }
    tbl.appendChild(tbody); m.appendChild(tbl);
    m.appendChild(renderPagination(data.page, function(o) { Router.navigate("/runs?offset=" + o); }));
  } catch (err) { showError(m, err); }
}

async function renderRunDetail(runId) {
  var m = document.getElementById("viewer-main");
  dom.clear(m); m.appendChild(loadingMsg());
  try {
    var data = await API.run(runId);
    var run = data.data.run;
    dom.clear(m);

    m.appendChild(dom.el("div", { className: "page-header" },
      dom.el("h1", { textContent: "Run Detail" }),
      dom.el("div", { className: "subtitle" }, dom.el("code", { className: "code-sm", textContent: run.id })),
    ));

    m.appendChild(detailSection("Details", kvGrid([
      ["Operation", dom.el("code", { className: "code-sm", textContent: run.operation })],
      ["Status", badgeStatus(run.status)],
      ["Actor", dom.el("code", { className: "code-sm", textContent: (run.actor && run.actor.type ? run.actor.type : "\u2014") + " / " + (run.actor && run.actor.name ? run.actor.name : "\u2014") })],
      ["Started", String(run.started_at || "\u2014")],
      ["Completed", String(run.completed_at || "\u2014")],
      ["Summary", String(run.summary || "\u2014")],
    ])));

    if (run.inputs && run.inputs.length) {
      var ul = dom.el("ul", { className: "relation-list" });
      for (var i = 0; i < run.inputs.length; i++) {
        var srcId = run.inputs[i];
        ul.appendChild(dom.el("li", null,
          dom.el("a", { href: "/sources/" + srcId, textContent: srcId, onClick: (function(id) { return function(e) { e.preventDefault(); Router.navigate("/sources/" + id); }; })(srcId) }),
        ));
      }
      m.appendChild(detailSection("Input Sources (" + run.inputs.length + ")", ul));
    }

    if (run.warnings && run.warnings.length) {
      var wdiv = dom.el("div", { className: "warning-banner" });
      for (var j = 0; j < run.warnings.length; j++) wdiv.appendChild(dom.el("div", { textContent: run.warnings[j] }));
      m.appendChild(detailSection("Warnings", wdiv));
    }

    if (data.data.record_ids && data.data.record_ids.length) {
      var rul = dom.el("ul", { className: "relation-list" });
      for (var k = 0; k < data.data.record_ids.length; k++) {
        var rid = data.data.record_ids[k];
        rul.appendChild(dom.el("li", null,
          dom.el("a", { href: "/records/" + rid, textContent: rid, onClick: (function(id) { return function(e) { e.preventDefault(); Router.navigate("/records/" + id); }; })(rid) }),
        ));
      }
      m.appendChild(detailSection("Records Generated (" + data.data.record_ids.length + ")", rul));
    }
  } catch (err) { showError(m, err); }
}

/* ── Shared Components ────────────────────── */

function loadingMsg() {
  return dom.el("div", { className: "state-msg" },
    dom.el("div", { className: "loading-spinner" }),
    dom.el("p", { textContent: "Loading\u2026" }),
  );
}

function showError(container, err) {
  dom.clear(container);
  container.appendChild(dom.el("div", { className: "state-msg" },
    dom.el("div", { className: "icon", textContent: "!" }),
    dom.el("p", { textContent: err.message || "An unexpected error occurred." }),
    dom.el("a", { href: "/", textContent: "Return to dashboard", onClick: function(e) { e.preventDefault(); Router.navigate("/"); } }),
  ));
}

/* ── Init ─────────────────────────────────── */

Router.on(/^\/$/, function() { renderDashboard(); });
Router.on(/^\/records\/?$/, function() { renderRecordExplorer(); });
Router.on(/^\/records\/(.+)$/, function(m) { renderRecordDetail(m[0]); });
Router.on(/^\/sources\/?$/, function() { renderSources(); });
Router.on(/^\/sources\/(.+)$/, function(m) { renderSourceDetail(m[0]); });
Router.on(/^\/runs\/?$/, function() { renderRuns(); });
Router.on(/^\/runs\/(.+)$/, function(m) { renderRunDetail(m[0]); });

Router.dispatch();
