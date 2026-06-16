# Politique de modération des Sites

Big Browser enrobe des webapps tierces en applications autonomes et les distribue via le Hub. Cette
page définit ce qui est **accepté**, **refusé**, et la **procédure** de revue. Elle complète le
[guide de contribution](CONTRIBUTING.md) et le [code de conduite](CODE_OF_CONDUCT.md).

> Principe directeur : un Site est un **emballage** d'un service web existant. On facilite l'accès à
> un site, on ne le réédite pas, on ne l'altère pas trompeusement, et on n'usurpe pas l'identité de
> son éditeur.

## Critères d'acceptation

Un Site est recevable s'il respecte **tout** ce qui suit :

- **Namespace** : `id` sous `io.bigbrowser.*`, unique, et dossier nommé exactement comme l'`id`.
  Le préfixe `io.bigbrowser.` évite d'usurper l'app-id de marque de l'éditeur.
- **Transport** : `url` en `https://`.
- **Licence** : `project_license` renseignée honnêtement — licence réelle de la webapp si connue,
  sinon `LicenseRef-proprietary`. Ne pas déclarer une licence ouverte par défaut.
- **Périmètre** : `allowed_domains` cohérents avec le service ; pas de domaines sans rapport.
- **Permissions** : demandées au strict nécessaire (notifications/géoloc/média justifiées par
  l'usage réel de l'app).
- **Métadonnées** : `summary`/`description` factuelles, sans superlatif trompeur ni fausse
  affiliation. L'icône doit être lisible et représentative.

## Motifs de refus

Un Site sera refusé (ou retiré du Hub) s'il :

- **usurpe une marque** : se fait passer pour l'éditeur officiel, ou laisse croire à un partenariat
  inexistant ; détourne un logo de façon trompeuse ;
- **enfreint le droit d'auteur ou les CGU** du service enrobé (ex. contournement de paywall,
  réinjection publicitaire, scraping interdit) ;
- **injecte du code hostile** : `inject_css`/`inject_js` ou `finish_args_extra` servant à exfiltrer
  des données, masquer des avertissements de sécurité, ou modifier le service à l'insu de
  l'utilisateur ;
- **désactive la sécurité** : `ignore_tls_errors: true` en production (réservé au debug local) ;
- **réclame des permissions excessives** sans justification (`finish_args_extra` ouvrant le système
  de fichiers hôte, le bus de session, etc.) ;
- **pointe vers du contenu illégal** ou contraire au code de conduite (haine, harcèlement, contenu
  sexuel impliquant des mineurs, etc.) ;
- **est un doublon** d'un Site existant sans valeur ajoutée.

## Procédure de revue

1. La **CI** valide le manifeste, génère et builde le Site, et publie un bundle `.flatpak` d'essai.
2. Un **mainteneur** (cf. `.github/CODEOWNERS`) revoit le manifeste au regard des critères ci-dessus.
3. Au **merge sur `main`**, le Site est publié automatiquement sur le Hub.
4. **Retrait a posteriori** : un Site déjà publié peut être retiré (suppression du dossier
   `sites/<id>/` + republication) s'il s'avère non conforme ou sur demande légitime de l'éditeur.

## Signalement

Pour signaler un Site problématique (marque, licence, sécurité, contenu) : ouvrir une *Issue* ou
écrire à **greg@tekkengreg.com**. Les signalements de sécurité sont traités en priorité.
