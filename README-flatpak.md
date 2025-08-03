# Packaging BigBrowser en Flatpak

Ce guide explique comment packager l'exécutable BigBrowser (créé avec Deno) en tant qu'application Flatpak.

## Prérequis

- Flatpak et flatpak-builder installés
- L'exécutable `bigbrowser` compilé avec Deno
- Une icône `icons/bigbrowser.png` (déjà créée)

## Structure des fichiers

```
├── bigbrowser                                    # Exécutable Deno
├── manifests/com.tekkengreg.bigbrowser.yml      # Manifeste Flatpak principal
├── icons/bigbrowser.png                         # Icône de l'application
├── build-flatpak.sh                            # Script de construction
├── export-flatpak.sh                           # Script d'export
└── README-flatpak.md                           # Ce fichier
```

## Construction du Flatpak

### 1. Construction et installation locale

```bash
./build-flatpak.sh
```

Ce script :
- Vérifie la présence de l'exécutable et de l'icône
- Construit le Flatpak avec flatpak-builder
- L'installe localement pour les tests

### 2. Test de l'application

```bash
flatpak run com.tekkengreg.bigbrowser
```

Ou avec une URL spécifique :
```bash
flatpak run com.tekkengreg.bigbrowser https://www.example.com
```

### 3. Export vers un fichier .flatpak

```bash
./export-flatpak.sh
```

Ce script crée un fichier `bigbrowser.flatpak` qui peut être distribué et installé sur d'autres systèmes.

## Installation sur un autre système

```bash
flatpak install --user bigbrowser.flatpak
```

## Désinstallation

```bash
flatpak uninstall com.tekkengreg.bigbrowser
```

## Structure du manifeste

Le manifeste `com.tekkengreg.bigbrowser.yml` :
- Utilise le runtime Freedesktop 23.08
- Configure les permissions nécessaires (réseau, audio, vidéo, système de fichiers)
- Installe l'exécutable Deno directement
- Crée un fichier .desktop pour l'intégration avec le système

## Permissions Flatpak

L'application demande les permissions suivantes :
- Accès réseau (pour naviguer sur le web)
- Accès audio et vidéo (pour le contenu multimédia)
- Accès aux dossiers de téléchargement, documents, images et vidéos
- Intégration avec le système (notifications, portails)

## Dépannage

Si la construction échoue :
1. Vérifiez que flatpak-builder est installé
2. Assurez-vous que le runtime Freedesktop 23.08 est disponible :
   ```bash
   flatpak install flathub org.freedesktop.Platform//23.08
   flatpak install flathub org.freedesktop.Sdk//23.08
   ```
3. Vérifiez les permissions de l'exécutable `bigbrowser` 