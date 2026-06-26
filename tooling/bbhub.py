#!/usr/bin/env python3
"""Big Browser Hub — tooling.

Transforme un manifeste de Site unique (`site.yaml`) en artefacts Flatpak :
manifeste flatpak-builder, AppStream metainfo.xml, .desktop, site.json runtime.

Commandes :
    bbhub.py validate <site-dir>
    bbhub.py generate <site-dir> [--out dist]
    bbhub.py build    <site-dir> [--out dist] [--install] [--repo REPO]

Dépendance : PyYAML.  (Validation faite à la main, pas besoin de `jsonschema`.)
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from html import escape
from pathlib import Path

import yaml

# --- Constantes ------------------------------------------------------------

DEFAULT_RUNTIME_VERSION = "49"
ENGINE_REL = Path(__file__).resolve().parent.parent / "engine" / "bigbrowser.js"
ID_RE = re.compile(r"^[A-Za-z][\w-]*(\.[A-Za-z][\w-]*)+$")
RUNTIME_KEYS = ("id", "title", "url", "icon", "allowed_domains",
                "permissions", "inject_css", "inject_js", "ignore_tls_errors")
REQUIRED = ("id", "title", "url", "icon", "summary", "description", "project_license")


# --- Chargement & validation ----------------------------------------------

def load_manifest(site_dir: Path) -> dict:
    path = site_dir / "site.yaml"
    if not path.exists():
        path = site_dir / "site.yml"
    if not path.exists():
        raise SystemExit(f"erreur: ni site.yaml ni site.yml dans {site_dir}")
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"erreur: {path} ne contient pas un mapping YAML")
    return data


def validate(site_dir: Path, manifest: dict) -> list[str]:
    """Retourne la liste des erreurs (vide = valide)."""
    errors: list[str] = []

    for key in REQUIRED:
        if not manifest.get(key):
            errors.append(f"champ requis manquant : '{key}'")

    sid = manifest.get("id", "")
    if sid and not ID_RE.match(sid):
        errors.append(f"id invalide '{sid}' : attendu un reverse-DNS (ex. com.tekkengreg.bigbrowser.MonSite)")
    if sid and not sid.startswith("com.tekkengreg.bigbrowser."):
        errors.append(f"id '{sid}' : doit commencer par 'com.tekkengreg.bigbrowser.' (namespace du Hub)")
    if sid and site_dir.name != sid:
        errors.append(f"le dossier '{site_dir.name}' doit être nommé exactement comme l'id '{sid}'")

    url = manifest.get("url", "")
    if url and not url.startswith("https://"):
        errors.append(f"url '{url}' : doit être en https://")

    icon = manifest.get("icon")
    if icon:
        icon_path = site_dir / icon
        if not icon_path.exists():
            errors.append(f"icône introuvable : {icon_path}")
        elif icon_path.suffix.lower() not in (".svg", ".png"):
            errors.append(f"icône '{icon}' : format .svg ou .png attendu")

    perms = manifest.get("permissions", {})
    if perms and not isinstance(perms, dict):
        errors.append("permissions : doit être un mapping (notifications/geolocation/media)")

    cats = manifest.get("categories", [])
    if cats and not isinstance(cats, list):
        errors.append("categories : doit être une liste")

    return errors


# --- Génération des artefacts ----------------------------------------------

def runtime_site_json(manifest: dict) -> dict:
    out = {k: manifest[k] for k in RUNTIME_KEYS if k in manifest}
    out.setdefault("permissions", {})
    return out


def finish_args(manifest: dict) -> list[str]:
    args = [
        "--share=network",
        "--share=ipc",
        "--socket=wayland",
        "--socket=fallback-x11",
        "--device=dri",
        # L'Engine enregistre les téléchargements dans le dossier Téléchargements
        # via un chemin direct (pas le portail) : accès en écriture nécessaire.
        "--filesystem=xdg-download:create",
    ]
    perms = manifest.get("permissions", {}) or {}
    if perms.get("media"):
        args.append("--device=all")          # caméra / périphériques
        args.append("--socket=pulseaudio")    # micro / audio
    if perms.get("notifications"):
        args.append("--talk-name=org.freedesktop.Notifications")
    for extra in manifest.get("finish_args_extra", []) or []:
        if extra not in args:
            args.append(extra)
    return args


def flatpak_manifest(manifest: dict) -> dict:
    sid = manifest["id"]
    icon = manifest["icon"]
    icon_ext = Path(icon).suffix.lower()
    if icon_ext == ".svg":
        icon_install = (f"install -Dm644 {icon} "
                        f"/app/share/icons/hicolor/scalable/apps/{sid}.svg")
    else:
        icon_install = (f"install -Dm644 {icon} "
                        f"/app/share/icons/hicolor/256x256/apps/{sid}.png")

    return {
        "app-id": sid,
        "runtime": "org.gnome.Platform",
        "runtime-version": str(manifest.get("runtime_version", DEFAULT_RUNTIME_VERSION)),
        "sdk": "org.gnome.Sdk",
        "command": "bigbrowser",
        "finish-args": finish_args(manifest),
        "modules": [
            {
                "name": "engine",
                "buildsystem": "simple",
                "build-commands": ["install -Dm755 bigbrowser.js /app/bin/bigbrowser"],
                "sources": [{"type": "file", "path": "bigbrowser.js"}],
            },
            {
                "name": "site",
                "buildsystem": "simple",
                "build-commands": [
                    "install -Dm644 site.json /app/share/${FLATPAK_ID}/site.json",
                    "install -Dm644 ${FLATPAK_ID}.desktop "
                    "/app/share/applications/${FLATPAK_ID}.desktop",
                    "install -Dm644 ${FLATPAK_ID}.metainfo.xml "
                    "/app/share/metainfo/${FLATPAK_ID}.metainfo.xml",
                    icon_install,
                ],
                "sources": [
                    {"type": "file", "path": "site.json"},
                    {"type": "file", "path": f"{sid}.desktop"},
                    {"type": "file", "path": f"{sid}.metainfo.xml"},
                    {"type": "file", "path": icon},
                ],
            },
        ],
    }


def desktop_file(manifest: dict) -> str:
    cats = manifest.get("categories", []) or []
    cat_line = ";".join(cats) + ";" if cats else ""
    lines = [
        "[Desktop Entry]",
        f"Name={manifest['title']}",
        f"Comment={manifest.get('summary', '')}",
        "Exec=bigbrowser",
        f"Icon={manifest['id']}",
        "Terminal=false",
        "Type=Application",
        f"Categories={cat_line}",
        "StartupNotify=true",
    ]
    return "\n".join(lines) + "\n"


def metainfo_xml(manifest: dict) -> str:
    sid = manifest["id"]
    paragraphs = [p.strip() for p in str(manifest["description"]).split("\n\n") if p.strip()]
    desc = "\n".join(f"    <p>{escape(p)}</p>" for p in paragraphs)

    cats = manifest.get("categories", []) or []
    cat_block = ""
    if cats:
        items = "\n".join(f"    <category>{escape(c)}</category>" for c in cats)
        cat_block = f"  <categories>\n{items}\n  </categories>\n"

    dev = manifest.get("developer_name", "Big Browser")
    homepage = manifest.get("homepage", manifest["url"])

    screenshots = manifest.get("screenshots", []) or []
    ss_block = ""
    if screenshots:
        imgs = "\n".join(
            f"    <screenshot{' type=\"default\"' if i == 0 else ''}>\n"
            f"      <image>{escape(s)}</image>\n    </screenshot>"
            for i, s in enumerate(screenshots)
        )
        ss_block = f"  <screenshots>\n{imgs}\n  </screenshots>\n"

    keywords = manifest.get("keywords", []) or []
    kw_block = ""
    if keywords:
        items = "\n".join(f"      <keyword>{escape(k)}</keyword>" for k in keywords)
        kw_block = f"  <keywords>\n{items}\n  </keywords>\n"

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>{sid}</id>
  <metadata_license>CC0-1.0</metadata_license>
  <project_license>{escape(manifest['project_license'])}</project_license>
  <name>{escape(manifest['title'])}</name>
  <summary>{escape(manifest['summary'])}</summary>
  <description>
{desc}
  </description>
  <launchable type="desktop-id">{sid}.desktop</launchable>
  <url type="homepage">{escape(homepage)}</url>
  <developer id="com.tekkengreg">
    <name>{escape(dev)}</name>
  </developer>
{cat_block}{kw_block}{ss_block}  <icon type="stock">{sid}</icon>
  <content_rating type="oars-1.1"/>
  <releases>
    <release version="{escape(str(manifest.get('version', '1.0')))}" date="{manifest.get('date', '2026-01-01')}"/>
  </releases>
</component>
"""


