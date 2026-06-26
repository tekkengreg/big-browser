#!/usr/bin/env python3
"""Big Browser Hub — récupération et cadrage des icônes de Site.

Deux étapes, à partir du champ optionnel `icon_source` du `site.yaml` :

    icons.py fetch <site-dir>   # télécharge le logo officiel → icon.src.<ext>
    icons.py frame <site-dir>   # enrobe le logo dans le cadre Big Browser → icon.svg
    icons.py build <site-dir>   # fetch puis frame
    icons.py <cmd> --all        # sur tous les Sites de sites/

Le **cadre** signale visuellement qu'il s'agit d'une application *Big Browser* :
le logo officiel est centré sur une carte arrondie, ceinturé d'un contour violet
(#6965db), avec une pastille « BB » dans le coin inférieur droit.

Aucune dépendance hors stdlib pour le cadrage. `fetch` utilise urllib.
"""
from __future__ import annotations

import argparse
import base64
import re
import sys
from pathlib import Path
from urllib.request import Request, urlopen

import yaml

# --- Cadre Big Browser -----------------------------------------------------

CANVAS = 256
BB_COLOR = "#6965db"
# Boîte où s'inscrit le logo (centré, laisse la place à la pastille de coin).
LOGO_BOX = (46, 30, 164, 164)            # x, y, largeur, hauteur
BADGE = (198, 198, 42)                    # cx, cy, r de la pastille « BB »

RASTER_MIME = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".webp": "image/webp",
}


def load_manifest(site_dir: Path) -> dict:
    path = site_dir / "site.yaml"
    if not path.exists():
        path = site_dir / "site.yml"
    if not path.exists():
        raise SystemExit(f"erreur: ni site.yaml ni site.yml dans {site_dir}")
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _attrs(open_tag: str) -> dict[str, str]:
    """Extrait les attributs d'une balise ouvrante `<svg ...>`."""
    return dict(re.findall(r'([\w:-]+)\s*=\s*"([^"]*)"', open_tag))


def svg_inner(src: Path) -> str:
    """Réécrit un SVG source en élément `<svg>` imbriqué, dimensionné dans LOGO_BOX.

    On garde le viewBox d'origine et on laisse `preserveAspectRatio` centrer le
    logo ; les attributs xmlns sont conservés pour que l'imbrication soit valide.
    """
    text = src.read_text(encoding="utf-8")
    text = re.sub(r"<\?xml.*?\?>", "", text, flags=re.S)
    text = re.sub(r"<!DOCTYPE.*?>", "", text, flags=re.S)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    m = re.search(r"<svg\b([^>]*)>", text, flags=re.S | re.I)
    if not m:
        raise SystemExit(f"erreur: {src} ne ressemble pas à un SVG")
    attrs = _attrs(m.group(0))

    view_box = attrs.get("viewBox")
    if not view_box:
        w = re.sub(r"[a-z%]+$", "", attrs.get("width", "")) or None
        h = re.sub(r"[a-z%]+$", "", attrs.get("height", "")) or None
        view_box = f"0 0 {w or 256} {h or 256}"

    keep = " ".join(f'{k}="{v}"' for k, v in attrs.items()
                    if k.startswith("xmlns"))
    x, y, w, h = LOGO_BOX
    body = text[m.end():text.rfind("</svg>")]
    return (f'<svg {keep} x="{x}" y="{y}" width="{w}" height="{h}" '
            f'viewBox="{view_box}" preserveAspectRatio="xMidYMid meet">'
            f"{body}</svg>")


def raster_inner(src: Path) -> str:
    """Encode un logo bitmap en `<image>` data-URI, ajusté dans LOGO_BOX."""
    mime = RASTER_MIME[src.suffix.lower()]
    b64 = base64.b64encode(src.read_bytes()).decode("ascii")
    x, y, w, h = LOGO_BOX
    return (f'<image x="{x}" y="{y}" width="{w}" height="{h}" '
            f'preserveAspectRatio="xMidYMid meet" '
            f'href="data:{mime};base64,{b64}"/>')


