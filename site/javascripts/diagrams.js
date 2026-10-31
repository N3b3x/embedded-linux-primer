/* Interactive diagrams: a viewer (zoom, pan, fit, side by side), step-by-step walkthroughs,
   diagram cards and a gallery. No dependencies. See docs/interactive-diagrams.md.

   Every .svg image on a page becomes a figure you can click to open in the viewer. The list of
   diagrams comes from assets/diagrams.json, which tools/build-site.py generates. A diagram that has a
   <name>.steps.json next to it also offers a walkthrough. */
(function () {
  "use strict";

  var SCRIPT = document.currentScript;
  var ROOT = new URL("../", SCRIPT.src);

  /* ------------------------------------------------------------------ helpers */
  function $(s, r) { return (r || document).querySelector(s); }
  function $$(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
  function h(tag, props) {
    var el = document.createElement(tag);
    props = props || {};
    Object.keys(props).forEach(function (k) {
      var v = props[k];
      if (v == null || v === false) return;
      if (k === "class") el.className = v;
      else if (k === "text") el.textContent = v;
      else if (k.slice(0, 2) === "on") el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? "" : v);
    });
    (function add(list) {
      for (var i = 0; i < list.length; i++) {
        var c = list[i];
        if (c == null || c === false) continue;
        if (Array.isArray(c)) add(c);
        else el.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
      }
    })(Array.prototype.slice.call(arguments, 2));
    return el;
  }
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
  function esc(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
  function stripHash(u) { return String(u).split("#")[0].split("?")[0]; }
  var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  var ICONS = {
    plus: '<path d="M12 5v14M5 12h14"/>',
    minus: '<path d="M5 12h14"/>',
    fit: '<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/>',
    close: '<path d="M6 6l12 12M18 6L6 18"/>',
    prev: '<path d="M15 5l-7 7 7 7"/>',
    next: '<path d="M9 5l7 7-7 7"/>',
    play: '<path d="M8 5v14l11-7z" fill="currentColor"/>',
    pause: '<path d="M9 5v14M15 5v14"/>',
    columns: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M12 4v16"/>',
    link: '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
    download: '<path d="M12 4v11M7 11l5 5 5-5M5 20h14"/>',
    external: '<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
    help: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.7.4-1 1-1 1.7M12 17h.01"/>',
    expand: '<path d="M4 9V4h5M20 15v5h-5M4 4l6 6M20 20l-6-6"/>',
    route: '<circle cx="6" cy="18" r="2"/><circle cx="18" cy="6" r="2"/><path d="M8 18h6a3 3 0 0 0 0-6h-4a3 3 0 0 1 0-6h6"/>',
    film: '<rect x="3" y="14" width="5" height="6" rx="1"/><rect x="9.5" y="14" width="5" height="6" rx="1"/><rect x="16" y="14" width="5" height="6" rx="1"/><rect x="3" y="4" width="18" height="7" rx="1"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>',
    check: '<path d="M5 12l5 5 9-10"/>',
    grid: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    rows: '<rect x="3" y="4" width="18" height="6" rx="1"/><rect x="3" y="14" width="18" height="6" rx="1"/>',
    chevrons: '<path d="M7 8l5-5 5 5M7 16l5 5 5-5"/>',
    arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>'
  };
  function icon(name) {
    var s = h("span", { class: "dv-i", "aria-hidden": "true" });
    s.innerHTML = '<svg viewBox="0 0 24 24" focusable="false">' + (ICONS[name] || "") + "</svg>";
    return s;
  }
  function btn(iconName, label, onclick, opts) {
    opts = opts || {};
    var b = h("button", { class: "dv-btn" + (opts.cls ? " " + opts.cls : ""), type: "button", title: opts.title || label, "aria-label": opts.title || label, onclick: onclick });
    if (iconName) b.appendChild(icon(iconName));
    if (opts.text !== false && label) b.appendChild(h("span", { class: "lbl", text: label }));
    return b;
  }

  /* ------------------------------------------------------------------ data */
  var manifestPromise;
  function manifest() {
    if (!manifestPromise) {
      manifestPromise = fetch(new URL("assets/diagrams.json", ROOT)).then(function (r) { return r.json(); }).then(function (m) {
        m.diagrams.forEach(function (d, i) {
          d.i = i;
          d.url = new URL(d.src, ROOT).href;
          d.stepsUrl = d.steps ? new URL(d.steps, ROOT).href : null;
        });
        m.byUrl = {};
        m.diagrams.forEach(function (d) { m.byUrl[d.url] = d; });
        return m;
      }).catch(function () { return { diagrams: [], byUrl: {} }; });
    }
    return manifestPromise;
  }
  var textCache = {};
  function fetchText(url) {
    if (!textCache[url]) textCache[url] = fetch(url).then(function (r) { if (!r.ok) throw new Error(url); return r.text(); });
    return textCache[url];
  }
  var stepsCache = {};
  function fetchSteps(url) {
    if (!stepsCache[url]) stepsCache[url] = fetch(url).then(function (r) { return r.json(); }).catch(function () { return null; });
    return stepsCache[url];
  }
  function entryFor(m, url, alt) {
    var clean = stripHash(url);
    return m.byUrl[clean] || { url: clean, src: clean, title: alt || clean.split("/").pop(), description: alt || "", group: "", tags: [], stepsUrl: null, adhoc: true };
  }

  /* tiny Markdown: **bold**, `code`, [text](url), blank line = paragraph */
  function mini(text) {
    var out = esc(text || "")
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, function (_, t, u) { return /^(https?:|\/|\.|#)/.test(u) ? '<a href="' + u + '" target="_blank" rel="noopener">' + t + "</a>" : t; });
    return out.split(/\n\s*\n/).map(function (p) { return "<p>" + p.replace(/\n/g, " ") + "</p>"; }).join("");
  }

  /* ------------------------------------------------------------------ pane: one diagram that can be zoomed and panned */
  var paneSeq = 0;
  function Pane(viewer) {
    var self = this;
    this.viewer = viewer;
    this.id = ++paneSeq;
    this.t = { x: 0, y: 0, k: 1 };
    this.fitK = 1;
    this.w = 1; this.h = 1;
    this.stage = h("div", { class: "dv-stage loading" });
    this.view = h("div", { class: "dv-view", tabindex: "-1" }, this.stage);
    this.title = h("strong");
    this.closeBtn = h("button", { class: "dv-btn ghost", type: "button", title: "Close this pane", "aria-label": "Close this pane", onclick: function () { viewer.closePane(self); } }, icon("close"));
    this.head = h("div", { class: "dv-pane-head" }, this.title, this.closeBtn);
    this.miniImg = h("img", { alt: "", draggable: "false" });
    this.miniBox = h("i");
    this.mini = h("div", { class: "dv-mini", title: "Overview: click or drag to move" }, this.miniImg, this.miniBox);
    this.el = h("div", { class: "dv-pane" }, this.head, this.view);
    this.view.appendChild(this.mini);
    this.shadow = this.stage.attachShadow({ mode: "open" });
    this.pointers = {};
    this.ov = null;
    this.bind();
    if (window.ResizeObserver) {
      this.ro = new ResizeObserver(function () { if (self.entry) self.onResize(); });
      this.ro.observe(this.view);
    }
  }
  Pane.prototype.onResize = function () {
    if (this.following && this.lastRegions) this.focus(this.lastRegions, false, true);
    else if (this.isFit) this.fit(false);
    else this.update();
  };
  Pane.prototype.load = function (entry) {
    var self = this;
    this.entry = entry;
    this.title.textContent = entry.title;
    this.stage.classList.add("loading");
    this.miniImg.src = entry.url;
    var token = (this.token = {});
    return fetchText(entry.url).then(function (text) {
      if (self.token !== token) return;
      self.shadow.innerHTML = text;
      self.svg = self.shadow.querySelector("svg");
      var vb = self.svg.viewBox && self.svg.viewBox.baseVal;
      self.w = (vb && vb.width) || parseFloat(self.svg.getAttribute("width")) || 1400;
      self.h = (vb && vb.height) || parseFloat(self.svg.getAttribute("height")) || 800;
      self.svg.removeAttribute("width"); self.svg.removeAttribute("height");
      self.svg.style.cssText = "display:block;width:" + self.w + "px;height:" + self.h + "px;overflow:visible";
      self.stage.style.width = self.w + "px"; self.stage.style.height = self.h + "px";
      self.stage.classList.remove("loading");
      self.ov = null; self.lastRegions = null; self.following = false;
      self.fit(false);
    }).catch(function () { self.stage.classList.remove("loading"); self.shadow.innerHTML = '<div style="color:#fda4af;padding:24px;font:14px system-ui">Could not load this diagram.</div>'; });
  };
  Pane.prototype.size = function () { var r = this.view.getBoundingClientRect(); return { w: r.width, h: r.height }; };
  Pane.prototype.apply = function (animate) {
    this.stage.classList.toggle("anim", !!animate && !reduced);
    this.stage.style.transform = "translate(" + this.t.x + "px," + this.t.y + "px) scale(" + this.t.k + ")";
    this.update();
  };
  Pane.prototype.update = function () {
    var s = this.size(), k = this.t.k;
    this.viewer.zoomLabel(this);
    var show = k > this.fitK * 1.12 && s.w > 360;
    this.mini.classList.toggle("show", show);
    if (show) {
      var mw = this.mini.clientWidth || 190, sc = mw / this.w;
      var vx = -this.t.x / k, vy = -this.t.y / k, vw = s.w / k, vh = s.h / k;
      var x0 = clamp(vx, 0, this.w), y0 = clamp(vy, 0, this.h), x1 = clamp(vx + vw, 0, this.w), y1 = clamp(vy + vh, 0, this.h);
      this.miniBox.style.cssText = "left:" + x0 * sc + "px;top:" + y0 * sc + "px;width:" + Math.max(4, (x1 - x0) * sc) + "px;height:" + Math.max(4, (y1 - y0) * sc) + "px";
    }
  };
  Pane.prototype.fitTransform = function () {
    var s = this.size(), pad = s.w < 500 ? 8 : 28;
    var k = Math.min((s.w - 2 * pad) / this.w, (s.h - 2 * pad) / this.h);
    k = clamp(k, 0.05, 2);
    return { k: k, x: (s.w - this.w * k) / 2, y: (s.h - this.h * k) / 2 };
  };
  Pane.prototype.fit = function (animate) {
    var f = this.fitTransform();
    this.fitK = f.k; this.t = { x: f.x, y: f.y, k: f.k }; this.isFit = true; this.following = false;
    this.apply(animate);
  };
  Pane.prototype.actual = function (animate) { this.zoomTo(1, animate); };
  Pane.prototype.constrain = function () {
    var s = this.size(), k = this.t.k, keep = 80;
    this.t.x = clamp(this.t.x, keep - this.w * k, s.w - keep);
    this.t.y = clamp(this.t.y, keep - this.h * k, s.h - keep);
  };
  Pane.prototype.zoomAt = function (cx, cy, factor, animate) {
    var k = clamp(this.t.k * factor, this.fitK * 0.4, 14);
    var r = k / this.t.k;
    this.t.x = cx - (cx - this.t.x) * r; this.t.y = cy - (cy - this.t.y) * r; this.t.k = k;
    this.isFit = Math.abs(k - this.fitK) < 1e-3; this.following = false;
    this.constrain(); this.apply(animate);
    this.viewer.synced(this);
  };
  Pane.prototype.zoomTo = function (k, animate) { var s = this.size(); this.zoomAt(s.w / 2, s.h / 2, k / this.t.k, animate); };
  Pane.prototype.panBy = function (dx, dy) { this.t.x += dx; this.t.y += dy; this.isFit = false; this.following = false; this.constrain(); this.apply(false); this.viewer.synced(this); };
  Pane.prototype.centerOn = function (ux, uy) { var s = this.size(); this.t.x = s.w / 2 - ux * this.t.k; this.t.y = s.h / 2 - uy * this.t.k; this.isFit = false; this.constrain(); this.apply(false); };

  Pane.prototype.bind = function () {
    var self = this, view = this.view;
    view.addEventListener("wheel", function (e) {
      e.preventDefault();
      var r = view.getBoundingClientRect();
      var dy = e.deltaMode === 1 ? e.deltaY * 16 : e.deltaY;
      self.zoomAt(e.clientX - r.left, e.clientY - r.top, Math.exp(-dy * (e.ctrlKey ? 0.01 : 0.0018)), false);
    }, { passive: false });
    view.addEventListener("pointerdown", function (e) {
      if (e.button !== 0 || e.target.closest(".dv-mini")) return;
      self.viewer.activate(self);
      view.setPointerCapture(e.pointerId);
      self.pointers[e.pointerId] = { x: e.clientX, y: e.clientY };
      self.moved = 0;
      view.classList.add("grabbing");
      self.viewer.hideHint();
    });
    view.addEventListener("pointermove", function (e) {
      var p = self.pointers[e.pointerId];
      if (!p) return;
      var ids = Object.keys(self.pointers);
      if (ids.length === 2) {
        var o = self.pointers[ids[0] === String(e.pointerId) ? ids[1] : ids[0]];
        var d0 = Math.hypot(p.x - o.x, p.y - o.y);
        p.x = e.clientX; p.y = e.clientY;
        var d1 = Math.hypot(p.x - o.x, p.y - o.y);
        var r = view.getBoundingClientRect();
        if (d0 > 0) self.zoomAt((p.x + o.x) / 2 - r.left, (p.y + o.y) / 2 - r.top, d1 / d0, false);
      } else {
        var dx = e.clientX - p.x, dy = e.clientY - p.y;
        p.x = e.clientX; p.y = e.clientY;
        self.moved += Math.abs(dx) + Math.abs(dy);
        self.panBy(dx, dy);
      }
    });
    function up(e) { delete self.pointers[e.pointerId]; if (!Object.keys(self.pointers).length) view.classList.remove("grabbing"); }
    view.addEventListener("pointerup", up);
    view.addEventListener("pointercancel", up);
    view.addEventListener("dblclick", function (e) {
      var r = view.getBoundingClientRect();
      if (self.isFit) self.zoomAt(e.clientX - r.left, e.clientY - r.top, 2.4, true);
      else self.fit(true);
      self.viewer.synced(self);
    });
    function miniMove(e) {
      var r = self.mini.getBoundingClientRect();
      var sc = r.width / self.w;
      self.centerOn((e.clientX - r.left) / sc, (e.clientY - r.top) / sc);
    }
    this.mini.addEventListener("pointerdown", function (e) { e.stopPropagation(); self.mini.setPointerCapture(e.pointerId); self.miniDrag = true; miniMove(e); });
    this.mini.addEventListener("pointermove", function (e) { if (self.miniDrag) miniMove(e); });
    this.mini.addEventListener("pointerup", function () { self.miniDrag = false; });
  };

  /* ---- highlight overlay (used by walkthroughs) ---- */
  Pane.prototype.ensureOverlay = function () {
    if (this.ov) return this.ov;
    var NS = "http://www.w3.org/2000/svg";
    var svg = this.svg;
    var style = document.createElementNS(NS, "style");
    style.textContent = ".dvr{fill:none;stroke:#5eead4;stroke-width:3.5;filter:drop-shadow(0 0 7px rgba(94,234,212,.75));transition:x .45s cubic-bezier(.22,.8,.28,1),y .45s cubic-bezier(.22,.8,.28,1),width .45s cubic-bezier(.22,.8,.28,1),height .45s cubic-bezier(.22,.8,.28,1);animation:dvp 1.8s ease-in-out infinite}" +
      ".dvh{transition:x .45s cubic-bezier(.22,.8,.28,1),y .45s cubic-bezier(.22,.8,.28,1),width .45s cubic-bezier(.22,.8,.28,1),height .45s cubic-bezier(.22,.8,.28,1)}" +
      "@keyframes dvp{0%,100%{stroke-opacity:1}50%{stroke-opacity:.45}}@media (prefers-reduced-motion:reduce){.dvr{animation:none}}";
    var g = document.createElementNS(NS, "g");
    g.setAttribute("pointer-events", "none");
    var mask = document.createElementNS(NS, "mask");
    mask.setAttribute("id", "dv-mask");
    mask.setAttribute("maskUnits", "userSpaceOnUse");
    var white = document.createElementNS(NS, "rect");
    white.setAttribute("x", "0"); white.setAttribute("y", "0"); white.setAttribute("width", this.w); white.setAttribute("height", this.h); white.setAttribute("fill", "#fff");
    mask.appendChild(white);
    var dim = document.createElementNS(NS, "rect");
    dim.setAttribute("x", "0"); dim.setAttribute("y", "0"); dim.setAttribute("width", this.w); dim.setAttribute("height", this.h);
    dim.setAttribute("fill", "#020617"); dim.setAttribute("fill-opacity", "0.7"); dim.setAttribute("mask", "url(#dv-mask)");
    var holes = document.createElementNS(NS, "g"), rings = document.createElementNS(NS, "g");
    mask.appendChild(holes);
    g.appendChild(mask); g.appendChild(dim); g.appendChild(rings);
    svg.appendChild(style); svg.appendChild(g);
    this.ov = { g: g, holes: holes, rings: rings, dim: dim, NS: NS, nodes: [] };
    return this.ov;
  };
  Pane.prototype.setRegions = function (regs) {
    if (!regs || !regs.length) {
      if (this.ov) { this.ov.g.setAttribute("display", "none"); }
      return;
    }
    var o = this.ensureOverlay();
    o.g.removeAttribute("display");
    while (o.nodes.length < regs.length) {
      var hole = document.createElementNS(o.NS, "rect"), ring = document.createElementNS(o.NS, "rect");
      hole.setAttribute("fill", "#000"); hole.setAttribute("class", "dvh");
      ring.setAttribute("class", "dvr");
      o.holes.appendChild(hole); o.rings.appendChild(ring);
      o.nodes.push({ hole: hole, ring: ring });
    }
    o.nodes.forEach(function (n, i) {
      var r = regs[i];
      n.hole.style.display = n.ring.style.display = r ? "" : "none";
      if (!r) return;
      [n.hole, n.ring].forEach(function (el) {
        el.setAttribute("x", r.x); el.setAttribute("y", r.y); el.setAttribute("width", r.w); el.setAttribute("height", r.h); el.setAttribute("rx", r.rx == null ? 12 : r.rx);
        el.style.setProperty("x", r.x + "px"); el.style.setProperty("y", r.y + "px"); el.style.setProperty("width", r.w + "px"); el.style.setProperty("height", r.h + "px");
      });
    });
  };

  /* ---- resolving walkthrough anchors to rectangles in diagram units ---- */
  function norm(s) { return String(s).replace(/\s+/g, " ").trim(); }
  Pane.prototype.units = function (rect, sr, vb) {
    var kx = vb.width / sr.width, ky = vb.height / sr.height;
    return { x: (rect.left - sr.left) * kx + vb.x, y: (rect.top - sr.top) * ky + vb.y, w: rect.width * kx, h: rect.height * ky };
  };
  Pane.prototype.resolveAnchor = function (a, step) {
    var svg = this.svg, sr = svg.getBoundingClientRect(), vb = svg.viewBox.baseVal;
    if (!sr.width) return null;
    var pad = step.pad == null ? 8 : step.pad;
    var m = /^rect:\s*([-\d.]+)[,\s]+([-\d.]+)[,\s]+([-\d.]+)[,\s]+([-\d.]+)/.exec(a);
    if (m) return { x: +m[1], y: +m[2], w: +m[3], h: +m[4] };
    var el, tr;
    if (a.indexOf("id:") === 0) {
      el = this.shadow.getElementById(a.slice(3));
      if (!el) return null;
      var u = this.units(el.getBoundingClientRect(), sr, vb);
      return { x: u.x - pad, y: u.y - pad, w: u.w + 2 * pad, h: u.h + 2 * pad };
    }
    var texts = $$("text", this.shadow), want = norm(a), hits = texts.filter(function (t) { return norm(t.textContent) === want; });
    if (!hits.length) hits = texts.filter(function (t) { return norm(t.textContent).indexOf(want) >= 0; });
    el = hits[step.nth || 0];
    if (!el) return null;
    tr = el.getBoundingClientRect();
    if (step.exact) { var e = this.units(tr, sr, vb); return { x: e.x - pad, y: e.y - pad, w: e.w + 2 * pad, h: e.h + 2 * pad, rx: 6 }; }
    var total = sr.width * sr.height, tol = 2, up = step.up || 0;
    var cands = $$("rect", this.shadow).map(function (r) { var b = r.getBoundingClientRect(); return { r: r, b: b, area: b.width * b.height }; }).filter(function (c) {
      return c.area > tr.width * tr.height * 1.15 && c.area < total * 0.55 &&
        c.b.left <= tr.left + tol && c.b.top <= tr.top + tol && c.b.right >= tr.right - tol && c.b.bottom >= tr.bottom - tol;
    }).sort(function (p, q) { return p.area - q.area; });
    var pick = cands[Math.min(up, cands.length - 1)];
    var box = pick ? pick.b : this.halo(el, tr, total, sr, vb);
    var uu = this.units(box, sr, vb);
    return { x: uu.x - pad / 2, y: uu.y - pad / 2, w: uu.w + pad, h: uu.h + pad, rx: pick ? parseFloat(pick.r.getAttribute("rx") || 10) + 2 : 6 };
  };
  /* A label with no box around it (a timeline caption, a note): take the label and the marks beside it. */
  Pane.prototype.halo = function (el, tr, total, sr, vb) {
    var f = sr.width / vb.width, hx = 44 * f, up = 40 * f, down = 72 * f;
    var l = tr.left - hx, r = tr.right + hx, t = tr.top - up, b = tr.bottom + down;
    var x0 = tr.left, y0 = tr.top, x1 = tr.right, y1 = tr.bottom;
    $$("text, circle, ellipse, path, line, polygon, rect", this.shadow).forEach(function (n) {
      if (n === el || n.closest("defs, marker, mask, clipPath, style")) return;
      var q = n.getBoundingClientRect();
      if (!q.width && !q.height) return;
      if (q.width * q.height > total * 0.3) return;
      var cx = (q.left + q.right) / 2, cy = (q.top + q.bottom) / 2;
      if (cx < l || cx > r || cy < t || cy > b) return;
      x0 = Math.min(x0, q.left); y0 = Math.min(y0, q.top); x1 = Math.max(x1, q.right); y1 = Math.max(y1, q.bottom);
    });
    return { left: x0, top: y0, width: x1 - x0, height: y1 - y0, right: x1, bottom: y1 };
  };
  Pane.prototype.resolveStep = function (step) {
    var self = this;
    var list = step.anchor == null ? [] : Array.isArray(step.anchor) ? step.anchor : [step.anchor];
    var regs = [], missing = [];
    list.forEach(function (a) { var r = self.resolveAnchor(a, step); if (r) regs.push(r); else missing.push(a); });
    return { regions: regs, missing: missing };
  };
  Pane.prototype.focus = function (regs, animate, keep) {
    if (!regs || !regs.length) { this.lastRegions = null; this.fit(animate); this.following = false; return; }
    var x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    regs.forEach(function (r) { x0 = Math.min(x0, r.x); y0 = Math.min(y0, r.y); x1 = Math.max(x1, r.x + r.w); y1 = Math.max(y1, r.y + r.h); });
    var s = this.size(), m = Math.min(s.w, s.h) * 0.14 + 24;
    var bw = x1 - x0, bh = y1 - y0;
    var k = Math.min((s.w - 2 * m) / bw, (s.h - 2 * m) / bh);
    var f = this.fitTransform();
    // never zoom further than is useful: a small box is shown with its surroundings
    k = clamp(k, f.k, Math.max(f.k, Math.min(2, f.k * 2.6)));
    if (bw * bh > this.w * this.h * 0.55 || k < f.k * 1.12) {
      k = f.k;
      this.t.k = f.k; this.t.x = f.x; this.t.y = f.y;
    } else {
      this.t.k = k;
      this.t.x = s.w / 2 - ((x0 + x1) / 2) * k; this.t.y = s.h / 2 - ((y0 + y1) / 2) * k;
    }
    this.isFit = Math.abs(k - f.k) < 1e-3; this.fitK = f.k;
    this.lastRegions = regs; this.following = true;
    this.apply(animate);
  };

  /* ------------------------------------------------------------------ the viewer */
  function Viewer() {
    var self = this;
    this.list = []; this.index = 0; this.panes = []; this.active = null; this.linked = false;
    this.steps = null; this.stepIdx = -1; this.playTimer = null;
    this.buildDom();
    document.addEventListener("keydown", function (e) { self.onKey(e); }, true);
    window.addEventListener("hashchange", function () { self.fromHash(); });
  }
  Viewer.prototype.buildDom = function () {
    var self = this;
    this.titleEl = h("strong"); this.subEl = h("span");
    this.zoomEl = h("span", { class: "dv-zoom", "aria-live": "off" });
    this.prevB = btn("prev", "Previous", function () { self.go(-1); }, { title: "Previous diagram ([)", text: false });
    this.nextB = btn("next", "Next", function () { self.go(1); }, { title: "Next diagram (])", text: false });
    this.walkB = btn("route", "Walk through", function () { self.toggleWalk(); }, { title: "Step-by-step walkthrough (w)" });
    this.splitB = btn("columns", "Side by side", function () { self.toggleSplit(); }, { title: "Show two diagrams side by side (s)" });
    this.linkB = btn("link", "Link", function () { self.toggleLink(); }, { title: "Keep both views in sync (l)" });
    this.stackB = btn("rows", "Stack", function () { self.toggleStack(); }, { title: "Stack the two diagrams instead of side by side (v)" });
    this.stripB = btn("film", "Diagrams", function () { self.toggleStrip(); }, { title: "Browse all diagrams (g)" });
    this.openB = h("a", { class: "dv-btn", target: "_blank", rel: "noopener", title: "Open the SVG file", "aria-label": "Open the SVG file" }, icon("external"));
    this.dlB = h("a", { class: "dv-btn", title: "Download the SVG", "aria-label": "Download the SVG", download: "" }, icon("download"));
    this.top = h("div", { class: "dv-top" },
      h("div", { class: "dv-title" }, this.titleEl, this.subEl),
      h("div", { class: "dv-tools" },
        this.prevB, this.nextB, h("span", { class: "dv-sep" }),
        btn("minus", "Zoom out", function () { self.zoom(1 / 1.35); }, { title: "Zoom out (-)", text: false }),
        this.zoomEl,
        btn("plus", "Zoom in", function () { self.zoom(1.35); }, { title: "Zoom in (+)", text: false }),
        btn("fit", "Fit", function () { self.fit(); }, { title: "Fit to the window (f or 0)" }),
        btn(null, "1:1", function () { self.each(function (p) { p.actual(true); }); }, { title: "Actual size (1)" }),
        h("span", { class: "dv-sep" }),
        this.walkB, this.splitB, this.linkB, this.stackB, this.stripB,
        h("span", { class: "dv-sep" }),
        this.openB, this.dlB,
        btn("help", "Help", function () { self.toggleHelp(); }, { title: "Keyboard shortcuts (?)", text: false }),
        btn("close", "Close", function () { self.close(); }, { title: "Close (Esc)", cls: "primary" })));
    this.panesEl = h("div", { class: "dv-panes" });
    this.hintEl = h("div", { class: "dv-hint", text: "Scroll to zoom · drag to move · double-click to zoom in or fit" });
    this.walkTitle = h("div", { class: "dv-step-title" }); this.walkBody = h("div", { class: "dv-step-body" });
    this.dotsEl = h("div", { class: "dv-dots" }); this.countEl = h("span", { class: "dv-count" });
    this.playB = btn("play", "Play", function () { self.togglePlay(); }, { title: "Play / pause (space)" });
    this.stepPrev = btn("prev", "Back", function () { self.step(-1); }, { title: "Previous step (←)" });
    this.stepNext = btn("next", "Next", function () { self.step(1); }, { title: "Next step (→)", cls: "primary" });
    this.walkEl = h("div", { class: "dv-walk", role: "region", "aria-label": "Walkthrough", "aria-live": "polite" },
      h("div", { class: "dv-walk-head" }, this.dotsEl, this.countEl, this.stepPrev, this.playB, this.stepNext, btn("close", "Show all", function () { self.stopWalk(); }, { title: "Leave the walkthrough (Esc)" })),
      this.walkTitle, this.walkBody);
    this.stripEl = h("div", { class: "dv-strip", role: "listbox", "aria-label": "Diagrams" });
    this.helpEl = h("div", { class: "dv-help", hidden: true, onclick: function (e) { if (e.target === self.helpEl) self.toggleHelp(false); } },
      h("div", { class: "dv-help-card", role: "document" }, h("h3", { text: "Keyboard and mouse" }), this.helpGrid()));
    this.root = h("div", { class: "dv-overlay", role: "dialog", "aria-modal": "true", "aria-label": "Diagram viewer", hidden: true },
      this.top, this.panesEl, this.walkEl, this.stripEl, this.helpEl);
    this.panesEl.appendChild(this.hintEl);
    document.body.appendChild(this.root);
  };
  Viewer.prototype.helpGrid = function () {
    var rows = [
      ["Zoom", "scroll · pinch · + −"], ["Move", "drag · arrow keys"], ["Fit to window", "f · 0 · double-click"], ["Actual size", "1"],
      ["Next / previous diagram", "] [ "], ["Walkthrough", "w"], ["Next / previous step", "→ ←"], ["Play / pause", "space"],
      ["Side by side", "s"], ["Link the two views", "l"], ["Stack or side by side", "v"], ["Browse diagrams", "g"], ["Close", "esc"]
    ];
    var grid = h("div", { class: "dv-help-grid" });
    rows.forEach(function (r) {
      var keys = h("span");
      r[1].split(" · ").forEach(function (k, i) { if (i) keys.appendChild(document.createTextNode("  ")); keys.appendChild(h("kbd", { class: "dv-k", text: k.trim() })); });
      grid.appendChild(h("div", null, h("span", { text: r[0] }), keys));
    });
    return grid;
  };
  Viewer.prototype.each = function (fn) { this.panes.forEach(fn); };
  Viewer.prototype.zoomLabel = function (pane) { if (pane === this.active) this.zoomEl.textContent = Math.round(pane.t.k * 100) + "%"; };
  Viewer.prototype.hideHint = function () { this.hintEl.classList.add("gone"); };
  Viewer.prototype.activate = function (pane) {
    this.active = pane;
    var multi = this.panes.length > 1;
    this.panes.forEach(function (p) { p.el.classList.toggle("active", p === pane); p.el.classList.toggle("multi", multi); });
    if (pane.entry) this.showMeta(pane.entry);
    this.zoomLabel(pane);
    this.markStrip();
  };
  Viewer.prototype.showMeta = function (e) {
    this.titleEl.textContent = e.title;
    this.subEl.textContent = [e.group, e.description && e.description.length < 140 ? e.description : ""].filter(Boolean).join(" · ");
    this.openB.href = e.url; this.dlB.href = e.url; this.dlB.setAttribute("download", e.url.split("/").pop());
    this.walkB.style.display = e.stepsUrl ? "" : "none";
  };

  Viewer.prototype.open = function (list, index, opts) {
    opts = opts || {};
    this.opener = document.activeElement;
    this.list = list.slice(); this.index = clamp(index, 0, list.length - 1);
    this.root.hidden = false;
    document.body.classList.add("dv-open");
    requestAnimationFrame(function (r) { return function () { r.classList.add("in"); }; }(this.root));
    this.hintEl.classList.remove("gone");
    this.buildStrip();
    this.ensurePanes(opts.split ? 2 : 1);
    var self = this;
    var loads = [this.panes[0].load(this.list[this.index])];
    if (opts.split) loads.push(this.panes[1].load(opts.split));
    this.activate(this.panes[0]);
    Promise.all(loads).then(function () {
      self.markStrip();
      if (opts.walk && self.panes[0].entry.stepsUrl) self.startWalk(opts.step || 0);
    });
    this.setHash();
    this.root.querySelector(".dv-btn.primary").focus();
    window.setTimeout(function () { self.hintEl.classList.add("gone"); }, 5200);
  };
  Viewer.prototype.ensurePanes = function (n) {
    while (this.panes.length < n) { var p = new Pane(this); this.panes.push(p); this.panesEl.appendChild(p.el); }
    while (this.panes.length > n) { var q = this.panes.pop(); q.el.remove(); if (q.ro) q.ro.disconnect(); }
    this.panesEl.classList.toggle("split", n > 1);
    this.splitB.setAttribute("aria-pressed", String(n > 1));
    this.linkB.style.display = n > 1 ? "" : "none";
    this.stackB.style.display = n > 1 ? "" : "none";
    this.activate(this.panes.indexOf(this.active) >= 0 ? this.active : this.panes[0]);
    var self = this;
    window.requestAnimationFrame(function () { self.each(function (p) { if (p.entry) p.fit(false); }); });
  };
  Viewer.prototype.close = function () {
    this.stopWalk(true);
    this.root.classList.remove("in");
    var root = this.root, self = this;
    window.setTimeout(function () { root.hidden = true; self.each(function (p) { p.ro && p.ro.disconnect(); p.el.remove(); }); self.panes = []; self.active = null; }, reduced ? 0 : 160);
    document.body.classList.remove("dv-open");
    if (history.replaceState && /dv=/.test(location.hash)) history.replaceState(null, "", location.pathname + location.search);
    if (this.opener && this.opener.focus) try { this.opener.focus(); } catch (e) { /* ignore */ }
  };
  Viewer.prototype.isOpen = function () { return !this.root.hidden; };
  Viewer.prototype.show = function (index, pane) {
    var self = this;
    pane = pane || this.active || this.panes[0];
    this.stopWalk(true);
    var entry = this.list[index];
    if (!entry) return;
    if (pane === this.panes[0]) this.index = index;
    pane.load(entry).then(function () { self.activate(pane); self.setHash(); });
    this.activate(pane);
  };
  Viewer.prototype.go = function (d) {
    if (this.list.length < 2) return;
    var i = (this.index + d + this.list.length) % this.list.length;
    this.show(i, this.panes[0]);
  };
  Viewer.prototype.zoom = function (f) {
    var self = this;
    this.each(function (p) { if (p === self.active || self.linked) { var s = p.size(); p.zoomAt(s.w / 2, s.h / 2, f, true); } });
  };
  Viewer.prototype.fit = function () { this.each(function (p) { p.fit(true); }); };
  Viewer.prototype.synced = function (src) {
    if (!this.linked || this.panes.length < 2 || this.syncing) return;
    this.syncing = true;
    var o = this.panes[0] === src ? this.panes[1] : this.panes[0];
    if (o && o.entry) {
      var rel = src.t.k / src.fitK;
      var s = o.size(), ss = src.size();
      o.t.k = o.fitK * rel;
      o.t.x = (src.t.x / ss.w) * s.w; o.t.y = (src.t.y / ss.h) * s.h;
      o.isFit = src.isFit; o.apply(false);
    }
    this.syncing = false;
  };
  Viewer.prototype.toggleStack = function () {
    var on = this.panesEl.classList.toggle("stack");
    this.stackB.setAttribute("aria-pressed", String(on));
    var self = this;
    window.setTimeout(function () { self.each(function (p) { p.fit(true); }); }, 40);
  };
  Viewer.prototype.toggleLink = function () { this.linked = !this.linked; this.linkB.setAttribute("aria-pressed", String(this.linked)); if (this.linked) this.synced(this.active); };
  Viewer.prototype.toggleSplit = function () {
    if (this.panes.length > 1) { this.ensurePanes(1); return; }
    var other = this.list[(this.index + 1) % this.list.length];
    this.ensurePanes(2);
    var self = this;
    this.panes[1].load(other).then(function () { self.activate(self.panes[1]); self.markStrip(); self.hint2(); });
  };
  Viewer.prototype.hint2 = function () { this.hintEl.textContent = "Pick a diagram in the strip below to show it in the highlighted pane"; this.hintEl.classList.remove("gone"); var h2 = this.hintEl; window.setTimeout(function () { h2.classList.add("gone"); }, 4500); this.stripEl.parentNode && this.root.classList.add("strip"); };
  Viewer.prototype.closePane = function (pane) { if (this.panes.length > 1) { this.panes.splice(this.panes.indexOf(pane), 1); pane.el.remove(); this.ensurePanes(1); } };
  Viewer.prototype.toggleStrip = function (force) { var on = force == null ? !this.root.classList.contains("strip") : force; this.root.classList.toggle("strip", on); this.stripB.setAttribute("aria-pressed", String(on)); var self = this; window.setTimeout(function () { self.each(function (p) { p.onResize(); }); }, 30); };
  Viewer.prototype.toggleHelp = function (force) { this.helpEl.hidden = force == null ? !this.helpEl.hidden : !force; };
  Viewer.prototype.buildStrip = function () {
    var self = this;
    this.stripEl.textContent = "";
    this.list.forEach(function (e, i) {
      var b = h("button", { class: "dv-thumb", type: "button", role: "option", title: e.title, onclick: function () { self.show(i, self.active); } },
        h("img", { src: e.url, alt: "", loading: "lazy" }), h("span", { text: e.title }));
      b.dataset.i = i;
      self.stripEl.appendChild(b);
    });
  };
  Viewer.prototype.markStrip = function () {
    var self = this, a = this.panes[0] && this.panes[0].entry, b = this.panes[1] && this.panes[1].entry;
    $$(".dv-thumb", this.stripEl).forEach(function (t) {
      var e = self.list[+t.dataset.i];
      t.classList.toggle("on", !!a && e.url === a.url);
      t.classList.toggle("on2", !!b && e.url === b.url);
      t.setAttribute("aria-selected", String(!!a && e.url === a.url));
    });
    var on = $(".dv-thumb.on", this.stripEl);
    if (on && on.scrollIntoView) on.scrollIntoView({ block: "nearest", inline: "center" });
  };

  /* ---- walkthroughs ---- */
  Viewer.prototype.toggleWalk = function () { if (this.root.classList.contains("walking")) this.stopWalk(); else this.startWalk(0); };
  Viewer.prototype.startWalk = function (idx) {
    var self = this, pane = this.panes[0], e = pane.entry;
    if (!e || !e.stepsUrl) return;
    if (this.panes.length > 1) this.ensurePanes(1);
    fetchSteps(e.stepsUrl).then(function (data) {
      if (!data || !data.steps || !data.steps.length) return;
      self.steps = data.steps; self.stepIdx = -1;
      self.dotsEl.textContent = "";
      data.steps.forEach(function (s, i) { self.dotsEl.appendChild(h("button", { class: "dv-dot", type: "button", title: s.title || "Step " + (i + 1), "aria-label": "Step " + (i + 1), onclick: function () { self.goStep(i); } })); });
      self.root.classList.add("walking");
      self.walkB.setAttribute("aria-pressed", "true");
      window.setTimeout(function () { self.goStep(idx || 0); }, 60);
    });
  };
  Viewer.prototype.stopWalk = function (quiet) {
    this.pause();
    if (!this.root.classList.contains("walking")) return;
    this.root.classList.remove("walking");
    this.walkB.setAttribute("aria-pressed", "false");
    this.steps = null; this.stepIdx = -1;
    var p = this.panes[0];
    if (p) { p.setRegions(null); if (!quiet) window.setTimeout(function () { p.fit(true); }, 40); }
    this.setHash();
  };
  Viewer.prototype.goStep = function (i) {
    if (!this.steps) return;
    i = clamp(i, 0, this.steps.length - 1);
    this.stepIdx = i;
    var pane = this.panes[0], s = this.steps[i];
    var res = pane.resolveStep(s);
    if (res.missing.length && window.console) console.warn("walkthrough: anchor not found in " + pane.entry.title + ":", res.missing);
    pane.setRegions(res.regions);
    pane.focus(res.regions, true);
    this.walkTitle.textContent = s.title || "";
    this.walkBody.innerHTML = mini(s.body || "");
    this.countEl.textContent = (i + 1) + " / " + this.steps.length;
    var dots = $$(".dv-dot", this.dotsEl);
    dots.forEach(function (d, j) { d.classList.toggle("on", j === i); d.classList.toggle("done", j < i); });
    this.stepPrev.disabled = i === 0;
    this.stepNext.disabled = i === this.steps.length - 1;
    this.setHash();
  };
  Viewer.prototype.step = function (d) { if (this.steps) this.goStep(this.stepIdx + d); };
  Viewer.prototype.togglePlay = function () { if (this.playTimer) this.pause(); else this.play(); };
  Viewer.prototype.play = function () {
    var self = this;
    if (this.stepIdx >= this.steps.length - 1) this.goStep(0);
    this.playB.querySelector(".dv-i").innerHTML = '<svg viewBox="0 0 24 24">' + ICONS.pause + "</svg>";
    var lbl = this.playB.querySelector(".lbl"); if (lbl) lbl.textContent = "Pause";
    this.playTimer = window.setInterval(function () {
      if (self.stepIdx >= self.steps.length - 1) { self.pause(); return; }
      self.goStep(self.stepIdx + 1);
    }, 7000);
  };
  Viewer.prototype.pause = function () {
    if (this.playTimer) { window.clearInterval(this.playTimer); this.playTimer = null; }
    var i = this.playB.querySelector(".dv-i"); if (i) i.innerHTML = '<svg viewBox="0 0 24 24">' + ICONS.play + "</svg>";
    var lbl = this.playB.querySelector(".lbl"); if (lbl) lbl.textContent = "Play";
  };

  /* ---- keyboard ---- */
  Viewer.prototype.onKey = function (e) {
    if (!this.isOpen()) return;
    var t = e.target;
    if (t && /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName)) return;
    var walking = this.root.classList.contains("walking"), k = e.key, handled = true;
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    if (k === "Tab") { this.trap(e); return; }
    switch (k) {
      case "Escape": if (!this.helpEl.hidden) this.toggleHelp(false); else if (walking) this.stopWalk(); else if (this.panes.length > 1) this.ensurePanes(1); else this.close(); break;
      case "+": case "=": this.zoom(1.35); break;
      case "-": case "_": this.zoom(1 / 1.35); break;
      case "0": case "f": case "F": this.fit(); break;
      case "1": this.each(function (p) { p.actual(true); }); break;
      case "]": case "PageDown": this.go(1); break;
      case "[": case "PageUp": this.go(-1); break;
      case "ArrowRight": if (walking) this.step(1); else if (this.active) this.active.panBy(-80, 0); break;
      case "ArrowLeft": if (walking) this.step(-1); else if (this.active) this.active.panBy(80, 0); break;
      case "ArrowUp": if (this.active) this.active.panBy(0, 80); break;
      case "ArrowDown": if (this.active) this.active.panBy(0, -80); break;
      case " ": if (walking) this.togglePlay(); else handled = false; break;
      case "w": case "W": if (this.panes[0] && this.panes[0].entry && this.panes[0].entry.stepsUrl) this.toggleWalk(); break;
      case "s": case "S": this.toggleSplit(); break;
      case "l": case "L": if (this.panes.length > 1) this.toggleLink(); break;
      case "v": case "V": if (this.panes.length > 1) this.toggleStack(); break;
      case "g": case "G": this.toggleStrip(); break;
      case "?": this.toggleHelp(); break;
      default: handled = false;
    }
    if (handled) { e.preventDefault(); e.stopPropagation(); }
  };
  Viewer.prototype.trap = function (e) {
    var f = $$("button:not([disabled]), a[href], [tabindex]:not([tabindex='-1'])", this.root).filter(function (x) { return x.offsetParent !== null; });
    if (!f.length) return;
    var first = f[0], last = f[f.length - 1];
    if (!this.root.contains(document.activeElement)) { first.focus(); e.preventDefault(); }
    else if (e.shiftKey && document.activeElement === first) { last.focus(); e.preventDefault(); }
    else if (!e.shiftKey && document.activeElement === last) { first.focus(); e.preventDefault(); }
  };

  /* ---- deep links: #dv=<id>&step=2&with=<id2> ---- */
  Viewer.prototype.setHash = function () {
    if (!history.replaceState || !this.isOpen()) return;
    var e = this.panes[0] && this.panes[0].entry;
    if (!e || e.adhoc) return;
    var q = "dv=" + encodeURIComponent(e.id);
    if (this.steps && this.stepIdx >= 0) q += "&step=" + (this.stepIdx + 1);
    var b = this.panes[1] && this.panes[1].entry; if (b && !b.adhoc) q += "&with=" + encodeURIComponent(b.id);
    history.replaceState(null, "", location.pathname + location.search + "#" + q);
  };
  Viewer.prototype.fromHash = function () {
    var m = /(?:^#|&)dv=([^&]+)/.exec(location.hash);
    if (!m) return;
    var self = this, id = decodeURIComponent(m[1]);
    var stepM = /step=(\d+)/.exec(location.hash), withM = /with=([^&]+)/.exec(location.hash);
    manifest().then(function (mf) {
      var list = mf.diagrams, i = list.findIndex(function (d) { return d.id === id; });
      if (i < 0) return;
      var other = withM ? list.find(function (d) { return d.id === decodeURIComponent(withM[1]); }) : null;
      self.open(list, i, { walk: !!stepM, step: stepM ? +stepM[1] - 1 : 0, split: other || null });
    });
  };

  var viewer;
  function getViewer() { if (!viewer) viewer = new Viewer(); return viewer; }

  /* ------------------------------------------------------------------ figures on pages */
  function openFrom(figEntry, pageEntries, all, opts) {
    var seen = {}, list = [];
    pageEntries.concat(all.filter(function (d) { return d.group === figEntry.group; })).concat(all).forEach(function (d) { if (!seen[d.url]) { seen[d.url] = 1; list.push(d); } });
    var i = list.findIndex(function (d) { return d.url === figEntry.url; });
    if (i < 0) { list.unshift(figEntry); i = 0; }
    getViewer().open(list, i, opts);
  }
  function upgradePage(m) {
    var scope = $(".md-content") || document;
    var imgs = $$("img", scope).filter(function (img) { return /\.svg(\?|#|$)/.test(img.getAttribute("src") || "") && !img.closest(".dv-card, .dv-thumb, .dv-overlay, .no-viewer, .dv-fig") && !img.closest(".headerlink"); });
    var entries = imgs.map(function (img) { return entryFor(m, img.src, img.alt); });
    imgs.forEach(function (img, idx) {
      var entry = entries[idx];
      var bar = h("div", { class: "dv-fig-bar" });
      var fig = h("figure", { class: "dv-fig", tabindex: "0", role: "button", "aria-label": "Open diagram: " + (img.alt || entry.title) });
      var open = function (opts) { openFrom(entry, entries, m.diagrams, opts); };
      bar.appendChild(btn("expand", "Explore", function (e) { e.stopPropagation(); open(); }, { title: "Open in the viewer: zoom, pan, fit" }));
      if (entry.stepsUrl) bar.appendChild(btn("route", "Walk through", function (e) { e.stopPropagation(); open({ walk: true }); }, { title: "Step by step" }));
      fig.addEventListener("click", function (e) { if (e.target.closest(".dv-fig-bar")) return; e.preventDefault(); open(); });
      fig.addEventListener("keydown", function (e) { if (e.target === fig && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); open(); } });
      var host = img.closest("a");
      var linkedToSelf = host && stripHash(host.href) === stripHash(img.src);
      var node = linkedToSelf ? host : img;
      node.replaceWith(fig);
      img.loading = "lazy"; img.removeAttribute("width"); img.removeAttribute("height");
      fig.appendChild(img); fig.appendChild(bar);
      fig.appendChild(h("span", { class: "dv-fig-badge" }, icon("search"), document.createTextNode(entry.stepsUrl ? "Click to explore · walkthrough available" : "Click to zoom and explore")));
      fig.dvEntry = entry;
    });
    $$(".diagram-pair", scope).forEach(function (pair) {
      var figs = $$("figure.dv-fig", pair);
      if (figs.length < 2) return;
      var a = figs[0].dvEntry, b = figs[1].dvEntry;
      pair.appendChild(h("div", { class: "dv-pair-bar" },
        btn("columns", "Open side by side", function () { openFrom(a, [a, b], m.diagrams, { split: b }); }, { title: "Zoom both diagrams independently, or link them" })));
    });
  }
  function pageBar() {
    var det = $$(".md-content details");
    if (det.length < 2) return;
    var h1 = $(".md-content h1");
    if (!h1 || $(".dv-pagebar")) return;
    var bar = h("div", { class: "dv-pagebar" },
      btn("chevrons", "Expand all", function () { det.forEach(function (d) { d.open = true; }); }, { title: "Expand every collapsible section" }),
      btn("rows", "Collapse all", function () { det.forEach(function (d) { d.open = false; }); }, { title: "Collapse every collapsible section" }));
    h1.insertAdjacentElement("afterend", bar);
  }

  /* ------------------------------------------------------------------ cards and the gallery */
  function card(d, opts) {
    opts = opts || {};
    var meta = h("div", { class: "meta" });
    if (d.group) meta.appendChild(h("span", { class: "dv-tag board", text: d.group }));
    (d.tags || []).slice(0, 2).forEach(function (t) { meta.appendChild(h("span", { class: "dv-tag", text: t })); });
    if (d.stepsUrl) meta.appendChild(h("span", { class: "dv-tag walk", text: "▶ walkthrough" }));
    var el = h("article", { class: "dv-card", tabindex: "0", role: "button", "aria-label": "Open diagram: " + d.title },
      h("div", { class: "thumb" }, h("img", { src: d.url, alt: "", loading: "lazy" })),
      h("div", { class: "body" }, h("h3", { text: d.title }), h("p", { text: d.description }), meta));
    if (opts.selectable) {
      var sel = h("button", { class: "dv-sel", type: "button", "aria-pressed": "false", title: "Select to compare", "aria-label": "Select " + d.title + " to compare", onclick: function (e) { e.stopPropagation(); var on = sel.getAttribute("aria-pressed") !== "true"; sel.setAttribute("aria-pressed", String(on)); opts.onSelect(d, on); } }, icon("check"));
      el.appendChild(sel);
    }
    el.addEventListener("click", function () { opts.onOpen(d); });
    el.addEventListener("keydown", function (e) { if (e.target === el && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); opts.onOpen(d); } });
    return el;
  }
  function initGallery(host, m) {
    var all = m.diagrams, selected = [], state = { q: "", group: "", tag: "", view: "" };
    var groups = [], tags = [];
    all.forEach(function (d) { if (d.group && groups.indexOf(d.group) < 0) groups.push(d.group); (d.tags || []).forEach(function (t) { if (tags.indexOf(t) < 0) tags.push(t); }); });
    var search = h("input", { type: "search", placeholder: "Search " + all.length + " diagrams…", "aria-label": "Search diagrams" });
    var count = h("div", { class: "dv-count-line", "aria-live": "polite" });
    var grid = h("div", { class: "dv-grid" });
    var bar = h("div", { class: "dv-compare-bar", hidden: true });
    function chips(label, items, key) {
      var wrap = h("div", { class: "dv-chips", role: "group", "aria-label": label });
      [""].concat(items).forEach(function (v) {
        var c = h("button", { class: "dv-chip", type: "button", "aria-pressed": String(state[key] === v), text: v || "All " + label.toLowerCase(), onclick: function () { state[key] = v; $$(".dv-chip", wrap).forEach(function (x) { x.setAttribute("aria-pressed", String(x === c)); }); render(); } });
        wrap.appendChild(c);
      });
      return wrap;
    }
    var views = h("div", { class: "dv-chips" },
      [["", "grid", "Cards"], ["large", "grid", "Large"], ["list", "rows", "List"]].map(function (v) {
        var b = btn(v[1], v[2], function () { state.view = v[0]; grid.className = "dv-grid " + v[0]; $$("button", views).forEach(function (x) { x.setAttribute("aria-pressed", String(x === b)); }); }, { title: v[2] + " view" });
        b.setAttribute("aria-pressed", String(v[0] === "")); b.style.height = "42px";
        return b;
      }));
    host.appendChild(h("div", { class: "dv-gal-controls" }, h("label", { class: "dv-search" }, icon("search"), search), views));
    host.appendChild(chips("Boards", groups, "group"));
    host.appendChild(chips("Topics", tags, "tag"));
    host.appendChild(count); host.appendChild(grid); host.appendChild(bar);
    search.addEventListener("input", function () { state.q = search.value.toLowerCase(); render(); });
    function filtered() {
      return all.filter(function (d) {
        if (state.group && d.group !== state.group) return false;
        if (state.tag && (d.tags || []).indexOf(state.tag) < 0) return false;
        if (state.q && (d.title + " " + d.description + " " + d.group + " " + (d.tags || []).join(" ")).toLowerCase().indexOf(state.q) < 0) return false;
        return true;
      });
    }
    function updateBar() {
      bar.hidden = selected.length < 2;
      if (selected.length < 2) return;
      bar.textContent = "";
      bar.appendChild(h("span", { text: selected.length + " selected" }));
      var a = selected[selected.length - 2], b = selected[selected.length - 1];
      bar.appendChild(btn("columns", "Compare “" + a.title.slice(0, 26) + "” and “" + b.title.slice(0, 26) + "”", function () { openFrom(a, [a, b], all, { split: b }); }, { cls: "primary", text: true }));
      bar.appendChild(btn("close", "Clear", function () { selected = []; $$(".dv-sel", grid).forEach(function (s) { s.setAttribute("aria-pressed", "false"); }); updateBar(); }, { text: false, title: "Clear selection" }));
    }
    function render() {
      var list = filtered();
      grid.textContent = "";
      count.textContent = list.length + " of " + all.length + " diagrams";
      if (!list.length) { grid.appendChild(h("div", { class: "dv-empty", text: "No diagrams match. Try a different word or clear a filter." })); return; }
      list.forEach(function (d) {
        grid.appendChild(card(d, {
          selectable: true,
          onOpen: function (x) { var i = list.indexOf(x); getViewer().open(list, i); },
          onSelect: function (x, on) { selected = selected.filter(function (s) { return s !== x; }); if (on) selected.push(x); updateBar(); }
        }));
      });
    }
    render();
  }
  function initFeatured(host, m) {
    var n = +host.getAttribute("data-limit") || 6;
    var list = m.diagrams.filter(function (d) { return d.stepsUrl; });
    if (list.length < n) list = list.concat(m.diagrams.filter(function (d) { return !d.stepsUrl; }));
    list = list.slice(0, n);
    var grid = h("div", { class: "dv-grid" });
    list.forEach(function (d, i) { grid.appendChild(card(d, { onOpen: function () { getViewer().open(list, i, { walk: !!d.stepsUrl }); } })); });
    host.appendChild(grid);
  }

  /* ------------------------------------------------------------------ validation (used by the site checks) */
  function validate() {
    var v = getViewer(), out = [], stats = [];
    return manifest().then(function (m) {
      var withSteps = m.diagrams.filter(function (d) { return d.stepsUrl; });
      var chain = Promise.resolve();
      withSteps.forEach(function (d) {
        chain = chain.then(function () {
          v.open([d], 0);
          return new Promise(function (r) { window.setTimeout(r, 250); }).then(function () { return fetchSteps(d.stepsUrl); }).then(function (data) {
            var pane = v.panes[0];
            (data.steps || []).forEach(function (s, i) {
              var res = pane.resolveStep(s);
              if (res.missing.length) out.push({ diagram: d.id, step: i + 1, missing: res.missing });
              var area = 0;
              res.regions.forEach(function (r) { area += r.w * r.h; });
              stats.push({ diagram: d.id, step: i + 1, pct: Math.round(1000 * area / (pane.w * pane.h)) / 10, n: res.regions.length });
            });
            v.close();
            return new Promise(function (r) { window.setTimeout(r, 220); });
          });
        });
      });
      return chain.then(function () { return { checked: withSteps.length, problems: out, stats: stats }; });
    });
  }

  /* ------------------------------------------------------------------ boot */
  function init() {
    manifest().then(function (m) {
      upgradePage(m);
      pageBar();
      var g = document.getElementById("dv-gallery"); if (g && !g.dataset.ready) { g.dataset.ready = "1"; initGallery(g, m); }
      $$(".dv-featured").forEach(function (f) { if (!f.dataset.ready) { f.dataset.ready = "1"; initFeatured(f, m); } });
      getViewer().fromHash();
    });
  }
  if (/[?&]dvcheck\b/.test(location.search)) {
    window.addEventListener("load", function () {
      validate().then(function (r) { document.body.appendChild(h("pre", { id: "dv-check-result", text: JSON.stringify(r) })); });
    });
  }
  if (window.document$ && window.document$.subscribe) window.document$.subscribe(init);
  else if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();

  window.DV = { open: function (id, opts) { return manifest().then(function (m) { var i = m.diagrams.findIndex(function (d) { return d.id === id; }); if (i >= 0) getViewer().open(m.diagrams, i, opts); }); }, manifest: manifest, validate: validate, viewer: getViewer };
})();
