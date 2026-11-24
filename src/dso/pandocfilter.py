"""
Pandocfilter that adds watermarks to images and plotly plots in quarto reports

Registered by `dso exec quarto` in `_quarto.yml` and called via `python -m dso.pandocfilter`.
The disclaimer is not handled here, but by a lua filter (`assets/disclaimer.lua`).
"""

import base64
import json
import os
import sys
import urllib.parse
from copy import copy
from pathlib import Path
from tempfile import NamedTemporaryFile

import PIL
from panflute import Div, Image, RawBlock, run_filter

from dso._logging import log
from dso._watermark import Watermarker, get_plotly_watermark_html, get_plotly_watermark_parts


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


def _is_plotly_div(elem: Div) -> bool:
    """Return whether a native pandoc `Div` is the container of an (interactive) plotly plot.

    This happens if the widget HTML is written directly into the markdown (e.g. via
    ``print(htmltools::tagList(widget))`` in a ``results: asis`` chunk). Pandoc then parses the
    container ``<div>`` into a native `Div`, followed by a separate `RawBlock` with the JSON payload.
    """
    classes = set(elem.classes)
    return {"plotly", "html-widget"} <= classes or "plotly-graph-div" in classes


def _get_watermark_dir() -> Path | None:
    """Get the directory where watermarked images are stored.

    This is the quarto "mediabag" directory within the document's `<name>_files` folder. Quarto passes its
    location (relative to the working directory of pandoc, i.e. the directory of the document) to filters via
    the `QUARTO_FILTER_PARAMS` environment variable. Storing images there (instead of a system temp dir) is
    important for output formats like typst that can only read files within the project directory.
    The directory is temporary and gets cleaned up by quarto (unless it is needed as a resource for the output).

    Returns None if the directory can't be determined (e.g. when not running through quarto).
    """
    # NOTE: `QUARTO_FILTER_PARAMS` and its `mediabag-dir` key are internal to quarto and not documented.
    # If they ever disappear, we fall back to a system temp dir (works for HTML, but not for typst).
    # References (quarto v1.11.9):
    #  * mediabag dir is `<name>_files/mediabag`, relative to the document directory:
    #    https://github.com/quarto-dev/quarto-cli/blob/v1.11.9/src/command/render/render-paths.ts#L17-L19
    #    https://github.com/quarto-dev/quarto-cli/blob/v1.11.9/src/command/render/render.ts#L116-L120
    #  * it is added to the filter params as `mediabag-dir`:
    #    https://github.com/quarto-dev/quarto-cli/blob/v1.11.9/src/command/render/filters.ts#L571
    #  * filter params are passed as base64-encoded JSON in the env of pandoc (and therefore of all filters):
    #    https://github.com/quarto-dev/quarto-cli/blob/v1.11.9/src/command/render/pandoc.ts#L343-L345
    #  * the mediabag dir is deleted after rendering (unless it is required by the output):
    #    https://github.com/quarto-dev/quarto-cli/blob/v1.11.9/src/command/render/cleanup.ts#L85-L90
    params = os.environ.get("QUARTO_FILTER_PARAMS")
    if not params:
        return None
    try:
        mediabag_dir = json.loads(base64.b64decode(params)).get("mediabag-dir")
    except ValueError:
        log.debug("Could not parse QUARTO_FILTER_PARAMS")
        return None
    if not mediabag_dir:
        return None
    return Path(mediabag_dir)


def _get_watermark_path(path: Path) -> Path:
    """Get a new path for a watermarked version of `path`, so that the original image is not modified inplace."""
    out_dir = _get_watermark_dir()
    if out_dir is None:
        with NamedTemporaryFile(delete=False, suffix=path.suffix) as f:
            return Path(f.name)
    out_dir.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(delete=False, dir=out_dir, prefix=f"{path.stem}.wm.", suffix=path.suffix) as f:
        # keep the path relative to the document, as typst doesn't support absolute paths outside its root
        return out_dir / Path(f.name).name


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
                out_path = _get_watermark_path(path)
                Watermarker.add_watermark(path, out_path, **watermark_config)
                elem.url = urllib.parse.quote(out_path.as_posix())

            except PIL.UnidentifiedImageError:
                log.warning("Image could not be read by PIL. It will not receive a watermark.")

        elif isinstance(elem, RawBlock) and elem.format == "html" and _is_plotly_html(elem.text):
            log.debug("Adding watermark to plotly plot")
            elem.text = get_plotly_watermark_html(elem.text, **watermark_config)

        elif isinstance(elem, Div) and _is_plotly_div(elem):
            log.debug("Adding watermark to plotly plot")
            style_html, overlay_html = get_plotly_watermark_parts(**watermark_config)
            # The JSON payload following the div doesn't need to be wrapped, as plotly renders into the div.
            return Div(
                RawBlock(style_html, format="html"),
                elem,
                RawBlock(overlay_html, format="html"),
                classes=["dso-watermark-container"],
                attributes={"style": "position:relative;"},
            )

    return elem


if __name__ == "__main__":
    run_filter(action, doc=None)
