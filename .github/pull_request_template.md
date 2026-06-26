<!--
Merci pour votre contribution ! Décrivez ci-dessous, puis cochez la checklist correspondante.
Pour ajouter un Site, voir CONTRIBUTING.md.
-->

## Description

<!-- Que fait cette PR ? Pour un nouveau Site : nom + URL. Lien vers l'Issue éventuelle (Closes #...). -->

## Type de contribution

- [ ] Nouveau Site (`sites/com.tekkengreg.bigbrowser.*`)
- [ ] Modification d'un Site existant
- [ ] Cœur : Engine / tooling / CI
- [ ] Documentation

## Checklist — nouveau Site / modification

- [ ] Le dossier est `sites/com.tekkengreg.bigbrowser.<Nom>/` et porte exactement l'`id` du `site.yaml`.
- [ ] `python3 tooling/bbhub.py validate sites/com.tekkengreg.bigbrowser.<Nom>` passe.
- [ ] Testé en local : `bbhub.py build ... --install` puis `flatpak run com.tekkengreg.bigbrowser.<Nom>`.
- [ ] `url` en https:// ; `project_license` renseignée honnêtement.
- [ ] Je n'ai modifié **que** `site.yaml` + l'icône (pas d'artefacts générés à la main).

## Checklist — cœur (Engine / tooling)

- [ ] Engine testé : `gjs engine/bigbrowser.js examples/wikipedia.site.json`.
- [ ] Si un champ requis a été ajouté : mis à jour dans `bbhub.py` **et** `site.schema.json`.
- [ ] Je comprends qu'une modif de l'Engine impose un rebuild de tous les Sites (fait par `publish.yml`).
