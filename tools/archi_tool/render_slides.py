"""Render slide decks from a .archimate model to standalone HTML.

A deck is a TOML file (decks/*.toml) telling one linear story: title,
sections, embedded views, prose and bullets, closing. View slides embed
the real diagram via render_html.diagram_canvas, so the architecture
content always comes from the model; the deck file only carries the
narrative. Every deck renders to a single self-contained HTML file:
inline CSS and vanilla JS, with the pinned NLDD CSS from the CDN as the
only external reference (the deck uses NLDD design tokens, not web
components, so the component bundle is not loaded). Output is
deterministic: no timestamps (the optional title date comes verbatim
from the deck file), stable ordering, marker comment first line.
"""
from __future__ import annotations

import html
import tomllib
from pathlib import Path

from .model import ModelError
from .render import MARKER, slugify, write_if_changed
from .render_html import (DIAGRAM_CSS, FAVICON, NLDD_CSS, diagram_canvas,
                          layer_css, legend_html)

RIJKSBLAUW = "#154273"
GOUD = "#ffb612"

DECK_KEYS = {"title", "slug", "speaker", "affiliation", "date", "lead",
             "slides"}
SLIDE_KEYS = {
    "title": {"type", "title", "lead", "notes"},
    "section": {"type", "title", "lead", "notes"},
    "view": {"type", "view", "title", "intro", "notes"},
    "text": {"type", "title", "lead", "body", "notes"},
    "bullets": {"type", "title", "lead", "bullets", "gov", "notes"},
    "closing": {"type", "title", "lead", "link", "notes"},
}
REQUIRED_SLIDE_KEYS = {
    "section": ("title",),
    "view": ("view",),
    "text": ("body",),
    "bullets": ("title", "bullets"),
    "closing": ("title",),
}

