#!/usr/bin/env python3
"""Big Browser Hub — génération du catalogue web + fichiers d'installation.

Produit dans le dossier de sortie (_site/) :
    index.html                     catalogue de découverte
    bigbrowser.flatpakrepo         pour `flatpak remote-add`
    refs/<id>.flatpakref           install en 1 clic par Site
    icons/<id>.<ext>               icônes des Sites

Le dépôt OSTree (repo/) est assemblé à part par le workflow et copié dans _site/repo.

Usage :
    catalog.py --sites sites --out _site --base-url https://user.github.io/repo \
               [--gpg-key-file pubkey.gpg]
"""
from __future__ import annotations

import argparse
import base64
import html
import shutil
from pathlib import Path

import yaml

BRANCH = "stable"
RUNTIME_REPO = "https://flathub.org/repo/flathub.flatpakrepo"


def load_sites(sites_dir: Path) -> list[dict]:
    out = []
    for d in sorted(sites_dir.iterdir()):
        man = d / "site.yaml"
        if not man.exists():
            man = d / "site.yml"
        if not man.exists():
            continue
        with open(man, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        data["_dir"] = d
        out.append(data)
    return out


def gpg_key_b64(path: Path | None) -> str:
    if not path:
        return ""
    return base64.b64encode(path.read_bytes()).decode("ascii")


def write_flatpakrepo(out: Path, base_url: str, gpgb64: str):
    lines = [
        "[Flatpak Repo]",
        "Title=Big Browser Hub",
        f"Url={base_url}/repo",
        f"Homepage={base_url}",
        "Comment=Des webapps en applications autonomes",
    ]
    if gpgb64:
        lines.append(f"GPGKey={gpgb64}")
    (out / "bigbrowser.flatpakrepo").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_flatpakref(refs: Path, site: dict, base_url: str, gpgb64: str):
    sid = site["id"]
    lines = [
        "[Flatpak Ref]",
        f"Name={sid}",
        f"Branch={BRANCH}",
        f"Title={site.get('title', sid)}",
        f"Url={base_url}/repo",
        f"RuntimeRepo={RUNTIME_REPO}",
        "IsRuntime=false",
    ]
    if gpgb64:
        lines.append(f"GPGKey={gpgb64}")
    (refs / f"{sid}.flatpakref").write_text("\n".join(lines) + "\n", encoding="utf-8")


def card_html(site: dict, base_url: str) -> str:
    sid = site["id"]
    title = html.escape(site.get("title", sid))
    summary = html.escape(site.get("summary", ""))
    icon_ext = Path(site.get("icon", "icon.svg")).suffix
    return f"""    <article class="card">
      <img class="icon" src="icons/{sid}{icon_ext}" alt="{title}" width="96" height="96">
      <h2>{title}</h2>
      <p class="summary">{summary}</p>
      <a class="install" href="refs/{sid}.flatpakref">Installer</a>
      <code class="cli">flatpak install bigbrowser {sid}</code>
    </article>"""


def write_index(out: Path, sites: list[dict], base_url: str):
    cards = "\n".join(card_html(s, base_url) for s in sites)
    doc = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Big Browser Hub</title>
  <style>
    :root {{ color-scheme: light dark; }}
    body {{ font-family: system-ui, sans-serif; margin: 0; padding: 2rem;
           max-width: 1100px; margin-inline: auto; line-height: 1.5; }}
    header h1 {{ margin-bottom: .2rem; }}
    header p {{ color: gray; margin-top: 0; }}
    .setup {{ background: #0001; padding: 1rem 1.2rem; border-radius: 12px; margin: 1.5rem 0; }}
    .setup code {{ display: block; padding: .3rem 0; }}
    .grid {{ display: grid; gap: 1.2rem;
            grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); }}
    .card {{ border: 1px solid #8884; border-radius: 14px; padding: 1.2rem;
            display: flex; flex-direction: column; align-items: flex-start; }}
    .icon {{ border-radius: 16px; }}
    .card h2 {{ font-size: 1.1rem; margin: .6rem 0 .2rem; }}
    .summary {{ color: gray; flex: 1; }}
    .install {{ background: #3a6ea5; color: #fff; text-decoration: none;
               padding: .5rem 1rem; border-radius: 8px; font-weight: 600; }}
    .cli {{ font-size: .8rem; color: gray; margin-top: .6rem; word-break: break-all; }}
  </style>
</head>
<body>
  <header>
    <h1>Big Browser Hub</h1>
    <p>Des webapps en applications autonomes, au niveau système.</p>
  </header>
  <section class="setup">
    <strong>Ajouter le dépôt (une fois) :</strong>
    <code>flatpak remote-add --if-not-exists bigbrowser {base_url}/bigbrowser.flatpakrepo</code>
    <strong>Puis installer un Site :</strong>
    <code>flatpak install bigbrowser &lt;id&gt;</code>
  </section>
  <main class="grid">
{cards}
  </main>
</body>
</html>
"""
    (out / "index.html").write_text(doc, encoding="utf-8")


def main(argv=None):
    p = argparse.ArgumentParser(prog="catalog")
    p.add_argument("--sites", default="sites")
    p.add_argument("--out", default="_site")
    p.add_argument("--base-url", required=True)
    p.add_argument("--gpg-key-file", default=None)
    args = p.parse_args(argv)

    out = Path(args.out)
    refs = out / "refs"
    icons = out / "icons"
    for d in (out, refs, icons):
        d.mkdir(parents=True, exist_ok=True)

    base_url = args.base_url.rstrip("/")
    gpgb64 = gpg_key_b64(Path(args.gpg_key_file) if args.gpg_key_file else None)
    sites = load_sites(Path(args.sites))

    write_flatpakrepo(out, base_url, gpgb64)
    for s in sites:
        write_flatpakref(refs, s, base_url, gpgb64)
        icon = s.get("icon", "icon.svg")
        src = s["_dir"] / icon
        if src.exists():
            shutil.copy(src, icons / f"{s['id']}{Path(icon).suffix}")
    write_index(out, sites, base_url)

    print(f"✓ catalogue généré dans {out}/ ({len(sites)} Site(s))")


if __name__ == "__main__":
    main()
