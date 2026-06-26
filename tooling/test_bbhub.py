#!/usr/bin/env python3
"""Tests du tooling Big Browser (bbhub).

Couvre la validation des manifestes et la génération des artefacts Flatpak à
partir d'un faux Site monté dans un dossier temporaire.

Dépendance : PyYAML (comme bbhub). Lancement :
    python3 -m unittest discover -s tooling -p 'test_*.py'
    # ou : python3 tooling/test_bbhub.py
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import yaml

import bbhub

# Manifeste valide minimal (tous les champs requis).
VALID = {
    "id": "com.tekkengreg.bigbrowser.TestSite",
    "title": "Test Site",
    "url": "https://example.com",
    "icon": "icon.svg",
    "summary": "Un site de test",
    "description": "Description du site de test.\n\nDeuxième paragraphe.",
    "project_license": "MIT",
}


def make_site(tmp: Path, manifest: dict, *, dir_name: str | None = None,
              icon_name: str | None = "icon.svg") -> Path:
    """Crée sites/<dir>/site.yaml (+ icône) et retourne le dossier du Site."""
    site_dir = tmp / (dir_name if dir_name is not None else manifest["id"])
    site_dir.mkdir(parents=True, exist_ok=True)
    (site_dir / "site.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    if icon_name is not None:
        (site_dir / icon_name).write_text("<svg/>", encoding="utf-8")
    return site_dir


class ValidateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_manifeste_valide(self):
        site = make_site(self.tmp, VALID)
        self.assertEqual(bbhub.validate(site, VALID), [])

    def test_champ_requis_manquant(self):
        m = {k: v for k, v in VALID.items() if k != "summary"}
        site = make_site(self.tmp, m)
        errors = bbhub.validate(site, m)
        self.assertTrue(any("summary" in e for e in errors))

    def test_url_non_https(self):
        m = dict(VALID, url="http://example.com")
        site = make_site(self.tmp, m)
        self.assertTrue(any("https" in e for e in bbhub.validate(site, m)))

    def test_id_hors_namespace(self):
        m = dict(VALID, id="com.example.App")
        # dossier nommé comme l'id pour isoler l'erreur de namespace
        site = make_site(self.tmp, m, dir_name="com.example.App")
        self.assertTrue(any("com.tekkengreg.bigbrowser." in e for e in bbhub.validate(site, m)))

    def test_dossier_different_de_id(self):
        site = make_site(self.tmp, VALID, dir_name="com.tekkengreg.bigbrowser.Autre")
        errors = bbhub.validate(site, VALID)
        self.assertTrue(any("doit être nommé" in e for e in errors))

    def test_icone_absente(self):
        site = make_site(self.tmp, VALID, icon_name=None)
        self.assertTrue(any("icône introuvable" in e for e in bbhub.validate(site, VALID)))


class FinishArgsTests(unittest.TestCase):
    def test_base_inclut_telechargements(self):
        args = bbhub.finish_args(VALID)
        self.assertIn("--share=network", args)
        self.assertIn("--filesystem=xdg-download:create", args)

    def test_permission_media(self):
        args = bbhub.finish_args(dict(VALID, permissions={"media": True}))
        self.assertIn("--device=all", args)
        self.assertIn("--socket=pulseaudio", args)

    def test_permission_notifications(self):
        args = bbhub.finish_args(dict(VALID, permissions={"notifications": True}))
        self.assertIn("--talk-name=org.freedesktop.Notifications", args)

    def test_pas_de_permission_pas_de_supplement(self):
        args = bbhub.finish_args(VALID)
        self.assertNotIn("--device=all", args)
        self.assertNotIn("--talk-name=org.freedesktop.Notifications", args)

    def test_finish_args_extra_dedupe(self):
        m = dict(VALID, finish_args_extra=["--share=network", "--talk-name=org.example"])
        args = bbhub.finish_args(m)
        self.assertEqual(args.count("--share=network"), 1)  # pas de doublon
        self.assertIn("--talk-name=org.example", args)


class RuntimeJsonTests(unittest.TestCase):
    def test_sous_ensemble_runtime(self):
        m = dict(VALID, allowed_domains=["example.com"],
                 inject_js="x", developer_name="Moi", homepage="https://h")
        out = bbhub.runtime_site_json(m)
        # garde les clés runtime…
        self.assertEqual(out["id"], m["id"])
        self.assertEqual(out["allowed_domains"], ["example.com"])
        # …et écarte les métadonnées catalogue
        self.assertNotIn("developer_name", out)
        self.assertNotIn("homepage", out)
        self.assertNotIn("summary", out)
        # permissions toujours présent (au moins vide)
        self.assertIn("permissions", out)


class GenerateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.site = make_site(self.tmp, dict(VALID, categories=["Network"]))
        self.out_root = self.tmp / "dist"
        self.out = bbhub.generate(self.site, self.out_root)

    def tearDown(self):
        self._tmp.cleanup()

    def test_artefacts_produits(self):
        sid = VALID["id"]
        for name in (f"{sid}.yml", f"{sid}.desktop", f"{sid}.metainfo.xml",
                     "site.json", "icon.svg", "bigbrowser.js"):
            self.assertTrue((self.out / name).exists(), f"manque : {name}")

    def test_site_json_runtime(self):
        data = json.loads((self.out / "site.json").read_text(encoding="utf-8"))
        self.assertEqual(data["url"], VALID["url"])
        self.assertNotIn("summary", data)  # métadonnée écartée du runtime

    def test_manifest_flatpak_coherent(self):
        sid = VALID["id"]
        manifest = yaml.safe_load((self.out / f"{sid}.yml").read_text(encoding="utf-8"))
        self.assertEqual(manifest["app-id"], sid)
        self.assertEqual(manifest["command"], "bigbrowser")
        self.assertIn("--filesystem=xdg-download:create", manifest["finish-args"])

    def test_desktop_et_metainfo(self):
        sid = VALID["id"]
        desktop = (self.out / f"{sid}.desktop").read_text(encoding="utf-8")
        self.assertIn(f"Name={VALID['title']}", desktop)
        self.assertIn("Categories=Network;", desktop)
        metainfo = (self.out / f"{sid}.metainfo.xml").read_text(encoding="utf-8")
        self.assertIn(f"<id>{sid}</id>", metainfo)
        self.assertIn(VALID["summary"], metainfo)


if __name__ == "__main__":
    unittest.main()
