"""Add text-watermarks to images"""

import io
from abc import abstractmethod
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import cast

from PIL import Image, ImageColor, ImageDraw, ImageFont
from pypdf import PdfReader, PdfWriter

from dso import assets


@dataclass
class RGBAColor:
    """Color with channels normalized to [0, 1]."""

    r: float
    g: float
    b: float
    a: float

    @property
    def hex_rgb(self) -> str:
        """Return the color as a CSS hex string (#rrggbb), ignoring alpha."""
        return f"#{round(self.r * 255):02x}{round(self.g * 255):02x}{round(self.b * 255):02x}"

    @staticmethod
    def from_string(color_str: str) -> "RGBAColor":
        """Parse any color string accepted by Pillow to an RGBAColor with values in [0, 1]."""
        r, g, b, *a = ImageColor.getrgb(color_str)
        return RGBAColor(r / 255, g / 255, b / 255, (a[0] if a else 255) / 255)


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
        font_outline_color: str = "#A5A5A590",
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
    """Add watermarks to SVG images using native SVG text elements with a tiling pattern."""

    @staticmethod
    def _parse_svg_length(value: str) -> float:
        """Parse an SVG length value, stripping any unit suffix (px, pt, …)."""
        import re

        m = re.match(r"([\d.]+)", value.strip())
        if not m:
            raise ValueError(f"Cannot parse SVG length: {value!r}")
        return float(m.group(1))

    def _get_dimensions(self, root) -> tuple[float, float]:
        """Return (width, height) from the SVG root element."""
        w = root.get("width")
        h = root.get("height")
        if w is not None and h is not None:
            return self._parse_svg_length(w), self._parse_svg_length(h)
        vb = root.get("viewBox")
        if vb:
            parts = vb.split()
            return float(parts[2]), float(parts[3])
        raise ValueError("Watermarking requires SVG images that define an explicit width/height or viewBox")

    def apply_and_save(self, input_image: Path | str, output_image: Path | str):
        """Apply the watermark to an image and save it to the specified output file"""
        import xml.etree.ElementTree as ET

        # Pre-register all namespaces so ElementTree preserves them in the output.
        # iterparse yields (event, (prefix, uri)) for "start-ns" but is typed as
        # (str, Element) — cast to the actual runtime type to satisfy Pylance.
        for _event, ns_tuple in ET.iterparse(input_image, events=["start-ns"]):
            prefix, uri = cast(tuple[str, str], ns_tuple)
            ET.register_namespace(prefix, uri)
        ET.register_namespace("", "http://www.w3.org/2000/svg")

        tree = ET.parse(input_image)
        root = tree.getroot()

        ns = root.tag.split("}")[0] + "}" if root.tag.startswith("{") else ""

        width, height = self._get_dimensions(root)
        tile_w, tile_h = self.tile_size
        fill = RGBAColor.from_string(self.font_color)
        stroke = RGBAColor.from_string(self.font_outline_color)

        stroke_attrs: dict[str, str] = {}
        if self.font_outline > 0:
            stroke_attrs = {
                "stroke": stroke.hex_rgb,
                "stroke-opacity": f"{stroke.a:.4f}",
                "stroke-width": str(self.font_outline),
                "paint-order": "stroke fill",
            }

        common_text_attrs = {
            "font-family": "Helvetica, Arial, sans-serif",
            "font-size": str(self.font_size),
            "fill": fill.hex_rgb,
            "fill-opacity": f"{fill.a:.4f}",
            **stroke_attrs,
        }

        # Add <defs> at the front if not present
        defs = root.find(f"{ns}defs")
        if defs is None:
            defs = ET.Element(f"{ns}defs")
            root.insert(0, defs)

        pattern = ET.SubElement(
            defs,
            f"{ns}pattern",
            {
                "id": "dso-watermark-pattern",
                "patternUnits": "userSpaceOnUse",
                "width": str(tile_w),
                "height": str(tile_h),
            },
        )

        # Position 1: top-left of tile (matches PIL anchor "lt" at (10, 10))
        # SVG y is baseline; PIL y=10 is top of text. baseline = top + ascent ≈ top + 0.75 * font_size
        text1 = ET.SubElement(
            pattern,
            f"{ns}text",
            {"x": "10", "y": str(10 + self.font_size * 0.75), **common_text_attrs},
        )
        text1.text = self.text

        # Position 2: middle-right of tile (matches PIL anchor "rm")
        # PIL center at y = tile_h/2 + font_size. baseline = center + 0.25 * font_size
        text2 = ET.SubElement(
            pattern,
            f"{ns}text",
            {
                "x": str(tile_w - 10),
                "y": str(tile_h / 2 + self.font_size * 1.25),
                "text-anchor": "end",
                **common_text_attrs,
            },
        )
        text2.text = self.text

        # Overlay rect filling the full SVG canvas with the tiled pattern
        ET.SubElement(
            root,
            f"{ns}rect",
            {
                "x": "0",
                "y": "0",
                "width": str(width),
                "height": str(height),
                "fill": "url(#dso-watermark-pattern)",
            },
        )

        tree.write(output_image, xml_declaration=True, encoding="utf-8")


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
            writer.add_page(page_obj)
            writer.pages[-1].merge_page(watermark_overlay_pdf)

        with open(output_image, "wb") as f:
            writer.write(f)
        reader.close()

    @staticmethod
    def _pdf_escape(text: str) -> str:
        r"""Escape text for a PDF literal string (PDF spec Table 4.1).

        Named escapes are used for the defined control characters; all other
        characters outside printable ASCII (0x20–0x7E) are encoded as \\ddd
        octal sequences using WinAnsiEncoding (cp1252), which is the standard
        encoding for PDF base fonts like Helvetica.

        Source: https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/pdfreference1.0.pdf

        Raises
        ------
        ValueError
            If the text contains characters outside the WinAnsiEncoding (cp1252) range.
        """
        _named = {
            "\\": "\\\\",
            "(": "\\(",
            ")": "\\)",
            "\n": "\\n",
            "\r": "\\r",
            "\t": "\\t",
            "\b": "\\b",
            "\f": "\\f",
        }
        parts: list[str] = []
        for ch in text:
            if ch in _named:
                parts.append(_named[ch])
            elif 0x20 <= ord(ch) <= 0x7E:
                parts.append(ch)
            else:
                try:
                    encoded = ch.encode("cp1252")
                except UnicodeEncodeError:
                    raise ValueError(
                        f"Character {ch!r} (U+{ord(ch):04X}) is not supported by the PDF "
                        f"base font encoding (WinAnsiEncoding/cp1252)."
                    ) from None
                for byte in encoded:
                    parts.append(f"\\{byte:03o}")
        return "".join(parts)

    def _create_text_watermark_pdf(self, page_width: float, page_height: float) -> bytes:
        """Build a single-page PDF with tiled watermark text using a PDF Tiling Pattern.

        The watermark tile is defined once as a pattern and the page is filled with it,
        so the renderer can cache and repeat the tile efficiently.
        """
        fill = RGBAColor.from_string(self.font_color)
        stroke = RGBAColor.from_string(self.font_outline_color)

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
            tile_lines.append(f"{stroke.r:.4f} {stroke.g:.4f} {stroke.b:.4f} RG")
        else:
            tile_lines.append("0 Tr")  # Fill only

        tile_lines.append(f"{fill.r:.4f} {fill.g:.4f} {fill.b:.4f} rg")

        # Position 1: top-left of tile (mirrors PIL anchor "lt" at (10, 10))
        # PDF y-axis is bottom-up. baseline = tile_h - top - ascent ≈ tile_h - 10 - 0.75 * font_size
        tx1 = 10
        ty1 = tile_h - 10 - self.font_size * 0.75
        tile_lines.append(f"1 0 0 1 {tx1:.2f} {ty1:.2f} Tm")
        tile_lines.append(f"({escaped_text}) Tj")

        # Position 2: middle-right of tile (mirrors PIL anchor "rm")
        # PIL center at tile_h/2 + font_size from top → tile_h/2 - font_size in PDF coords.
        # baseline = center - 0.25 * font_size
        tx2 = tile_w - 10 - approx_text_width
        ty2 = tile_h / 2 - self.font_size * 1.25
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
            _obj(5, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"),
            # 6: Page content stream
            _stream_obj(6, "", page_content),
            # 7: Graphics state for transparency
            _obj(
                7,
                f"<< /Type /ExtGState /ca {fill.a:.4f} /CA {stroke.a:.4f} >>".encode(),
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
