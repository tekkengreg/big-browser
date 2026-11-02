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
# Étiquette de langue : sous-tag principal, éventuellement régionalisé (pt-BR).
LANG_TAG_RE = re.compile(r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$")
RUNTIME_KEYS = ("id", "title", "url", "icon", "allowed_domains", "languages",
                "permissions", "inject_css", "inject_js", "ignore_tls_errors")
REQUIRED = ("id", "title", "url", "icon", "summary", "description", "project_license")

# --- URL paramétrée par la langue -----------------------------------------
# L'Engine substitue `{lang}` (sous-tag principal : fr) et `{locale}`
# (étiquette complète : fr-FR) dans `url` au lancement, d'après la langue du
# système ou la surcharge choisie au menu. Un Site comme Wikipédia suit ainsi
# la langue du bureau (https://{lang}.wikipedia.org) au lieu d'être figé sur
# une édition. Le gabarit n'étant pas une URL valide, `homepage` devient requis
# pour que le metainfo garde un lien « Page d'accueil » cliquable.
URL_PLACEHOLDER_RE = re.compile(r"\{(?:lang|locale)\}")

# --- Liens du store (Big Browser Hub) -------------------------------------
# Un Site n'est pas publié par l'éditeur de la webapp : son « projet », au sens
# AppStream, c'est le Hub. On injecte donc d'office les liens du store dans le
# metainfo. Côté GNOME Logiciels : `help` et `bugtracker` deviennent les lignes
# « Aide » et « Signaler un problème » de la section « Liens », `contribute`
# alimente le bouton « S'impliquer » de la vignette de licence (Sites libres
# uniquement) ; `vcs-browser` est ignoré par GNOME Logiciels mais attendu par
# les linters Flathub et d'autres stores.
HUB_URL = "https://tekkengreg.github.io/big-browser"
SOURCE_URL = "https://github.com/tekkengreg/big-browser"
HUB_URLS = {
    "help": HUB_URL,
    "bugtracker": f"{SOURCE_URL}/issues",
    "vcs-browser": SOURCE_URL,
    "contribute": f"{SOURCE_URL}/blob/main/CONTRIBUTING.md",
}
# Types d'URL reconnus par AppStream, dans l'ordre où on les écrit.
URL_KINDS = ("homepage", "help", "bugtracker", "faq", "donation",
             "translate", "contact", "vcs-browser", "contribute")

# --- Facteurs de forme (vignette « Matériel » de GNOME Logiciels) ---------
# Un Site n'est qu'une WebView sans chrome propre : il suit la webapp, qui est
# responsive la plupart du temps, et la fenêtre n'impose aucune taille minimale.
# On déclare donc par défaut clavier + pointeur + tactile en `recommends` (qui
# veut dire « supporte » côté AppStream) : c'est la combinaison exacte que
# GNOME Logiciels exige pour afficher le badge vert « Adaptatif ». Sans aucune
# de ces relations, il retombe sur son repli « Ordinateur uniquement ».
#
# Pas de `<requires><display_length>` : `appstreamcli compose` le dépouille de
# ses attributs `compare`/`side` au passage dans le catalogue, et GNOME
# Logiciels ne lit la valeur en pixels que si `side` est présent (le reste est
# compilé hors build depuis AppStream 1.0). La relation ne peut donc plus rien
# affirmer, tout en gardant le pouvoir de déclencher une vignette rouge si elle
# ne correspond pas. Les `<control>` suffisent.
FORM_FACTORS = ("desktop", "mobile")
FORM_FACTOR_CONTROLS = {
    "desktop": ("keyboard", "pointing"),
    "mobile": ("touch",),
}

# --- Couleur de marque ------------------------------------------------------
# GNOME Logiciels lit `<branding>` (gs-appstream.c) et s'en sert pour teinter la
# grande tuile de mise en avant ; sans elle il devine une couleur depuis
# l'icône, ce qui donnerait le même violet à tous les Sites (toutes nos icônes
# partagent le cadre BB). Un seul hex suffit dans le site.yaml : les deux
# variantes clair/sombre en sont dérivées, la couleur étant affichée *derrière*
# l'icône et devant donc s'en distinguer.
DEFAULT_BRAND_COLOR = "#6965db"          # violet Big Browser
BRAND_LIGHTEN = 0.25                     # part de blanc, variante claire
BRAND_DARKEN = 0.45                      # part de noir, variante sombre
HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

# --- Classement d'âge -------------------------------------------------------
# Valeurs OARS 1.1. Par défaut on n'affirme rien (`<content_rating>` vide), ce
# que font aussi les vrais navigateurs empaquetés : un Site n'a pas de contenu
# propre, il affiche celui de la webapp.
OARS_VALUES = ("none", "mild", "moderate", "intense")

# --- Captures d'écran -------------------------------------------------------
# Les PNG commités dans `sites/<id>/screenshots/` sont servis par
# raw.githubusercontent.com, et non par le Hub : `appstreamcli compose`
# télécharge chaque image au build pour en relever les dimensions, or le Hub
# n'est déployé qu'*après* le build (GitHub Pages publie en fin de workflow).
# Vérifié : une URL distante traverse le compose intacte, enrichie de
# `width`/`height`.
SCREENSHOT_BASE = "https://raw.githubusercontent.com/tekkengreg/big-browser/main"
SCREENSHOT_SUFFIXES = (".png", ".jpg", ".jpeg")


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
    if url and URL_PLACEHOLDER_RE.search(url) and not manifest.get("homepage"):
        errors.append(f"url '{url}' est paramétrée par la langue : "
                      "renseignez 'homepage' (lien du catalogue)")

    langs = manifest.get("languages")
    if langs is not None:
        if not isinstance(langs, list) or not langs:
            errors.append("languages : doit être une liste non vide de codes "
                          "BCP 47 (ex. [fr, en, de])")
        else:
            for code in langs:
                if not isinstance(code, str) or not LANG_TAG_RE.match(code):
                    errors.append(f"languages : '{code}' n'est pas un code BCP 47 "
                                  "(ex. fr, en, pt-BR)")

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

    shots = manifest.get("screenshots", [])
    if shots and not isinstance(shots, list):
        errors.append("screenshots : doit être une liste d'URLs")
    elif shots:
        for shot in shots:
            if not str(shot).startswith(("http://", "https://")):
                errors.append(f"screenshots : '{shot}' doit être une URL http(s) "
                              "(les PNG de sites/<id>/screenshots/ sont trouvés seuls)")

    brand = manifest.get("brand_color")
    if brand and not HEX_COLOR_RE.match(str(brand)):
        errors.append(f"brand_color '{brand}' : attendu un hex #rrggbb")

    rating = manifest.get("content_rating", {})
    if rating and not isinstance(rating, dict):
        errors.append("content_rating : doit être un mapping <attribut OARS>: <valeur>")
    elif rating:
        for attr, value in rating.items():
            if value not in OARS_VALUES:
                errors.append(f"content_rating.{attr} : valeur '{value}' invalide "
                              f"(attendu : {', '.join(OARS_VALUES)})")

    factors = manifest.get("form_factors")
    if factors is not None:
        if not isinstance(factors, list) or not factors:
            errors.append("form_factors : doit être une liste non vide "
                          f"({', '.join(FORM_FACTORS)})")
        else:
            for factor in factors:
                if factor not in FORM_FACTORS:
                    errors.append(f"form_factors : '{factor}' inconnu "
                                  f"(attendu : {', '.join(FORM_FACTORS)})")

    urls = manifest.get("urls", {})
    if urls and not isinstance(urls, dict):
        errors.append("urls : doit être un mapping <type AppStream>: <url>")
    elif urls:
        for kind, value in urls.items():
            if kind not in URL_KINDS:
                errors.append(f"urls : type '{kind}' inconnu "
                              f"(attendu : {', '.join(URL_KINDS)})")
            elif value and not str(value).startswith(("http://", "https://")):
                errors.append(f"urls.{kind} : doit être une URL http(s) ('{value}')")

    return errors


# --- Génération des artefacts ----------------------------------------------

def runtime_site_json(manifest: dict) -> dict:
    out = {k: manifest[k] for k in RUNTIME_KEYS if k in manifest}
    out.setdefault("permissions", {})
    return out


def appstream_urls(manifest: dict) -> dict[str, str]:
    """Liens AppStream d'un Site : la webapp en `homepage`, le Hub pour le reste.

    Le champ `urls` du site.yaml surcharge n'importe quelle entrée ; une valeur
    vide retire le lien (ex. `urls: {help: ""}`).
    """
    urls = {"homepage": manifest.get("homepage") or manifest["url"]}
    urls.update(HUB_URLS)
    for kind, value in (manifest.get("urls") or {}).items():
        if value:
            urls[kind] = value
        else:
            urls.pop(kind, None)
    return {k: urls[k] for k in URL_KINDS if urls.get(k)}


def screenshot_urls(site_dir: Path, manifest: dict) -> list[str]:
    """URLs des captures : `screenshots` du site.yaml, sinon auto-découverte."""
    explicit = manifest.get("screenshots") or []
    if explicit:
        return [str(u) for u in explicit]
    shots = site_dir / "screenshots"
    if not shots.is_dir():
        return []
    names = sorted(f.name for f in shots.iterdir()
                   if f.suffix.lower() in SCREENSHOT_SUFFIXES)
    return [f"{SCREENSHOT_BASE}/sites/{manifest['id']}/screenshots/{n}" for n in names]


def _mix(color: str, target: int, ratio: float) -> str:
    """Mélange `color` (#rrggbb) vers `target` (0 = noir, 255 = blanc)."""
    channels = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return "#" + "".join(
        f"{round(c + (target - c) * ratio):02x}" for c in channels)


def brand_colors(manifest: dict) -> tuple[str, str]:
    """(variante claire, variante sombre) dérivées de `brand_color`."""
    base = manifest.get("brand_color") or DEFAULT_BRAND_COLOR
    return (_mix(base, 255, BRAND_LIGHTEN), _mix(base, 0, BRAND_DARKEN))


def hardware_relations(manifest: dict) -> list[str]:
    """Contrôles recommandés d'un Site, d'après `form_factors`."""
    factors = manifest.get("form_factors") or list(FORM_FACTORS)
    controls: list[str] = []
    for factor in FORM_FACTORS:          # ordre stable, indépendant du YAML
        if factor not in factors:
            continue
        for control in FORM_FACTOR_CONTROLS[factor]:
            if control not in controls:
                controls.append(control)
    return controls


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
    url_block = "\n".join(f'  <url type="{kind}">{escape(value)}</url>'
                          for kind, value in appstream_urls(manifest).items())

    light, dark = brand_colors(manifest)
    branding_block = (
        '  <branding>\n'
        f'    <color type="primary" scheme_preference="light">{light}</color>\n'
        f'    <color type="primary" scheme_preference="dark">{dark}</color>\n'
        '  </branding>\n')

    rating = manifest.get("content_rating") or {}
    if rating:
        items = "\n".join(
            f'    <content_attribute id="{escape(attr)}">{escape(value)}</content_attribute>'
            for attr, value in sorted(rating.items()))
        rating_block = f'  <content_rating type="oars-1.1">\n{items}\n  </content_rating>\n'
    else:
        rating_block = '  <content_rating type="oars-1.1"/>\n'

    notes = str(manifest.get("release_notes", "") or "").strip()
    release_attrs = (f'version="{escape(str(manifest.get("version", "1.0")))}" '
                     f'date="{manifest.get("date", "2026-01-01")}"')
    if notes:
        paras = "\n".join(f"        <p>{escape(n.strip())}</p>"
                           for n in notes.split("\n\n") if n.strip())
        release_block = (f'    <release {release_attrs}>\n'
                         f'      <description>\n{paras}\n      </description>\n'
                         '    </release>\n')
    else:
        release_block = f'    <release {release_attrs}/>\n'

    controls = hardware_relations(manifest)
    hw_block = ""
    if controls:
        items = "\n".join(f"    <control>{c}</control>" for c in controls)
        hw_block = f"  <recommends>\n{items}\n  </recommends>\n"

    screenshots = manifest.get("screenshots", []) or []
    ss_block = ""
    if screenshots:
        # GNOME Logiciels affiche la légende sous le carrousel ; sans elle
        # `appstreamcli validate --pedantic` signale `screenshot-no-caption`.
        caption = escape(manifest.get(
            "screenshot_caption", f"{manifest['title']} dans sa fenêtre Big Browser"))
        imgs = "\n".join(
            f"    <screenshot{' type=\"default\"' if i == 0 else ''}>\n"
            f"      <caption>{caption}</caption>\n"
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
{url_block}
{hw_block}  <developer id="com.tekkengreg">
    <name>{escape(dev)}</name>
  </developer>
{cat_block}{kw_block}{ss_block}  <icon type="stock">{sid}</icon>
{branding_block}{rating_block}  <releases>
{release_block}  </releases>
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

    # Captures auto-découvertes dans sites/<id>/screenshots/ si le site.yaml
    # n'en liste pas explicitement.
    manifest["screenshots"] = screenshot_urls(site_dir, manifest)

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


def flatpak_builder_cmd() -> list[str]:
    """Localise flatpak-builder, avec repli pour les hôtes immuables (Silverblue).

    Ordre : binaire natif → Flatpak `org.flatpak.Builder` → idem via
    `flatpak-spawn --host` (cas toolbox, où seul l'hôte a flatpak).
    """
    if shutil.which("flatpak-builder"):
        return ["flatpak-builder"]
    for prefix in (["flatpak"], ["flatpak-spawn", "--host", "flatpak"]):
        if not shutil.which(prefix[0]):
            continue
        probe = subprocess.run(prefix + ["info", "org.flatpak.Builder"],
                               capture_output=True)
        if probe.returncode == 0:
            return prefix + ["run", "org.flatpak.Builder"]
    raise SystemExit(
        "✗ flatpak-builder introuvable. Installez-le (dnf install flatpak-builder) "
        "ou installez le Flatpak : flatpak install flathub org.flatpak.Builder")


def cmd_build(args):
    out = generate(Path(args.site_dir), Path(args.out))
    manifest = load_manifest(Path(args.site_dir))
    sid = manifest["id"]
    cmd = flatpak_builder_cmd() + ["--force-clean", "--disable-rofiles-fuse"]
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