DECK_CSS = """\
    html, body { margin: 0; height: 100%; overflow: hidden; }
    body { background: #154273;
      font-family: var(--primitives-font-family-sans-serif,
        system-ui, sans-serif); color: #ffffff; }
    .slide { position: fixed; inset: 0; box-sizing: border-box;
      display: flex; flex-direction: column; justify-content: center;
      padding: 3rem clamp(2.5rem, 9vw, 11rem); overflow: hidden;
      opacity: 0; visibility: hidden; transition: opacity 0.35s ease; }
    .slide.active { opacity: 1; visibility: visible; }
    /* chapter slides are Rijksblauw; the diagram canvas stays light,
       consistent with the standalone view pages */
    .slide.dark { background: #154273; color: #ffffff; }
    .slide.light { background: #ffffff; color: #202030; }
    .slide h1, .slide h2 {
      font-family: var(--primitives-font-family-serif, Georgia, serif);
      font-weight: 700; line-height: 1.08; margin: 0; }
    .accent { width: 72px; height: 6px; background: #ffb612;
      border-radius: 3px; margin-bottom: 1.6rem; flex: none; }
    .lead { font-size: clamp(1.2rem, 2.2vw, 1.9rem); line-height: 1.35;
      max-width: 60ch; margin: 1.2rem 0 0; opacity: 0.92; }
    .slide-title h1 { font-size: clamp(2.6rem, 6.5vw, 6rem); }
    .byline { margin-top: 3rem; display: flex; flex-wrap: wrap;
      gap: 0.4rem 1.6rem; font-size: 1.05rem; opacity: 0.85; }
    .byline .speaker { font-weight: 600; }
    .slide-section h2 { font-size: clamp(2.4rem, 5.5vw, 5rem); }
    .slide-bullets h2, .slide-text h2 {
      font-size: clamp(2rem, 4vw, 3.4rem); }
    ul.bullets { margin: 2rem 0 0; padding: 0; list-style: none;
      display: grid; gap: 1.1rem; max-width: 62ch;
      font-size: clamp(1.15rem, 2vw, 1.7rem); line-height: 1.4; }
    ul.bullets li { padding-left: 1.6rem; position: relative; }
    ul.bullets li::before { content: ""; position: absolute; left: 0;
      top: 0.55em; width: 0.55rem; height: 0.55rem; border-radius: 50%;
      background: #ffb612; }
    .gov-pill { display: inline-flex; align-self: flex-start;
      margin-top: 2.2rem; padding: 0.35rem 0.9rem; border-radius: 999px;
      border: 1px solid #ffb612; color: #ffb612; font-size: 0.85rem;
      font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase; }
    .gov-note { margin: 0.7rem 0 0; font-size: 1.05rem; opacity: 0.9;
      max-width: 60ch; }
    .prose { margin: 1.6rem 0 0; display: grid; gap: 0.9rem;
      font-size: clamp(1.05rem, 1.8vw, 1.45rem); line-height: 1.5;
      max-width: 65ch; }
    .prose p { margin: 0; }
    /* extra bottom padding keeps the legend clear of the fixed chrome */
    .slide-view { padding: 2.2rem clamp(2rem, 5vw, 4.5rem) 3.4rem; }
    .view-head { flex: none; }
    .slide-view h2 { font-size: clamp(1.5rem, 2.6vw, 2.4rem);
      color: #154273; }
    .slide-view .intro { margin: 0.4rem 0 0; font-size: 0.95rem;
      line-height: 1.4; color: #55555e; max-width: 110ch; }
    /* the fit wrapper positions and scales the fixed-size diagram; the
       transform itself is computed client-side (fitDiagrams) */
    .view-fit { flex: 1; position: relative; overflow: hidden;
      margin-top: 1rem; min-height: 0; }
    .view-fit .diagram { position: absolute; left: 0; top: 0; }
    .view-foot { display: flex; align-items: center; flex: none;
      justify-content: space-between; gap: 1rem; }
    .view-foot .legend { border-top: 0; padding: 0; }
    .view-open { font-size: 0.85rem; color: #154273; white-space: nowrap; }
    .slide-closing { align-items: center; text-align: center; }
    .slide-closing .accent { margin-left: auto; margin-right: auto; }
    .slide-closing h2 { font-size: clamp(2.6rem, 6vw, 5.5rem); }
    .slide-closing .lead { margin-left: auto; margin-right: auto; }
    .closing-link { margin-top: 2.5rem; font-size: 1.15rem; }
    .closing-link a { color: #ffb612; }
    .slide .notes { display: none; }
    .hint { position: fixed; left: 1.1rem; bottom: 1rem; z-index: 10;
      font-size: 0.75rem; color: #ffffff; opacity: 0.75;
      background: rgb(21 66 115 / 0.85); padding: 0.25rem 0.7rem;
      border-radius: 999px; }
    .chrome { position: fixed; right: 1.1rem; bottom: 1rem; z-index: 10;
      display: flex; align-items: center; gap: 0.6rem; }
    .counter {
      font-family: var(--primitives-font-family-monospace, monospace);
      font-size: 0.8rem; letter-spacing: 0.06em; color: #ffffff;
      background: rgb(21 66 115 / 0.85); padding: 0.25rem 0.7rem;
      border-radius: 999px; }
    .counter.autoplay::before { content: "\\25B6  "; color: #ffb612; }
    .nav-btn { width: 2rem; height: 2rem; border-radius: 50%;
      border: 1px solid rgb(255 255 255 / 0.4); cursor: pointer;
      background: rgb(21 66 115 / 0.85); color: #ffffff;
      font-size: 1rem; line-height: 1; }
    .nav-btn:hover, .nav-btn:focus-visible { border-color: #ffb612; }
    .notes-panel { position: fixed; right: 1.1rem; bottom: 3.6rem;
      z-index: 12; width: min(420px, 80vw); max-height: 40vh;
      overflow: auto; background: #ffffff; color: #202030;
      border-radius: 12px; padding: 1rem 1.2rem;
      box-shadow: 0 8px 30px rgb(0 0 0 / 0.35); font-size: 0.95rem; }
    .notes-panel h3 { margin: 0 0 0.5rem; font-size: 0.8rem;
      text-transform: uppercase; letter-spacing: 0.05em; color: #55555e; }
    .progress { position: fixed; left: 0; right: 0; bottom: 0; height: 4px;
      z-index: 11; background: rgb(255 255 255 / 0.15); }
    .progress-fill { height: 100%; width: 0; background: #ffb612;
      transition: width 0.3s ease; }
    @page { size: A4 landscape; margin: 0; }
    @media print {
      html, body { overflow: visible; background: #ffffff; }
      .slide { position: relative; inset: auto; height: 100vh;
        opacity: 1; visibility: visible; transition: none;
        break-after: page; page-break-after: always; }
      .hint, .chrome, .notes-panel, .progress { display: none; }
    }
    @media (prefers-reduced-motion: reduce) {
      .slide, .progress-fill { transition: none; }
    }
"""

