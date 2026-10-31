/* Boot-chain explorer: compare how boards boot, stage by stage.

   Usage in a page:  <div class="bc" data-src="docs/data/boot-chains.json"></div>
   data-src is relative to the site root. The same JSON draws the static diagram
   (docs/images/_src/boot_compare.py), so the picture and this widget cannot disagree. */
(function () {
  "use strict";
  var ROOT = new URL("../", document.currentScript.src);

  function h(tag, props) {
    var el = document.createElement(tag);
    Object.keys(props || {}).forEach(function (k) {
      var v = props[k];
      if (v == null || v === false) return;
      if (k === "class") el.className = v;
      else if (k === "text") el.textContent = v;
      else if (k.slice(0, 2) === "on") el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? "" : v);
    });
    (function add(list) {
      list.forEach(function (c) {
        if (c == null || c === false) return;
        if (Array.isArray(c)) add(c);
        else el.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
      });
    })(Array.prototype.slice.call(arguments, 2));
    return el;
  }

  function build(host, data) {
    var state = { board: "all", sel: null, hl: null };
    var tabs = h("div", { class: "bc-tabs", role: "group", "aria-label": "Board" });
    var body = h("div", { class: "bc-body" });
    var detail = h("div", { class: "bc-detail", "aria-live": "polite" });
    host.textContent = "";
    host.appendChild(tabs); host.appendChild(body); host.appendChild(detail);

    function chip(id, label) {
      var c = h("button", { class: "dv-chip", type: "button", "aria-pressed": String(state.board === id), text: label, onclick: function () { state.board = id; state.sel = null; render(); } });
      return c;
    }
    function stageCard(board, s, idx) {
      var key = board.id + ":" + idx;
      var on = state.sel && state.sel.key === key;
      var dim = state.hl && state.hl !== s.col;
      var b = h("button", {
        class: "bc-stage " + s.kind + (s.optional ? " absent" : "") + (on ? " on" : "") + (state.hl === s.col ? " hl" : "") + (dim ? " dim" : ""),
        type: "button", "aria-pressed": String(!!on), title: s.runs,
        onclick: function () { state.sel = { key: key, board: board, stage: s }; render(); },
        onmouseenter: function () { state.hl = s.col; paintHl(); },
        onmouseleave: function () { state.hl = null; paintHl(); },
        onfocus: function () { state.hl = s.col; paintHl(); },
        onblur: function () { state.hl = null; paintHl(); }
      }, h("b", { text: s.name }), h("span", { text: s.runs }));
      b.dataset.col = s.col;
      return b;
    }
    function paintHl() {
      Array.prototype.forEach.call(host.querySelectorAll(".bc-stage"), function (el) {
        el.classList.toggle("hl", !!state.hl && el.dataset.col === state.hl);
        el.classList.toggle("dim", !!state.hl && el.dataset.col !== state.hl);
      });
    }
    function row(board) {
      var flow = h("div", { class: "bc-flow" });
      var idx = 0, first = true;
      data.columns.forEach(function (col) {
        var items = board.stages.map(function (s, i) { return { s: s, i: i }; }).filter(function (x) { return x.s.col === col.id; });
        if (!first) flow.appendChild(h("span", { class: "bc-arrow", "aria-hidden": "true" }));
        first = false;
        var cell = h("div", { class: "bc-cell" });
        items.forEach(function (x) { cell.appendChild(stageCard(board, x.s, x.i)); });
        if (!items.length) cell.appendChild(h("div", { class: "bc-stage absent hw", "aria-hidden": "true" }, h("b", { text: "–" }), h("span", { text: "not a separate stage" })));
        flow.appendChild(cell);
        idx++;
      });
      return h("div", { class: "bc-row" },
        h("div", { class: "bc-label" }, h("span", { text: board.name }), h("small", { text: board.model })), flow);
    }
    function heads() {
      var flow = h("div", { class: "bc-flow" });
      data.columns.forEach(function (c, i) {
        if (i) flow.appendChild(h("span", { class: "bc-arrow", "aria-hidden": "true" }));
        flow.appendChild(h("div", { class: "bc-head", title: c.hint }, h("strong", { text: c.name }), h("div", { text: c.hint })));
      });
      return h("div", { class: "bc-row bc-heads" }, h("div"), flow);
    }
    function render() {
      tabs.textContent = "";
      tabs.appendChild(chip("all", "Compare all"));
      data.boards.forEach(function (b) { tabs.appendChild(chip(b.id, b.name)); });
      body.textContent = "";
      body.appendChild(heads());
      data.boards.filter(function (b) { return state.board === "all" || b.id === state.board; }).forEach(function (b) { body.appendChild(row(b)); });
      renderDetail();
    }
    function renderDetail() {
      detail.textContent = "";
      if (!state.sel) {
        detail.appendChild(h("h4", { text: "Pick a stage" }));
        detail.appendChild(h("p", { text: "Click any box to see where it runs, where it is stored, what it does and which command builds it. Hover a box to find the same job on the other boards." }));
        return;
      }
      var b = state.sel.board, s = state.sel.stage;
      var col = data.columns.filter(function (c) { return c.id === s.col; })[0];
      detail.appendChild(h("h4", { text: s.name + "  ·  " + b.name }));
      detail.appendChild(h("p", { text: s.does }));
      detail.appendChild(h("dl", null,
        h("dt", { text: "Its job in the chain" }), h("dd", { text: col ? col.name + ": " + col.hint : "" }),
        h("dt", { text: "Runs on / at" }), h("dd", { text: s.runs }),
        h("dt", { text: "Stored in" }), h("dd", { text: s.stored }),
        h("dt", { text: "Built by" }), h("dd", null, h("code", { text: s.built })),
        h("dt", { text: "Flashing model" }), h("dd", { text: b.model })));
      if (b.chapter) detail.appendChild(h("p", { style: "margin:0.7rem 0 0" }, h("a", { class: "md-button", href: new URL(b.chapter, ROOT).href, text: "Read the " + b.name + " boot chapter" })));
    }
    render();
  }

  function init() {
    Array.prototype.forEach.call(document.querySelectorAll(".bc[data-src]"), function (host) {
      if (host.dataset.ready) return;
      host.dataset.ready = "1";
      fetch(new URL(host.getAttribute("data-src"), ROOT)).then(function (r) { return r.json(); }).then(function (d) { build(host, d); })
        .catch(function () { host.textContent = "The explorer could not load its data."; });
    });
  }
  if (window.document$ && window.document$.subscribe) window.document$.subscribe(init);
  else if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