def generate(site_dir: Path, out_root: Path) -> Path:
    manifest = load_manifest(site_dir)
    errors = validate(site_dir, manifest)
    if errors:
        for e in errors:
            print(f"  ✗ {e}", file=sys.stderr)
        raise SystemExit(f"erreur: manifeste invalide ({len(errors)} problème(s))")

    sid = manifest["id"]
    out = out_root / sid
    out.mkdir(parents=True, exist_ok=True)

    # site.json (runtime)
    import json
    (out / "site.json").write_text(
        json.dumps(runtime_site_json(manifest), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    # .desktop / .metainfo.xml
    (out / f"{sid}.desktop").write_text(desktop_file(manifest), encoding="utf-8")
    (out / f"{sid}.metainfo.xml").write_text(metainfo_xml(manifest), encoding="utf-8")

    # manifeste flatpak-builder
    with open(out / f"{sid}.yml", "w", encoding="utf-8") as fh:
        yaml.safe_dump(flatpak_manifest(manifest), fh, sort_keys=False,
                       default_flow_style=False, allow_unicode=True)

    # icône + engine (sources copiées → build self-contained)
    shutil.copy(site_dir / manifest["icon"], out / manifest["icon"])
    shutil.copy(ENGINE_REL, out / "bigbrowser.js")

    return out


# --- Commandes -------------------------------------------------------------

def cmd_validate(args):
    site_dir = Path(args.site_dir)
    manifest = load_manifest(site_dir)
    errors = validate(site_dir, manifest)
    if errors:
        for e in errors:
            print(f"  ✗ {e}", file=sys.stderr)
        raise SystemExit(1)
    print(f"✓ {manifest.get('id', site_dir.name)} : manifeste valide")


def cmd_generate(args):
    out = generate(Path(args.site_dir), Path(args.out))
    print(f"✓ artefacts générés dans {out}")
    for f in sorted(out.iterdir()):
        print(f"    {f.name}")


def cmd_build(args):
    out = generate(Path(args.site_dir), Path(args.out))
    manifest = load_manifest(Path(args.site_dir))
    sid = manifest["id"]
    cmd = ["flatpak-builder", "--force-clean", "--disable-rofiles-fuse"]
    if args.install:
        cmd += ["--user", "--install"]
    if args.repo:
        cmd += [f"--repo={args.repo}"]
    cmd += [str(out / ".build"), str(out / f"{sid}.yml")]
    print("→ " + " ".join(cmd))
    subprocess.run(cmd, check=True)
    print(f"✓ build OK. Lancer : flatpak run {sid}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="bbhub", description="Big Browser Hub tooling")
    sub = p.add_subparsers(dest="cmd", required=True)

    pv = sub.add_parser("validate", help="valide un site.yaml")
    pv.add_argument("site_dir")
    pv.set_defaults(func=cmd_validate)

    pg = sub.add_parser("generate", help="génère les artefacts Flatpak")
    pg.add_argument("site_dir")
    pg.add_argument("--out", default="dist")
    pg.set_defaults(func=cmd_generate)

    pb = sub.add_parser("build", help="génère puis build via flatpak-builder")
    pb.add_argument("site_dir")
    pb.add_argument("--out", default="dist")
    pb.add_argument("--install", action="store_true")
    pb.add_argument("--repo", default=None)
    pb.set_defaults(func=cmd_build)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