def render_frame(inner: str) -> str:
    cx, cy, r = BADGE
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="{CANVAS}" height="{CANVAS}" viewBox="0 0 {CANVAS} {CANVAS}" xmlns="http://www.w3.org/2000/svg">
  <!-- Carte de fond -->
  <rect x="8" y="8" width="240" height="240" rx="48" fill="#ffffff"/>
  <!-- Logo officiel encapsulé -->
  {inner}
  <!-- Contour Big Browser -->
  <rect x="8" y="8" width="240" height="240" rx="48" fill="none" stroke="{BB_COLOR}" stroke-width="10"/>
  <!-- Pastille « BB » : marque d'application Big Browser -->
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="{BB_COLOR}" stroke="#ffffff" stroke-width="8"/>
  <text x="{cx}" y="{cy + 12}" font-family="system-ui, sans-serif" font-size="38"
        font-weight="700" fill="#ffffff" text-anchor="middle">BB</text>
</svg>
"""


def inner_for(src: Path) -> str:
    ext = src.suffix.lower()
    if ext == ".svg":
        return svg_inner(src)
    if ext in RASTER_MIME:
        return raster_inner(src)
    raise SystemExit(f"erreur: format d'icône non géré : {ext}")


# --- Commandes -------------------------------------------------------------

def _source_file(site_dir: Path) -> Path | None:
    found = sorted(site_dir.glob("icon.src.*"))
    return found[0] if found else None


def fetch(site_dir: Path) -> Path:
    manifest = load_manifest(site_dir)
    url = manifest.get("icon_source")
    if not url:
        raise SystemExit(f"erreur: pas de champ 'icon_source' dans {site_dir}/site.yaml")
    req = Request(url, headers={"User-Agent": "BigBrowserHub/1.0 (+https://github.com/tekkengreg/big-browser)"})
    with urlopen(req, timeout=30) as resp:
        data = resp.read()
        ctype = resp.headers.get("Content-Type", "")
    ext = Path(url.split("?")[0]).suffix.lower()
    if ext not in {".svg", *RASTER_MIME}:
        ext = {"image/svg+xml": ".svg", "image/png": ".png",
               "image/jpeg": ".jpg", "image/gif": ".gif",
               "image/webp": ".webp"}.get(ctype.split(";")[0].strip(), ".png")
    # purge d'éventuelles sources précédentes (extension différente)
    for old in site_dir.glob("icon.src.*"):
        old.unlink()
    out = site_dir / f"icon.src{ext}"
    out.write_bytes(data)
    print(f"✓ {site_dir.name} : logo téléchargé → {out.name} ({len(data)} o)")
    return out


def frame(site_dir: Path, input_path: Path | None = None) -> Path:
    src = input_path or _source_file(site_dir)
    if not src or not src.exists():
        raise SystemExit(
            f"erreur: aucune source pour {site_dir.name} "
            f"(lancez `fetch` ou passez --input)")
    out = site_dir / "icon.svg"
    out.write_text(render_frame(inner_for(src)), encoding="utf-8")
    print(f"✓ {site_dir.name} : icône cadrée → {out.name} (source : {src.name})")
    return out


def _site_dirs(args) -> list[Path]:
    if args.all:
        root = Path(args.sites)
        return [d for d in sorted(root.iterdir())
                if (d / "site.yaml").exists() or (d / "site.yml").exists()]
    if not args.site_dir:
        raise SystemExit("erreur: indiquez un <site-dir> ou --all")
    return [Path(args.site_dir)]


def main(argv=None):
    p = argparse.ArgumentParser(prog="icons", description="Icônes Big Browser")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_common(sp):
        sp.add_argument("site_dir", nargs="?")
        sp.add_argument("--all", action="store_true", help="tous les Sites de sites/")
        sp.add_argument("--sites", default="sites")

    pf = sub.add_parser("fetch", help="télécharge le logo (icon_source)")
    add_common(pf)

    pr = sub.add_parser("frame", help="enrobe le logo dans le cadre Big Browser")
    add_common(pr)
    pr.add_argument("--input", help="fichier logo explicite (sinon icon.src.*)")

    pb = sub.add_parser("build", help="fetch puis frame")
    add_common(pb)

    args = p.parse_args(argv)
    dirs = _site_dirs(args)
    failures = 0
    for d in dirs:
        try:
            if args.cmd == "fetch":
                fetch(d)
            elif args.cmd == "frame":
                frame(d, Path(args.input) if getattr(args, "input", None) else None)
            elif args.cmd == "build":
                fetch(d)
                frame(d)
        except SystemExit as e:
            print(e, file=sys.stderr)
            failures += 1
    if failures:
        raise SystemExit(f"\n{failures} Site(s) en échec")


if __name__ == "__main__":
    main()
