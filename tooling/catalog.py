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
import re
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


def source_url(base_url: str) -> str | None:
    """Déduit l'URL du dépôt GitHub depuis l'URL Pages (best-effort).

    https://user.github.io/repo  →  https://github.com/user/repo
    """
    m = re.match(r"https?://([^./]+)\.github\.io/([^/]+)", base_url)
    return f"https://github.com/{m.group(1)}/{m.group(2)}" if m else None


def card_html(site: dict, base_url: str) -> str:
    sid = site["id"]
    title = html.escape(site.get("title", sid))
    summary = html.escape(site.get("summary", ""))
    icon_ext = Path(site.get("icon", "icon.svg")).suffix
    return f"""      <article class="card">
        <img class="icon" src="icons/{sid}{icon_ext}" alt="{title}" width="88" height="88">
        <h3>{title}</h3>
        <p class="summary">{summary}</p>
        <a class="install" href="refs/{sid}.flatpakref">Installer</a>
        <code class="cli">flatpak install bigbrowser {sid}</code>
      </article>"""


def write_index(out: Path, sites: list[dict], base_url: str):
    cards = "\n".join(card_html(s, base_url) for s in sites)
    count = len(sites)
    src = source_url(base_url)
    src_link = (f'<a href="{src}">Code source</a> · ' if src else "")
    doc = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Big Browser — chaque webapp, une application autonome</title>
  <meta name="description" content="Big Browser transforme chaque webapp en application autonome au niveau système : sa fenêtre, son icône, sa sandbox. Installable en un clic via Flatpak.">
  <style>
    :root {{
      color-scheme: light dark;
      --bb: #6965db;
      --bb-dark: #514dc0;
      --card: #fff;
      --ink: #1b1b22;
      --muted: #6b6b76;
      --line: #8882;
      --bg: #f6f6fb;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{ --card: #1c1c24; --ink: #ececf2; --muted: #a0a0ad; --bg: #121218; }}
    }}
    * {{ box-sizing: border-box; }}
    body {{ font-family: system-ui, -apple-system, sans-serif; margin: 0;
           color: var(--ink); background: var(--bg); line-height: 1.6; }}
    .wrap {{ max-width: 1080px; margin-inline: auto; padding: 0 1.5rem; }}
    a {{ color: var(--bb); }}

    .hero {{ text-align: center; padding: 4.5rem 1.5rem 3rem;
            background: radial-gradient(120% 120% at 50% 0%, #6965db22, transparent 60%); }}
    .hero .logo {{ display: inline-flex; align-items: center; justify-content: center;
            width: 84px; height: 84px; border-radius: 22px; background: var(--bb);
            color: #fff; font-weight: 800; font-size: 2rem; letter-spacing: -1px;
            box-shadow: 0 12px 30px #6965db55; margin-bottom: 1.2rem; }}
    .hero h1 {{ font-size: clamp(2rem, 5vw, 3rem); margin: .2rem 0 .6rem; letter-spacing: -1px; }}
    .hero p {{ font-size: 1.2rem; color: var(--muted); max-width: 38ch; margin: 0 auto 1.8rem; }}
    .cta {{ display: inline-block; background: var(--bb); color: #fff; text-decoration: none;
           padding: .8rem 1.6rem; border-radius: 10px; font-weight: 700;
           box-shadow: 0 8px 20px #6965db44; }}
    .cta:hover {{ background: var(--bb-dark); }}

    section {{ padding: 2.5rem 0; }}
    h2 {{ font-size: 1.5rem; letter-spacing: -.5px; }}
    .features {{ display: grid; gap: 1.2rem;
               grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }}
    .feature {{ background: var(--card); border: 1px solid var(--line);
              border-radius: 14px; padding: 1.3rem; }}
    .feature h3 {{ margin: .2rem 0 .4rem; font-size: 1.05rem; }}
    .feature p {{ margin: 0; color: var(--muted); font-size: .95rem; }}

    .setup {{ background: var(--card); border: 1px solid var(--line);
             padding: 1.4rem 1.6rem; border-radius: 14px; }}
    .setup code {{ display: block; padding: .45rem .7rem; margin: .5rem 0; border-radius: 8px;
                 background: #6965db14; font-family: ui-monospace, monospace;
                 font-size: .9rem; overflow-x: auto; }}
    .setup .step {{ font-weight: 700; margin-top: 1rem; }}

    .grid {{ display: grid; gap: 1.2rem;
            grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); }}
    .card {{ background: var(--card); border: 1px solid var(--line); border-radius: 16px;
            padding: 1.4rem; display: flex; flex-direction: column; align-items: flex-start; }}
    .card .icon {{ border-radius: 18px; }}
    .card h3 {{ font-size: 1.15rem; margin: .7rem 0 .3rem; }}
    .summary {{ color: var(--muted); flex: 1; font-size: .95rem; }}
    .install {{ background: var(--bb); color: #fff; text-decoration: none; align-self: stretch;
               text-align: center; padding: .55rem 1rem; border-radius: 9px; font-weight: 700;
               margin-top: .4rem; }}
    .install:hover {{ background: var(--bb-dark); }}
    .cli {{ font-size: .78rem; color: var(--muted); margin-top: .7rem; word-break: break-all; }}

    footer {{ text-align: center; color: var(--muted); padding: 3rem 1.5rem;
             border-top: 1px solid var(--line); margin-top: 2rem; font-size: .9rem; }}
  </style>
</head>
<body>
  <header class="hero">
    <div class="logo">BB</div>
    <h1>Big Browser</h1>
    <p>Chaque webapp devient une application autonome au niveau système.</p>
    <a class="cta" href="#catalogue">Découvrir les Sites ({count})</a>
  </header>

  <main class="wrap">
    <section>
      <h2>Un nouveau genre de navigateur</h2>
      <p style="color: var(--muted); max-width: 60ch;">
        Là où un navigateur classique empile des onglets dans un seul processus,
        Big Browser promeut chaque site au rang d'application : sa propre fenêtre,
        son icône, sa sandbox et son stockage isolé. Installable et désinstallable
        comme n'importe quelle app, via Flatpak.
      </p>
      <div class="features">
        <div class="feature"><h3>🪟 Fenêtre dédiée</h3>
          <p>Chaque Site vit dans sa propre fenêtre, avec son entrée de menu et son icône.</p></div>
        <div class="feature"><h3>🔒 Isolé &amp; sandboxé</h3>
          <p>Cookies et stockage cloisonnés par Site ; permissions Flatpak explicites.</p></div>
        <div class="feature"><h3>📦 Installation 1 clic</h3>
          <p>Un dépôt Flatpak standard : <code>remote-add</code> puis <code>install</code>.</p></div>
        <div class="feature"><h3>🔄 Mises à jour</h3>
          <p>Les Sites se mettent à jour comme toute application Flatpak.</p></div>
      </div>
    </section>

    <section>
      <h2>Démarrer en deux commandes</h2>
      <div class="setup">
        <div class="step">1. Ajouter le dépôt (une seule fois)</div>
        <code>flatpak remote-add --if-not-exists bigbrowser {base_url}/bigbrowser.flatpakrepo</code>
        <div class="step">2. Installer un Site</div>
        <code>flatpak install bigbrowser &lt;id&gt;</code>
        <p style="color: var(--muted); margin: .8rem 0 0;">Ou cliquez sur « Installer » sous un Site
        ci-dessous (fichier <code>.flatpakref</code>).</p>
      </div>
    </section>

    <section id="catalogue">
      <h2>Catalogue des Sites</h2>
      <div class="grid">
{cards}
      </div>
    </section>
  </main>

  <footer>
    {src_link}Big Browser Hub — des webapps en applications autonomes.<br>
    Distribué via Flatpak &amp; GitHub Pages.
  </footer>
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