DECK_JS = """\
(function () {
  'use strict';
  var slides = Array.prototype.slice.call(
    document.querySelectorAll('.slide'));
  var total = slides.length;
  var counter = document.querySelector('.counter');
  var fill = document.querySelector('.progress-fill');
  var notesPanel = document.querySelector('.notes-panel');
  var notesBody = notesPanel.querySelector('.notes-body');
  var current = 0;
  var autoplayTimer = null;

  function pad(n) { return (n < 10 ? '0' : '') + n; }

  function fitDiagrams() {
    slides.forEach(function (slide) {
      var fit = slide.querySelector('.view-fit');
      if (!fit) { return; }
      var diagram = fit.querySelector('.diagram');
      var w = parseFloat(fit.getAttribute('data-w'));
      var h = parseFloat(fit.getAttribute('data-h'));
      var fw = fit.clientWidth;
      var fh = fit.clientHeight;
      if (!diagram || !w || !h || !fw || !fh) { return; }
      var s = Math.min(fw / w, fh / h, 1.4);
      diagram.style.transformOrigin = '0 0';
      diagram.style.transform = 'translate(' +
        ((fw - w * s) / 2).toFixed(1) + 'px, ' +
        ((fh - h * s) / 2).toFixed(1) + 'px) scale(' + s.toFixed(4) + ')';
    });
  }

  function updateNotes() {
    var notes = slides[current].querySelector('.notes');
    notesBody.innerHTML = notes ? notes.innerHTML
      : '<em>Geen notities bij deze slide.</em>';
  }

  function show(i) {
    current = Math.max(0, Math.min(total - 1, i));
    slides.forEach(function (slide, j) {
      slide.classList.toggle('active', j === current);
    });
    counter.textContent = pad(current + 1) + '/' + pad(total);
    fill.style.width = ((current + 1) / total * 100) + '%';
    if (('#' + (current + 1)) !== location.hash) {
      history.replaceState(null, '', '#' + (current + 1));
    }
    updateNotes();
  }

  function step(delta) {
    var next = current + delta;
    if (next >= total) { stopAutoplay(); return; }
    show(next);
  }

  function startAutoplay() {
    autoplayTimer = setInterval(function () { step(1); }, 6000);
    counter.classList.add('autoplay');
  }

  function stopAutoplay() {
    if (autoplayTimer) { clearInterval(autoplayTimer); autoplayTimer = null; }
    counter.classList.remove('autoplay');
  }

  function toggleFullscreen() {
    if (document.fullscreenElement) { document.exitFullscreen(); }
    else { document.documentElement.requestFullscreen(); }
  }

  function fromHash() {
    var n = parseInt(location.hash.slice(1), 10);
    return isNaN(n) ? 0 : n - 1;
  }

  document.addEventListener('keydown', function (event) {
    if (event.altKey || event.ctrlKey || event.metaKey) { return; }
    switch (event.key) {
      case 'ArrowRight': case 'PageDown': case ' ':
        event.preventDefault(); step(1); break;
      case 'ArrowLeft': case 'PageUp':
        event.preventDefault(); step(-1); break;
      case 'Home': event.preventDefault(); show(0); break;
      case 'End': event.preventDefault(); show(total - 1); break;
      case 'f': toggleFullscreen(); break;
      case 'n': notesPanel.hidden = !notesPanel.hidden; break;
      case 'a': autoplayTimer ? stopAutoplay() : startAutoplay(); break;
    }
  });

  Array.prototype.forEach.call(
    document.querySelectorAll('.nav-btn'), function (button) {
      button.addEventListener('click', function () {
        step(parseInt(button.getAttribute('data-nav'), 10));
      });
    });

  window.addEventListener('hashchange', function () { show(fromHash()); });
  window.addEventListener('resize', fitDiagrams);
  window.addEventListener('beforeprint', fitDiagrams);

  fitDiagrams();
  show(fromHash());
})();
"""


