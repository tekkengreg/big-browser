# Flatpak

## Créer un dépôt local 

```sh
flatpak remote-add --user --no-gpg-verify local-repo file:///home/tekkengreg/Workspace/big-browser/repo
```

## Ajout d'un dépôt local

```sh
flatpak remote-add --user --no-gpg-verify local-repo ./repo
```

## Supprimer et recréer le dépôt local :

```sh
flatpak remote-delete --user local-repo
```

## Gestion

```sh
# Lister vos apps installées
flatpak list --app | grep tekkengreg

# Mettre à jour
flatpak update com.tekkengreg.bigbrowser.google

# Désinstaller
flatpak uninstall com.tekkengreg.bigbrowser.google
```

```sh
latpak list --app                    # Toutes les apps installées
flatpak list --app --user             # Apps installées pour l'utilisateur
flatpak list --app --system           # Apps installées système
flatpak remotes                       # Liste des dépôts configurés
flatpak remote-ls local-repo          # Apps disponibles dans local-repo
flatpak remote-ls notion-repo         # Apps disponibles dans notion-repo