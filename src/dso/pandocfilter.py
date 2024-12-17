"""
Pandocfilter that add watermarks to quarto reports

 * warning box at the top
 * watermark to all PNG images

Called internally by `dso exec quarto` via `python -m dso.pandocfilter`.
"""

import sys
import urllib.parse
from copy import copy
from textwrap import dedent

import PIL
import PIL.Image
import PIL.ImageChops
import PIL.ImageDraw
import PIL.ImageFont
from panflute import Div, Image, RawBlock, run_filter

from dso._logging import log
from dso._watermark import Watermarker


def _get_disclaimer_box(title, text):
    title = str(title).strip().replace("\n", " ")
    text = str(text).strip().replace("\n", " ")
    return dedent(
        f"""\
        <div class="callout callout-style-default callout-important callout-titled">
        <div class="callout-header d-flex align-content-center">
        <div class="callout-icon-container">
        <i class="callout-icon"></i>
        </div>
        <div class="callout-title-container flex-fill">
        {title}
        </div>
        </div>
        <div class="callout-body-container callout-body">
        <p>{text}</p>
        </div>
        </div>
        """
    )


def prepare(doc):
    """Panflutes prepare"""
    disclaimer_title = doc.get_metadata("disclaimer.title")
    disclaimer_text = doc.get_metadata("disclaimer.text")
    if disclaimer_title is not None and disclaimer_text is not None:
        div = Div(RawBlock(_get_disclaimer_box(disclaimer_title, disclaimer_text), format="html"))
        doc.content.insert(0, div)


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
                path = urllib.parse.unquote(elem.url)
                Watermarker.add_watermark(path, path, **watermark_config)

            except PIL.UnidentifiedImageError:
                log.warning("Image could not be read by PIL. It will not receive a watermark.")

    return elem


if __name__ == "__main__":
    run_filter(action, prepare=prepare, doc=None)
