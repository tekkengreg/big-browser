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


class AppstreamUrlsTests(unittest.TestCase):
    def test_homepage_par_defaut_sur_url(self):
        urls = bbhub.appstream_urls(VALID)
        self.assertEqual(urls["homepage"], VALID["url"])

    def test_homepage_explicite_prioritaire(self):
        urls = bbhub.appstream_urls(dict(VALID, homepage="https://example.org"))
        self.assertEqual(urls["homepage"], "https://example.org")

    def test_liens_du_hub_injectes(self):
        urls = bbhub.appstream_urls(VALID)
        for kind, value in bbhub.HUB_URLS.items():
            self.assertEqual(urls[kind], value)

    def test_surcharge_et_retrait(self):
        m = dict(VALID, urls={"bugtracker": "https://example.com/bugs", "help": ""})
        urls = bbhub.appstream_urls(m)
        self.assertEqual(urls["bugtracker"], "https://example.com/bugs")
        self.assertNotIn("help", urls)

    def test_ordre_appstream(self):
        urls = bbhub.appstream_urls(VALID)
        self.assertEqual(list(urls), [k for k in bbhub.URL_KINDS if k in urls])

    def test_type_inconnu_rejete(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            m = dict(VALID, urls={"store": "https://example.com"})
            site = make_site(Path(tmp.name), m)
            self.assertTrue(any("store" in e for e in bbhub.validate(site, m)))
        finally:
            tmp.cleanup()

    def test_url_non_http_rejetee(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            m = dict(VALID, urls={"help": "example.com"})
            site = make_site(Path(tmp.name), m)
            self.assertTrue(any("urls.help" in e for e in bbhub.validate(site, m)))
        finally:
            tmp.cleanup()


class HardwareRelationsTests(unittest.TestCase):
    def test_defaut_adaptatif(self):
        self.assertEqual(bbhub.hardware_relations(VALID),
                         ["keyboard", "pointing", "touch"])

    def test_desktop_seul(self):
        self.assertEqual(
            bbhub.hardware_relations(dict(VALID, form_factors=["desktop"])),
            ["keyboard", "pointing"])

    def test_mobile_seul(self):
        self.assertEqual(
            bbhub.hardware_relations(dict(VALID, form_factors=["mobile"])),
            ["touch"])

    def test_ordre_stable(self):
        """L'ordre des contrôles ne dépend pas de celui du YAML."""
        self.assertEqual(
            bbhub.hardware_relations(dict(VALID, form_factors=["mobile", "desktop"])),
            bbhub.hardware_relations(dict(VALID, form_factors=["desktop", "mobile"])))

    def test_facteur_inconnu_rejete(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            m = dict(VALID, form_factors=["tablet"])
            site = make_site(Path(tmp.name), m)
            self.assertTrue(any("tablet" in e for e in bbhub.validate(site, m)))
        finally:
            tmp.cleanup()

    def test_liste_vide_rejetee(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            m = dict(VALID, form_factors=[])
            site = make_site(Path(tmp.name), m)
            self.assertTrue(any("form_factors" in e for e in bbhub.validate(site, m)))
        finally:
            tmp.cleanup()

    def test_metainfo_contient_les_relations(self):
        xml = bbhub.metainfo_xml(VALID)
        self.assertIn("<recommends>", xml)
        self.assertIn("<control>touch</control>", xml)
        # `display_length` est volontairement absent (cf. bbhub.FORM_FACTORS).
        self.assertNotIn("display_length", xml)
        xml_desktop = bbhub.metainfo_xml(dict(VALID, form_factors=["desktop"]))
        self.assertNotIn("<control>touch</control>", xml_desktop)


class BrandingTests(unittest.TestCase):
    def test_defaut_violet_big_browser(self):
        light, dark = bbhub.brand_colors(VALID)
        self.assertNotEqual(light, dark)
        # La variante claire tire vers le blanc, la sombre vers le noir.
        self.assertGreater(int(light[1:3], 16), int(dark[1:3], 16))

    def test_couleur_declaree(self):
        light, dark = bbhub.brand_colors(dict(VALID, brand_color="#1db954"))
        self.assertEqual((light, dark), ("#56ca7f", "#10662e"))

    def test_noir_et_blanc_restent_dans_les_bornes(self):
        self.assertEqual(bbhub.brand_colors(dict(VALID, brand_color="#000000")),
                         ("#404040", "#000000"))
        self.assertEqual(bbhub.brand_colors(dict(VALID, brand_color="#ffffff")),
                         ("#ffffff", "#8c8c8c"))

    def test_hex_invalide_rejete(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            m = dict(VALID, brand_color="rouge")
            site = make_site(Path(tmp.name), m)
            self.assertTrue(any("brand_color" in e for e in bbhub.validate(site, m)))
        finally:
            tmp.cleanup()

    def test_metainfo_contient_branding(self):
        xml = bbhub.metainfo_xml(dict(VALID, brand_color="#1db954"))
        self.assertIn('<color type="primary" scheme_preference="light">#56ca7f</color>', xml)
        self.assertIn('<color type="primary" scheme_preference="dark">#10662e</color>', xml)


class ContentRatingTests(unittest.TestCase):
    def test_vide_par_defaut(self):
        self.assertIn('<content_rating type="oars-1.1"/>', bbhub.metainfo_xml(VALID))

    def test_attributs_declares(self):
        xml = bbhub.metainfo_xml(dict(VALID, content_rating={"social-chat": "intense"}))
        self.assertIn('<content_attribute id="social-chat">intense</content_attribute>', xml)

    def test_valeur_oars_invalide_rejetee(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            m = dict(VALID, content_rating={"social-chat": "beaucoup"})
            site = make_site(Path(tmp.name), m)
            self.assertTrue(any("content_rating" in e for e in bbhub.validate(site, m)))
        finally:
            tmp.cleanup()


class ReleaseNotesTests(unittest.TestCase):
    def test_sans_notes_release_vide(self):
        self.assertIn("<release version=", bbhub.metainfo_xml(VALID))
        self.assertNotIn("<description>\n        <p>", bbhub.metainfo_xml(VALID))

    def test_avec_notes(self):
        xml = bbhub.metainfo_xml(dict(VALID, release_notes="Un.\n\nDeux."))
        self.assertIn("<p>Un.</p>", xml)
        self.assertIn("<p>Deux.</p>", xml)


class ScreenshotTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_auto_decouverte_triee(self):
        site = make_site(self.tmp, VALID)
        shots = site / "screenshots"
        shots.mkdir()
        for name in ("2.png", "1.png", "notes.txt"):
            (shots / name).write_text("x", encoding="utf-8")
        urls = bbhub.screenshot_urls(site, VALID)
        self.assertEqual(len(urls), 2)
        self.assertTrue(urls[0].endswith(f"/sites/{VALID['id']}/screenshots/1.png"))
        self.assertTrue(urls[0].startswith(bbhub.SCREENSHOT_BASE))

    def test_sans_dossier(self):
        site = make_site(self.tmp, VALID)
        self.assertEqual(bbhub.screenshot_urls(site, VALID), [])

    def test_liste_explicite_prioritaire(self):
        site = make_site(self.tmp, VALID)
        (site / "screenshots").mkdir()
        (site / "screenshots" / "1.png").write_text("x", encoding="utf-8")
        m = dict(VALID, screenshots=["https://example.com/a.png"])
        self.assertEqual(bbhub.screenshot_urls(site, m), ["https://example.com/a.png"])

    def test_url_relative_rejetee(self):
        m = dict(VALID, screenshots=["captures/1.png"])
        site = make_site(self.tmp, m)
        self.assertTrue(any("screenshots" in e for e in bbhub.validate(site, m)))

    def test_generate_injecte_les_captures(self):
        site = make_site(self.tmp, VALID)
        (site / "screenshots").mkdir()
        (site / "screenshots" / "1.png").write_text("x", encoding="utf-8")
        out = bbhub.generate(site, self.tmp / "dist")
        xml = (out / f"{VALID['id']}.metainfo.xml").read_text(encoding="utf-8")
        self.assertIn('<screenshot type="default">', xml)
        self.assertIn("screenshots/1.png", xml)


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
