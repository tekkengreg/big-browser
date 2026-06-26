#!/usr/bin/env python3
"""Tests du cadrage d'icônes (icons.py) — sans accès réseau.

Couvre l'imbrication SVG, l'encodage bitmap en data-URI, le rendu du cadre
Big Browser et l'écriture de icon.svg. Lancement :
    python3 -m unittest discover -s tooling -p 'test_*.py'
"""
from __future__ import annotations

import base64
import tempfile
import unittest
from pathlib import Path

import icons

# 1x1 PNG transparent (en clair pour le test).
PNG_1x1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)
SVG_LOGO = (
    '<?xml version="1.0"?>\n'
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
    '<circle cx="50" cy="50" r="40" fill="#1db954"/></svg>'
)


class FrameRenderTests(unittest.TestCase):
    def test_cadre_contient_marque_bb(self):
        out = icons.render_frame("<g/>")
        self.assertIn(">BB<", out)
        self.assertIn(icons.BB_COLOR, out)              # contour + pastille
        self.assertIn('viewBox="0 0 256 256"', out)
        self.assertIn("<g/>", out)                       # le loge est injecté

    def test_svg_inner_imbrique_avec_viewbox(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "icon.src.svg"
            src.write_text(SVG_LOGO, encoding="utf-8")
            inner = icons.svg_inner(src)
        self.assertNotIn("<?xml", inner)                 # déclaration retirée
        self.assertIn('viewBox="0 0 100 100"', inner)
        self.assertIn("preserveAspectRatio", inner)
        self.assertIn('width="164"', inner)              # dimensionné dans LOGO_BOX
        self.assertIn("circle", inner)

    def test_raster_inner_data_uri(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "icon.src.png"
            src.write_bytes(PNG_1x1)
            inner = icons.raster_inner(src)
        self.assertIn("data:image/png;base64,", inner)
        self.assertIn("<image", inner)

    def test_inner_for_format_inconnu(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "icon.src.bmp"
            src.write_bytes(b"x")
            with self.assertRaises(SystemExit):
                icons.inner_for(src)


class FrameCommandTests(unittest.TestCase):
    def test_frame_ecrit_icon_svg(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            (site / "icon.src.svg").write_text(SVG_LOGO, encoding="utf-8")
            out = icons.frame(site)
        self.assertEqual(out.name, "icon.svg")

    def test_frame_sans_source_echoue(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit):
                icons.frame(Path(tmp))


if __name__ == "__main__":
    unittest.main()