def load_deck(path: Path, model) -> dict:
    """Parse and validate a deck TOML; errors name the file (in Dutch)."""
    path = Path(path)
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ModelError(
            f"Deck '{path.as_posix()}' is geen geldige TOML: {exc}") from exc
    return validate_deck(data, model, source=path.as_posix(),
                         default_slug=slugify(path.stem))


def _check_str(value, source: str, where: str, key: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ModelError(f"Deck '{source}'{where}: '{key}' moet een "
                         f"niet-lege tekst zijn")
    return value


def _resolve_view(model, ref, source: str, n: int):
    diagrams = model.diagrams()
    for diagram in diagrams:
        if diagram.get("id") == ref:
            return diagram
    matches = [d for d in diagrams if (d.get("name") or "") == ref]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ModelError(f"Deck '{source}', slide {n}: viewnaam '{ref}' is "
                         f"niet uniek in het model; gebruik het view-id")
    names = ", ".join(sorted(d.get("name") or d.get("id")
                             for d in diagrams)) or "(geen)"
    raise ModelError(f"Deck '{source}', slide {n}: view '{ref}' bestaat "
                     f"niet in het model. Beschikbare views: {names}")


def validate_deck(deck: dict, model, source: str, default_slug: str) -> dict:
    """Normalize a raw deck dict; raise ModelError (Dutch) on any problem."""
    unknown = sorted(set(deck) - DECK_KEYS)
    if unknown:
        raise ModelError(f"Deck '{source}': onbekende sleutel "
                         f"'{unknown[0]}'. Toegestaan: "
                         + ", ".join(sorted(DECK_KEYS)))
    if "title" not in deck:
        raise ModelError(f"Deck '{source}': verplicht veld 'title' ontbreekt")
    title = _check_str(deck["title"], source, "", "title")
    for key in ("slug", "speaker", "affiliation", "date", "lead"):
        if key in deck:
            _check_str(deck[key], source, "", key)

    slug = slugify(deck.get("slug") or default_slug)

    raw_slides = deck.get("slides")
    if not isinstance(raw_slides, list) or not raw_slides:
        raise ModelError(f"Deck '{source}': 'slides' moet een niet-lege "
                         f"lijst van [[slides]]-tabellen zijn")

    slides = []
    for n, raw in enumerate(raw_slides, start=1):
        where = f", slide {n}"
        if not isinstance(raw, dict):
            raise ModelError(f"Deck '{source}'{where}: elke slide moet een "
                             f"[[slides]]-tabel zijn")
        kind = raw.get("type")
        if kind not in SLIDE_KEYS:
            raise ModelError(f"Deck '{source}'{where}: onbekend type "
                             f"'{kind}'. Toegestaan: "
                             + ", ".join(sorted(SLIDE_KEYS)))
        unknown = sorted(set(raw) - SLIDE_KEYS[kind])
        if unknown:
            raise ModelError(f"Deck '{source}'{where}: onbekende sleutel "
                             f"'{unknown[0]}'. Toegestaan voor type "
                             f"'{kind}': "
                             + ", ".join(sorted(SLIDE_KEYS[kind])))
        for key in REQUIRED_SLIDE_KEYS.get(kind, ()):
            if key not in raw:
                raise ModelError(f"Deck '{source}'{where}: verplicht veld "
                                 f"'{key}' ontbreekt voor type '{kind}'")
        slide = dict(raw)
        for key in ("title", "lead", "intro", "notes", "gov", "body"):
            if key in slide:
                _check_str(slide[key], source, where, key)
        if kind == "view":
            ref = _check_str(slide["view"], source, where, "view")
            slide["diagram"] = _resolve_view(model, ref, source, n)
        if kind == "bullets":
            bullets = slide["bullets"]
            if (not isinstance(bullets, list) or not bullets
                    or not all(isinstance(b, str) and b.strip()
                               for b in bullets)):
                raise ModelError(f"Deck '{source}'{where}: 'bullets' moet "
                                 f"een niet-lege lijst van teksten zijn")
        if kind == "closing" and "link" in slide:
            link = slide["link"]
            if isinstance(link, str):
                slide["link"] = {"href": link, "label": link}
            elif isinstance(link, dict) and isinstance(link.get("href"), str):
                slide["link"] = {"href": link["href"],
                                 "label": link.get("label") or link["href"]}
            else:
                raise ModelError(f"Deck '{source}'{where}: 'link' moet een "
                                 f"tekst of een tabel met 'href' (en "
                                 f"optioneel 'label') zijn")
        slides.append(slide)

    return {"title": title, "slug": slug,
            "speaker": deck.get("speaker"),
            "affiliation": deck.get("affiliation"),
            "date": deck.get("date"),
            "lead": deck.get("lead"), "slides": slides}


def _notes_html(slide: dict) -> str:
    notes = slide.get("notes")
    if not notes:
        return ""
    return f'<aside class="notes" hidden>{html.escape(notes)}</aside>'


def _slide_title(deck: dict, slide: dict) -> str:
    title = slide.get("title") or deck["title"]
    lead = slide.get("lead") or deck.get("lead")
    parts = ['<div class="accent"></div>', f"<h1>{html.escape(title)}</h1>"]
    if lead:
        parts.append(f'<p class="lead">{html.escape(lead)}</p>')
    byline = []
    if deck.get("speaker"):
        byline.append(f'<span class="speaker">'
                      f'{html.escape(deck["speaker"])}</span>')
    if deck.get("affiliation"):
        byline.append(f"<span>{html.escape(deck['affiliation'])}</span>")
    if deck.get("date"):
        byline.append(f"<span>{html.escape(deck['date'])}</span>")
    if byline:
        parts.append('<footer class="byline">' + "".join(byline)
                     + "</footer>")
    return "".join(parts)


def _slide_section(slide: dict) -> str:
    parts = ['<div class="accent"></div>',
             f"<h2>{html.escape(slide['title'])}</h2>"]
    if slide.get("lead"):
        parts.append(f'<p class="lead">{html.escape(slide["lead"])}</p>')
    return "".join(parts)


def _slide_view(model, slide: dict, n: int) -> str:
    diagram = slide["diagram"]
    name = diagram.get("name") or "(naamloze view)"
    title = slide.get("title") or name
    intro = slide.get("intro") or model.documentation(diagram)
    canvas = diagram_canvas(model, diagram, marker_prefix=f"s{n}-",
                            ref_base="../")
    intro_html = (f'<p class="intro">{html.escape(intro)}</p>'
                  if intro else "")
    return (
        f'<header class="view-head"><h2>{html.escape(title)}</h2>'
        f"{intro_html}</header>"
        f'<div class="view-fit" data-w="{canvas["width"]}" '
        f'data-h="{canvas["height"]}">'
        f'<div class="diagram" style="width:{canvas["width"]}px;'
        f'height:{canvas["height"]}px">{canvas["svg"]}{canvas["divs"]}'
        f"</div></div>"
        f'<footer class="view-foot">'
        f'{legend_html(canvas["boxes"], canvas["edges"])}'
        f'<a class="view-open" href="../{slugify(name)}.html">'
        f"open als losse pagina</a></footer>")


def _slide_bullets(slide: dict) -> str:
    parts = ['<div class="accent"></div>',
             f"<h2>{html.escape(slide['title'])}</h2>"]
    if slide.get("lead"):
        parts.append(f'<p class="lead">{html.escape(slide["lead"])}</p>')
    items = "".join(f"<li>{html.escape(b)}</li>" for b in slide["bullets"])
    parts.append(f'<ul class="bullets">{items}</ul>')
    if slide.get("gov"):
        parts.append('<span class="gov-pill">Specifiek voor de '
                     "overheid</span>")
        parts.append(f'<p class="gov-note">{html.escape(slide["gov"])}</p>')
    return "".join(parts)


def _slide_text(slide: dict) -> str:
    parts = ['<div class="accent"></div>']
    if slide.get("title"):
        parts.append(f"<h2>{html.escape(slide['title'])}</h2>")
    if slide.get("lead"):
        parts.append(f'<p class="lead">{html.escape(slide["lead"])}</p>')
    paragraphs = "".join(
        f"<p>{html.escape(p.strip())}</p>"
        for p in slide["body"].split("\n\n") if p.strip())
    parts.append(f'<div class="prose">{paragraphs}</div>')
    return "".join(parts)


def _slide_closing(slide: dict) -> str:
    parts = ['<div class="accent"></div>',
             f"<h2>{html.escape(slide['title'])}</h2>"]
    if slide.get("lead"):
        parts.append(f'<p class="lead">{html.escape(slide["lead"])}</p>')
    link = slide.get("link")
    if link:
        parts.append(f'<p class="closing-link">'
                     f'<a href="{html.escape(link["href"])}">'
                     f'{html.escape(link["label"])}</a></p>')
    return "".join(parts)


def render_slide_html(model, deck: dict, slide: dict, n: int) -> str:
    kind = slide["type"]
    if kind == "title":
        inner = _slide_title(deck, slide)
    elif kind == "section":
        inner = _slide_section(slide)
    elif kind == "view":
        inner = _slide_view(model, slide, n)
    elif kind == "text":
        inner = _slide_text(slide)
    elif kind == "bullets":
        inner = _slide_bullets(slide)
    else:
        inner = _slide_closing(slide)
    surface = "light" if kind == "view" else "dark"
    return (f'<section class="slide slide-{kind} {surface}" id="s{n}">'
            f"{inner}{_notes_html(slide)}</section>")


def render_deck_html(model, deck: dict) -> str:
    """One self-contained HTML document for a validated deck."""
    total = len(deck["slides"])
    slides_html = "\n".join(
        render_slide_html(model, deck, slide, n)
        for n, slide in enumerate(deck["slides"], start=1))
    return f"""{MARKER}
<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(deck["title"])}</title>
<link rel="icon" href="{FAVICON}">
<link rel="stylesheet" href="{NLDD_CSS}">
<style>
{layer_css()}
{DIAGRAM_CSS}{DECK_CSS}</style>
</head>
<body>
<main class="deck">
{slides_html}
</main>
<div class="hint">&larr; &rarr; navigeren &middot; f volledig scherm &middot;
n notities &middot; a autoplay</div>
<div class="chrome">
<button class="nav-btn" data-nav="-1" aria-label="Vorige slide">&lsaquo;</button>
<button class="nav-btn" data-nav="1" aria-label="Volgende slide">&rsaquo;</button>
<div class="counter">01/{total:02d}</div>
</div>
<aside class="notes-panel" hidden><h3>Notities</h3>
<div class="notes-body"></div></aside>
<div class="progress"><div class="progress-fill"></div></div>
<script>
{DECK_JS}</script>
</body>
</html>
"""


def render_all_slides(model, decks_dir, out_dir) -> tuple[list, list]:
    """Render every decks/*.toml; returns (written, removed) path lists.
    A missing or empty decks dir is not an error: nothing is rendered and
    stale generated decks are cleaned up."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    decks = [load_deck(path, model)
             for path in sorted(Path(decks_dir).glob("*.toml"))]

    slugs = set()
    for deck in decks:
        if deck["slug"] in slugs:
            raise ModelError(f"Meerdere decks renderen naar "
                             f"'{deck['slug']}.html'; geef een deck een "
                             f"uniek 'slug'-veld")
        slugs.add(deck["slug"])

    written, produced = [], set()
    for deck in decks:
        path = out / f"{deck['slug']}.html"
        if write_if_changed(path, render_deck_html(model, deck)):
            written.append(path)
        produced.add(path.name)

    removed = []
    for stale in out.glob("*.html"):
        if stale.name in produced:
            continue
        first_line = stale.read_text(encoding="utf-8").split("\n", 1)[0]
        if first_line.strip() == MARKER:
            stale.unlink()
            removed.append(stale)
    return written, removed
