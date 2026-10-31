# Contributing

The rules for a board directory are in [the board contract](docs/board-contract.md). In short:

- every board answers the same commands (`deps`, `info`, `all`, `flash`, `--dry-run`), pins every source
  and download, and documents each step in numbered chapters with diagrams;
- scripts pass `shellcheck -x` and complete in `--dry-run` on Ubuntu 24.04;
- diagrams are generated (`tools/diagrams.sh`), never edited by hand, and CI fails when a committed
  SVG differs from its generator;
- say in the board's status table exactly what was verified, and how. Never claim a hardware boot that
  was not performed.

## Before you push

```bash
tools/diagrams.sh                       # regenerate the SVGs
python3 tools/check-links.py            # every relative link resolves
pip install -r requirements-docs.txt    # once
python3 tools/build-site.py --strict    # builds the documentation site; any warning fails
python3 tools/build-site.py --serve     # or preview it at http://127.0.0.1:8000
```

Each board's own checks (from inside its directory): `shellcheck -x build.sh scripts/*.sh scripts/lib/*.sh`
and `./build.sh --dry-run all`.

## The documentation site

`tools/build-site.py` gathers `docs/`, each board's `README.md` and `docs/`, and the landing page in
`site/`, rewrites the relative links, generates the navigation and runs MkDocs (configuration in
`mkdocs.yml`). A push to `main` that touches documentation publishes it to GitHub Pages with
`.github/workflows/pages.yml`.

Write documentation as ordinary Markdown next to the code, with relative links; the site build turns
links to files that are not pages (scripts, configs) into links to the file on GitHub.
