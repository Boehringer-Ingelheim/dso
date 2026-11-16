"""
Pandocfilter that add watermarks to quarto reports

 * warning box at the top
 * watermark to all PNG images

Called internally by `dso exec quarto` via `python -m dso.pandocfilter {disclaimer,watermark}`.
The `disclaimer` stage needs to run before quarto's filters (`pre-ast`), such that quarto
renders the callout in all output formats. The `watermark` stage runs after quarto's filters.
"""

import sys
import urllib.parse
from copy import copy
from pathlib import Path
from tempfile import NamedTemporaryFile

import PIL
from panflute import Div, Image, Para, RawBlock, Space, Str, run_filter
from panflute.elements import RAW_FORMATS

from dso._logging import log
from dso._watermark import Watermarker, get_plotly_watermark_html

# panflute doesn't know about the typst format yet and would fail on raw typst blocks (e.g. quarto callouts)
RAW_FORMATS.add("typst")


def _text_to_inlines(text):
    """Convert plain text into a list of panflute inline elements (words separated by spaces)."""
    inlines = []
    for word in str(text).split():
        if inlines:
            inlines.append(Space())
        inlines.append(Str(word))
    return inlines


def _get_disclaimer_box(title, text):
    """
    Build the disclaimer as a quarto callout.

    Using a native callout Div (rather than raw HTML) ensures quarto renders
    it in all output formats (e.g. HTML, Typst, LaTeX).
    """
    title = " ".join(str(title).split())
    return Div(Para(*_text_to_inlines(text)), classes=["callout-important"], attributes={"title": title})


def prepare(doc):
    """Panflutes prepare"""
    disclaimer_title = doc.get_metadata("disclaimer.title")
    disclaimer_text = doc.get_metadata("disclaimer.text")
    if disclaimer_title is not None and disclaimer_text is not None:
        doc.content.insert(0, _get_disclaimer_box(disclaimer_title, disclaimer_text))


def _sanitize_watermark_config(config):
    """Parse values to integer where appropriate"""
    config = copy(config)
    int_fields = ["font_outline", "font_size"]
    for f in int_fields:
        if f in config:
            config[f] = int(config[f])
    # special handling for tile size; it's a list; but if it contains only one element
    # then it has the same widht and height (quarto or yaml limitation that list can't contain two identical elements)
    if "tile_size" in config:
        if len(config["tile_size"]) == 1:
            size = int(config["tile_size"][0])
            config["tile_size"] = (size, size)
        else:
            config["tile_size"] = [int(x) for x in config["tile_size"]]
    return config


def _is_plotly_html(text: str) -> bool:
    """Return whether a raw HTML block contains an (interactive) plotly plot.

    Detects both flavours of plotly output found in quarto reports:
      * Python plotly: ``<div class="plotly-graph-div" ...>``
      * R plotly (htmlwidgets): ``<div ... class="plotly html-widget">`` plus a
        ``<script type="application/json" data-for="htmlwidget-...">`` payload.
    """
    if "plotly-graph-div" in text:
        return True
    # R htmlwidgets: the rendered container carries both the "plotly" and the
    # "html-widget" classes (order may vary). The "html-widget" class (with hyphen)
    # only appears on the widget container, not in the JSON payload.
    return "html-widget" in text and "plotly" in text


def action(elem, doc):
    """Panflutes action"""
    watermark_config = _sanitize_watermark_config(doc.get_metadata("watermark"))
    if watermark_config:  # could be "" or None, both which evaluate to False
        if "text" not in watermark_config:
            log.error("Need to specify at least `watermark.text`")
            sys.exit(1)
        if isinstance(elem, Image):
            try:
                log.debug(f"Modifying image {elem.url}")
                path = Path(urllib.parse.unquote(elem.url))
                # use a temporary file to add the watermark, otherwise the original file may be modified inplace
                out_path = NamedTemporaryFile(delete=False, suffix=path.suffix).name
                Watermarker.add_watermark(path, out_path, **watermark_config)
                elem.url = urllib.parse.quote(out_path)

            except PIL.UnidentifiedImageError:
                log.warning("Image could not be read by PIL. It will not receive a watermark.")

        elif isinstance(elem, RawBlock) and elem.format == "html" and _is_plotly_html(elem.text):
            log.debug("Adding watermark to plotly plot")
            elem.text = get_plotly_watermark_html(elem.text, **watermark_config)

    return elem


def _noop(elem, doc):
    return elem


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else None
    if stage == "disclaimer":
        run_filter(_noop, prepare=prepare, doc=None)
    elif stage == "watermark":
        run_filter(action, doc=None)
    else:
        run_filter(action, prepare=prepare, doc=None)
