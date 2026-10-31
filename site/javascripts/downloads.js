/* "Latest builds" for the downloads page.
   Renders <div id="dv-downloads"> from assets/releases.json, which tools/release/fetch-releases.py writes
   at site build time (the GitHub Pages workflow). Nothing here talks to GitHub: the page is static, and
   the file is empty when the build could not read the releases (then the page says so).
   Styles: stylesheets/downloads.css, on top of diagrams.css. */
(function () {
  "use strict";
  var SCRIPT = document.currentScript;
  var ROOT = SCRIPT ? new URL("../", SCRIPT.src) : new URL("../", location.href);

  function h(tag, attrs, kids) {
    var e = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === "text") e.textContent = attrs[k];
      else if (k === "class") e.className = attrs[k];
      else if (k.slice(0, 2) === "on") e.addEventListener(k.slice(2), attrs[k]);
      else if (attrs[k] !== false && attrs[k] != null) e.setAttribute(k, attrs[k]);
    });
    (kids || []).forEach(function (c) { if (c) e.appendChild(typeof c === "string" ? document.createTextNode(c) : c); });
    return e;
  }
  function safeUrl(u) { return typeof u === "string" && /^https:\/\/github\.com\//.test(u) ? u : "#"; }
  function size(n) {
    if (n >= 1e9) return (n / 1e9).toFixed(2) + " GB";
    if (n >= 1e6) return (n / 1e6).toFixed(n >= 1e8 ? 0 : 1) + " MB";
    return Math.max(1, Math.round(n / 1e3)) + " kB";
  }
  function day(iso) { return iso ? String(iso).slice(0, 10) : ""; }

  function copy(text, button) {
    function done() { var old = button.textContent; button.textContent = "Copied"; setTimeout(function () { button.textContent = old; }, 1400); }
    if (navigator.clipboard && window.isSecureContext) { navigator.clipboard.writeText(text).then(done, fallback); } else fallback();
    function fallback() {
      var t = h("textarea", { "aria-hidden": "true", style: "position:fixed;opacity:0" });
      t.value = text; document.body.appendChild(t); t.select();
      try { document.execCommand("copy"); done(); } catch (e) { window.prompt("Copy the sha256:", text); }
      document.body.removeChild(t);
    }
  }

  /* newest release first; the newest build of every image wins. Verified images come from normal releases,
     the others from the <tag>-preview pre-releases: two streams, shown apart. */
  function pickCards(data) {
    var seen = {}, stable = [], preview = [];
    data.releases.forEach(function (rel) {
      rel.images.forEach(function (im) {
        if (seen[im.name + "|" + im.role]) return;
        seen[im.name + "|" + im.role] = true;
        (rel.prerelease || !im.verified ? preview : stable).push({ rel: rel, im: im });
      });
    });
    return { stable: stable, preview: preview };
  }

  function card(c) {
    var im = c.im, rel = c.rel;
    var chips = [h("span", { class: "dv-tag board", text: im.version ? "v" + String(im.version).replace(/^v/, "") : rel.tag })];
    if (rel.prerelease) chips.push(h("span", { class: "dv-tag dl-chip-pre", text: "preview" }));
    else if (rel.latest) chips.push(h("span", { class: "dv-tag walk", text: "latest" }));
    chips.push(im.verified
      ? h("span", { class: "dv-tag dl-chip-ok", title: im.verified_text || "", text: "verified on hardware" })
      : h("span", { class: "dv-tag dl-chip-pre", text: "not verified" }));

    var hash = h("div", { class: "dl-hash" }, [
      h("code", { title: im.sha256, text: im.sha256.slice(0, 16) + "…" }),
      h("button", { class: "dv-btn", type: "button", "aria-label": "Copy the full sha256 of " + im.file, text: "Copy", onclick: function (ev) { copy(im.sha256, ev.currentTarget); } })
    ]);
    var kv = h("dl", { class: "dl-kv" }, [
      h("dt", { text: "File" }), h("dd", {}, [h("code", { text: im.file })]),
      h("dt", { text: "Size" }), h("dd", { text: size(im.size) }),
      h("dt", { text: "sha256" }), h("dd", {}, [hash]),
      h("dt", { text: "Built" }), h("dd", { text: day(im.build_date) + (im.commit ? " · " + im.commit.slice(0, 9) : "") })
    ]);

    var actions = [h("a", { class: "dv-btn primary", href: safeUrl(im.latest_url || im.url), rel: "noopener" }, ["Download"])];
    if (im.bmap_url) actions.push(h("a", { class: "dv-btn", href: safeUrl(im.bmap_url), rel: "noopener", title: "block map for bmaptool (optional)" }, [".bmap"]));
    actions.push(h("a", { class: "dv-btn ghost", href: safeUrl(rel.url), rel: "noopener" }, ["Release page"]));

    var body = [h("h4", { text: im.title || im.name }), h("p", { class: "dl-sub", text: im.name }), h("div", { class: "meta" }, chips), kv];
    if (!im.verified) {
      body.push(h("p", { class: "dl-warn", role: "note" }, [
        h("strong", { text: "Not booted on hardware. " }),
        (im.verified_text || "This image has not been verified on a real board") + ". It may not boot; use it next to a serial console."
      ]));
    } else if (im.verified_text) {
      body.push(h("p", { class: "dl-sub", text: "Verified: " + im.verified_text }));
    }
    if (rel.prerelease) body.push(h("p", { class: "dl-sub", text: "Preview build: not part of the stable download links. This button links this exact pre-release." }));
    body.push(h("div", { class: "dl-actions" }, actions));
    return h("article", { class: "dv-card dl-card" }, [h("div", { class: "body" }, body)]);
  }

  function render(root, data) {
    root.textContent = "";
    root.classList.add("dl-root");
    var releases = (data && data.releases) || [];
    if (!releases.length) {
      var why = data && data.error ? " (" + data.error + ")" : "";
      root.appendChild(h("div", { class: "dl-empty" }, [
        h("p", {}, [h("strong", { text: "No published release to show yet" + why + "." })]),
        h("p", { text: "Releases are created by the images workflow when a v* tag is pushed or when it is started by hand with “publish”. Until then, builds of a single run are available as workflow artifacts for 14 days:" }),
        h("p", {}, [h("a", { class: "dv-btn", href: safeUrl(data && data.actions_url), rel: "noopener" }, ["Open the images workflow runs"])])
      ]));
      return;
    }

    var latest = releases.filter(function (r) { return r.latest; })[0];
    var status = h("div", { class: "dl-status" }, [
      latest ? h("span", {}, ["Latest release ", h("a", { href: safeUrl(latest.url), text: latest.tag }), " · published " + day(latest.published_at)])
             : h("span", { text: "No full release yet: only pre-releases (some images are not verified on hardware)." }),
      h("span", { text: "· page built " + day(data.generated) })
    ]);
    root.appendChild(status);

    var picked = pickCards(data), all = picked.stable.concat(picked.preview);
    var boards = [], titles = {}, sections = [];
    all.forEach(function (c) { if (boards.indexOf(c.im.board) < 0) boards.push(c.im.board); titles[c.im.board] = c.im.board_title || c.im.board; });

    var chips = h("div", { class: "dv-chips", role: "group", "aria-label": "Filter by board" });
    function chip(label, id) {
      var b = h("button", { class: "dv-chip", type: "button", "aria-pressed": id === "all" ? "true" : "false", text: label, onclick: function () {
        Array.prototype.forEach.call(chips.children, function (x) { x.setAttribute("aria-pressed", String(x === b)); });
        sections.forEach(function (sec) { sec.hidden = !(id === "all" || id === sec.dataset.board); });
      } });
      chips.appendChild(b);
    }
    chip("All boards", "all");
    boards.forEach(function (b) { chip(titles[b], b); });
    if (boards.length > 1) root.appendChild(chips);

    function stream(list, heading, intro, warn) {
      if (!list.length) return;
      var wrap = h("section", { class: "dl-stream" + (warn ? " dl-stream-preview" : ""), "aria-label": heading }, [
        h("h2", {}, [heading, warn ? h("span", { class: "dv-tag dl-chip-pre", text: "not verified on hardware" }) : h("span", { class: "dv-tag dl-chip-ok", text: "verified" })]),
        h("p", { class: warn ? "dl-warn" : "dl-sub", text: intro })
      ]);
      root.appendChild(wrap);
      boards.forEach(function (b) {
        var mine = list.filter(function (c) { return c.im.board === b; });
        if (!mine.length) return;
        var grid = h("div", { class: "dv-grid dl-grid" });
        mine.forEach(function (c) { grid.appendChild(card(c)); });
        var sec = h("section", { class: "dl-board", "data-board": b, "aria-label": titles[b] }, [h("h3", {}, [titles[b]]), grid]);
        sections.push(sec); wrap.appendChild(sec);
      });
    }
    stream(picked.stable, "Verified images", "Booted on real hardware. These are the files behind the stable releases/latest/download links.", false);
    stream(picked.preview, "Previews", "Built by the same workflow but never booted on a real board: they may not boot at all. Use them for bring-up, next to a serial console. A board moves to the verified list when verified_on_hardware is set to true in tools/release/images.json after someone has booted it.", true);

    var list = h("ul", {});
    releases.forEach(function (r) {
      list.appendChild(h("li", {}, [
        h("a", { class: "tag", href: safeUrl(r.url), text: r.tag }),
        r.prerelease ? h("span", { class: "dv-tag dl-chip-pre", text: "preview" }) : (r.latest ? h("span", { class: "dv-tag walk", text: "latest" }) : null),
        h("span", { text: r.files.length + " files" }),
        h("span", { class: "when", text: day(r.published_at) })
      ]));
    });
    root.appendChild(h("section", { class: "dl-releases", "aria-label": "All releases" }, [
      h("h3", { text: "All releases" }), list,
      h("p", { class: "dl-note" }, [
        "Releases are the durable copy. Builds of a single run that were not published are workflow artifacts and expire after 14 days: ",
        h("a", { href: safeUrl(data.actions_url), rel: "noopener", text: "images workflow runs" }), ". ",
        h("a", { href: safeUrl(data.releases_url), rel: "noopener", text: "All releases on GitHub" }), "."
      ])
    ]));
  }

  function init() {
    var root = document.getElementById("dv-downloads");
    if (!root || root.dataset.ready) return;
    root.dataset.ready = "1";
    root.appendChild(h("p", { class: "dl-note", text: "Loading the latest builds…" }));
    fetch(new URL("assets/releases.json", ROOT)).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (d) { render(root, d); })
      .catch(function () { render(root, { releases: [], error: "releases.json could not be loaded", actions_url: "", releases_url: "" }); });
  }
  if (window.document$ && window.document$.subscribe) window.document$.subscribe(init);
  else if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
