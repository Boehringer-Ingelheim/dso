"""Add text-watermarks to images"""

import tempfile
from abc import abstractmethod
from importlib import resources
from pathlib import Path
from typing import Generic, TypeVar

from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader, PdfWriter
from svgutils import compose

from dso import assets

ImgType = TypeVar("ImgType")


class Watermarker(Generic[ImgType]):
    """
    Add watermarks to images

    Parameters
    ----------
    text
        Text to use as watermark
    tile_size
        watermark text will be arranged in tile of this size (once at top left, once at middle right)
    font_size
        watermark font size
    font_outline
        font outline thickness
    font_color
        watermark font color. Use #RGBA format to add alpha
    font_outline_color
        watermark font outline color. Use #RGBA format to add alpha
    """

    def __init__(
        self,
        text: str,
        *,
        tile_size: tuple[int, int] = (200, 200),
        font_size: int = 18,
        font_outline: int = 1,
        font_color: str = "#EEEEEE60",
        font_outline_color: str = "#44444460",
    ):
        self.text = text
        self.tile_size = tile_size
        self.font_size = font_size
        self.font_outline = font_outline
        self.font_color = font_color
        self.font_outline_color = font_outline_color

    @abstractmethod
    def apply_and_save(self, input_image: Path | str, output_image: Path | str):
        """Apply the watermark to an image"""
        ...

    def get_watermark_overlay(self, size: tuple[int, int]) -> Image.Image:
        """Generate an overlay with the watermark that has the same size as the base image"""
        watermark = self._get_watermark_tile()
        watermark_tiled = Image.new("RGBA", size)
        for x in range(0, size[0], self.tile_size[0]):
            for y in range(0, size[1], self.tile_size[1]):
                watermark_tiled.paste(watermark, (x, y))

        return watermark_tiled

    def _get_watermark_tile(self) -> Image.Image:
        """Get a tile of predefined size that contains the watermark text twice

        (once top left corner, once middle right - this leads to a regular pattern)
        """
        img = Image.new("RGBA", self.tile_size, color=(255, 255, 255, 0))

        d = ImageDraw.Draw(img)
        with resources.open_binary(assets, "open_sans.ttf") as watermark_font:
            font = ImageFont.truetype(watermark_font, self.font_size)

        # Add text in top left corner
        d.text(
            (10, 10),
            self.text,
            anchor="lt",
            fill=self.font_color,
            font=font,
            stroke_width=self.font_outline,
            stroke_fill=self.font_outline_color,
        )

        # Add text in bottom right corner
        d.text(
            (self.tile_size[0] - 10, self.tile_size[1] / 2 + self.font_size),
            self.text,
            anchor="rm",
            fill=self.font_color,
            font=font,
            stroke_width=self.font_outline,
            stroke_fill=self.font_outline_color,
        )

        return img

    @staticmethod
    def add_watermark(input_image: Path | str, output_image: Path | str, **kwargs):
        """Add watermark to an image, using the different implementations base on the file type"""
        input_image = Path(input_image)
        ext = input_image.suffix
        if ext == ".svg":
            wm = SVGWatermarker(**kwargs)
        elif ext == ".pdf":
            wm = PDFWatermarker(**kwargs)
        else:
            wm = PILWatermarker(**kwargs)

        wm.apply_and_save(input_image, output_image)


class PILWatermarker(Watermarker):
    """Add watermarks to any image supported by Pillow"""

    def apply_and_save(self, input_image: Path | str, output_image: Path | str):
        """Apply the watermark to an image and save it to the specified output file"""
        base_image = Image.open(input_image).convert("RGBA")
        watermark_overlay = self.get_watermark_overlay(base_image.size)
        combined = Image.alpha_composite(base_image, watermark_overlay)

        try:
            combined.save(output_image)
        except OSError:
            # e.g. OSError: cannot write mode RGBA as JPEG
            combined.convert("RGB").save(output_image)


class SVGWatermarker(Watermarker):
    """Add watermarks to SVG images. The watermark overlay will be a pixel graphic embedded in the svg."""

    def _get_size(self, svg_image: compose.SVG):
        try:
            if svg_image.width is None or svg_image.height is None:
                raise ValueError("Watermarking works only with SVG images that define an explicit width and height")
            return (int(svg_image.width), int(svg_image.height))
        except AttributeError:
            raise ValueError(
                "Watermarking works only with SVG images that define an explicit width and height"
            ) from None

    def apply_and_save(self, input_image: Path | str, output_image: Path | str):
        """Apply the watermark to an image and save it to the specified output file"""
        base_image = compose.SVG(input_image, fix_mpl=True)
        size = self._get_size(base_image)

        watermark_overlay = self.get_watermark_overlay(size)
        with tempfile.NamedTemporaryFile(suffix=".png") as tf:
            watermark_overlay.save(tf)
            watermark_overlay_svg = compose.Image(*size, tf.name)
        fig = compose.Figure(*size, base_image, watermark_overlay_svg)
        fig.save(output_image)


class PDFWatermarker(Watermarker):
    """Add watermarks to PDF images. The watermark overlay will be a pixel graphic embedded in the svg."""

    # Inspired by https://www.geeksforgeeks.org/working-with-pdf-files-in-python/
    def apply_and_save(self, input_image: Path | str, output_image: Path | str):
        """Apply the watermark to an image and save it to the specified output file"""
        reader = PdfReader(input_image)
        writer = PdfWriter()
        for page_obj in reader.pages:
            size = (int(page_obj.mediabox.width), int(page_obj.mediabox.height))
            watermark_overlay = self.get_watermark_overlay(size)
            with tempfile.NamedTemporaryFile(suffix=".pdf") as tf:
                watermark_overlay.save(tf)
                watermark_overlay_pdf = PdfReader(tf.file).pages[0]
                page_obj.merge_page(watermark_overlay_pdf)
                writer.add_page(page_obj)

        with open(output_image, "wb") as f:
            writer.write(f)
        reader.close()
