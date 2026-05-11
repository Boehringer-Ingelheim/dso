"""Add text-watermarks to images"""

import io
import tempfile
from abc import abstractmethod
from importlib import resources
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader, PdfWriter
from svgutils import compose

from dso import assets


class Watermarker:
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
    """Add watermarks to PDF files using native PDF text operations."""

    def apply_and_save(self, input_image: Path | str, output_image: Path | str):
        """Apply the watermark to an image and save it to the specified output file"""
        reader = PdfReader(input_image)
        writer = PdfWriter()
        for page_obj in reader.pages:
            page_width = float(page_obj.mediabox.width)
            page_height = float(page_obj.mediabox.height)
            pdf_bytes = self._create_text_watermark_pdf(page_width, page_height)
            watermark_overlay_pdf = PdfReader(io.BytesIO(pdf_bytes)).pages[0]
            page_obj.merge_page(watermark_overlay_pdf)
            writer.add_page(page_obj)

        with open(output_image, "wb") as f:
            writer.write(f)
        reader.close()

    @staticmethod
    def _parse_color(color_str: str) -> tuple[float, float, float, float]:
        """Parse a color string (#RRGGBBAA or #RRGGBB) to (r, g, b, a) floats in [0, 1]."""
        color_str = color_str.lstrip("#")
        r = int(color_str[0:2], 16) / 255
        g = int(color_str[2:4], 16) / 255
        b = int(color_str[4:6], 16) / 255
        a = int(color_str[6:8], 16) / 255 if len(color_str) >= 8 else 1.0
        return r, g, b, a

    @staticmethod
    def _pdf_escape(text: str) -> str:
        """Escape special characters for a PDF literal string."""
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    def _create_text_watermark_pdf(self, page_width: float, page_height: float) -> bytes:
        """Build a single-page PDF with tiled watermark text using a PDF Tiling Pattern.

        The watermark tile is defined once as a pattern and the page is filled with it,
        so the renderer can cache and repeat the tile efficiently.
        """
        fill_r, fill_g, fill_b, fill_a = self._parse_color(self.font_color)
        stroke_r, stroke_g, stroke_b, stroke_a = self._parse_color(self.font_outline_color)

        tile_w, tile_h = self.tile_size
        escaped_text = self._pdf_escape(self.text)

        # Approximate text width using Helvetica average character width (~0.52 * font_size)
        approx_text_width = len(self.text) * self.font_size * 0.52

        # Build the pattern's content stream (drawn once, tiled by the renderer)
        tile_lines: list[str] = []
        tile_lines.append("BT")
        tile_lines.append(f"/F1 {self.font_size} Tf")

        if self.font_outline > 0:
            tile_lines.append("2 Tr")  # Fill then stroke
            tile_lines.append(f"{self.font_outline} w")
            tile_lines.append(f"{stroke_r:.4f} {stroke_g:.4f} {stroke_b:.4f} RG")
        else:
            tile_lines.append("0 Tr")  # Fill only

        tile_lines.append(f"{fill_r:.4f} {fill_g:.4f} {fill_b:.4f} rg")

        # Position 1: top-left of tile (mirrors PIL anchor "lt" at (10, 10))
        # PDF y-axis is bottom-up, so top of tile = tile_h
        tx1 = 10
        ty1 = tile_h - 10 - self.font_size
        tile_lines.append(f"1 0 0 1 {tx1:.2f} {ty1:.2f} Tm")
        tile_lines.append(f"({escaped_text}) Tj")

        # Position 2: middle-right of tile (mirrors PIL anchor "rm")
        tx2 = tile_w - 10 - approx_text_width
        ty2 = tile_h / 2 - self.font_size * 0.4
        tile_lines.append(f"1 0 0 1 {tx2:.2f} {ty2:.2f} Tm")
        tile_lines.append(f"({escaped_text}) Tj")

        tile_lines.append("ET")
        tile_content = "\n".join(tile_lines).encode()

        # Page content stream: fill the entire page with the pattern
        page_content = (f"q /GS0 gs\n/Pattern cs /P1 scn\n0 0 {page_width} {page_height} re f\nQ").encode()

        # ---- Assemble minimal PDF ----
        def _obj(n: int, body: bytes) -> bytes:
            return f"{n} 0 obj\n".encode() + body + b"\nendobj\n"

        def _stream_obj(n: int, extra_header: str, data: bytes) -> bytes:
            hdr = f"{n} 0 obj\n<< {extra_header}/Length {len(data)} >>\nstream\n".encode()
            return hdr + data + b"\nendstream\nendobj\n"

        objects = [
            # 1: Catalog
            _obj(1, b"<< /Type /Catalog /Pages 2 0 R >>"),
            # 2: Pages
            _obj(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"),
            # 3: Page
            _obj(
                3,
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_width} {page_height}] "
                f"/Resources << /Pattern << /P1 4 0 R >> /ExtGState << /GS0 7 0 R >> >> "
                f"/Contents 6 0 R >>".encode(),
            ),
            # 4: Tiling Pattern
            _stream_obj(
                4,
                f"/Type /Pattern /PatternType 1 /PaintType 1 /TilingType 1 "
                f"/BBox [0 0 {tile_w} {tile_h}] /XStep {tile_w} /YStep {tile_h} "
                f"/Resources << /Font << /F1 5 0 R >> >> ",
                tile_content,
            ),
            # 5: Font
            _obj(5, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"),
            # 6: Page content stream
            _stream_obj(6, "", page_content),
            # 7: Graphics state for transparency
            _obj(
                7,
                f"<< /Type /ExtGState /ca {fill_a:.4f} /CA {stroke_a:.4f} >>".encode(),
            ),
        ]

        pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets: list[int] = []
        for obj in objects:
            offsets.append(len(pdf))
            pdf.extend(obj)

        xref_offset = len(pdf)
        pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode())
        pdf.extend(b"0000000000 65535 f \r\n")
        for offset in offsets:
            pdf.extend(f"{offset:010d} 00000 n \r\n".encode())

        pdf.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode())

        return bytes(pdf)
