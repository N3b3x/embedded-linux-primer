# Authoring interactive diagrams

Every SVG in `docs/images/` (and in each board's `docs/images/`) is picked up by the documentation
site automatically: it becomes a card in the diagram gallery (the **Diagrams** tab of the site), and a click
anywhere it appears opens it in the viewer. This page explains how to give a diagram a
**walkthrough**, how to put two diagrams **side by side**, and how to check your work.

Reader-facing help (zoom, pan, shortcuts) is on the gallery page. Press `?` inside the viewer for the
shortcut sheet.

## What you get for free

For any `name.svg` the build generates an entry in `assets/diagrams.json`:

| Field | Comes from |
| --- | --- |
| `title` | the first `<text>` in the SVG (the generators draw the title there) |
| `description` | the SVG's `aria-label`. Write it as the one-paragraph claim the picture makes |
| `group` | the board the file is in, or "Concepts" |
| `tags` | keywords in the file name (`boot`, `storage`, `security`, `build`…) |
| order | where the diagram first appears in the text, README first, then chapters |

So a good file name and a good `aria-label` are the whole job for a diagram that needs no walkthrough.

## A walkthrough

Put `name.steps.json` next to `name.svg`. The build copies it, the gallery card gets a
**▶ walkthrough** tag, and the viewer shows a **Walk through** button. In the viewer the part being
explained stays bright, the rest is dimmed, and the view zooms to it.

```json
{
  "title": "Optional title of the tour",
  "steps": [
    {
      "anchor": null,
      "title": "The whole picture first",
      "body": "A short opening. **Bold**, `code` and [links](https://example.com) work."
    },
    {
      "anchor": "TF-A BL31",
      "up": 1,
      "title": "BL31 stays resident",
      "body": "One idea per step, 2 to 4 sentences. A blank line starts a new paragraph."
    }
  ]
}
```

### Keys of a step

| Key | Meaning |
| --- | --- |
| `anchor` | what to highlight: a string, a list of strings (several regions at once), or `null` for "no highlight, show everything". See below |
| `title` | the heading of the step (required) |
| `body` | the explanation (required): Markdown-lite, `**bold**`, `` `code` ``, `[text](url)`, blank line = paragraph |
| `up` | grow the highlight to a larger enclosing box: `0` (default) is the smallest box around the text, `1` the next one out, and so on |
| `nth` | when the anchor text appears more than once, use the n-th match (counting from `0`) |
| `pad` | extra margin around the highlight, in diagram units (default `8`) |
| `exact` | `true` highlights only the text itself, with no enclosing box |

### Anchors

An anchor is looked up **in the SVG**, so it survives layout changes, which a coordinate would not.

| Anchor | Matches |
| --- | --- |
| `"TF-A BL31"` | a `<text>` element whose text is exactly this; if there is none, the first one that *contains* it. The highlight is the smallest `<rect>` around that text (a card, a table cell…); use `up` to widen it |
| `"id:my-group"` | the element with that `id` (give a `<g>` an id in the generator when no text will do) |
| `"rect:x,y,w,h"` | explicit coordinates in the diagram's own units (the `viewBox`), the last resort |
| `["A", "B"]` | several regions highlighted together; the view fits all of them |

Tips:

- Anchor on a **short, stable** piece of text such as a card title, not on a sentence that someone
  will reword.
- If the box is too small, add `"up": 1`. If it swallows the whole diagram, drop `up` or use `exact`.
- Open with a step whose anchor is `null` so readers see the whole picture, then walk in reading
  order, and close with the takeaway.
- A diagram of five boxes needs five steps, not fifteen. A step is one idea.
- Write for someone who has not read the chapter. Say **what it is**, **what it does here**, and
  **what goes wrong without it**.

### Checking

```bash
python3 tools/check-steps.py       # every anchor matches text in its SVG (fast, runs in CI)
python3 tools/build-site.py        # then:
tools/check-steps.sh               # resolves every step in headless Chrome against the real layout
```

`tools/check-steps.sh` needs Chrome or Chromium; it reports the diagram, the step and the anchor that
did not resolve.

## Two diagrams side by side

Wrap two images in a `diagram-pair` block. On a wide screen they sit next to each other and each
one opens in the viewer; a button opens **both** in the two-pane view, where each pane zooms
independently (or together, with `l`).

```markdown
<div class="diagram-pair" markdown>

![What happens on an smc](images/smc-flow.svg)

![How TrustZone is enforced](images/trustzone.svg)

</div>
```

Keep the blank lines: they make the block render correctly on GitHub as well.

## Writing diagrams that work in the viewer

- Draw them with the generator kit (`docs/images/_src/kit.py`) so the colours mean the same thing on
  every board. Regenerate with `tools/diagrams.sh`; CI fails if a committed SVG differs from its
  generator.
- Put real words in `<text>` elements. Text drawn as outlines cannot be anchored, searched or read
  by a screen reader.
- Give every diagram a `role="img"` and an `aria-label` that states what it shows. The gallery
  shows it as the card's description.
- Do not put `<script>` or event handlers in an SVG. The viewer injects it into a shadow root, which
  keeps its `<style>` from leaking into the page, and adds the highlight itself.
- Keep one idea per diagram. Two ideas that belong together are a `diagram-pair`.
