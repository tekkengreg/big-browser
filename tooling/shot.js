#!/usr/bin/env gjs
//
// Big Browser — capture d'écran d'un Site (outil de dev)
// Charge une URL dans une WebView GTK4 / WebKitGTK 6.0 et enregistre un PNG
// destiné au bloc <screenshots> de l'AppStream (fiche GNOME Logiciels).
//
// Usage :
//   gjs tooling/shot.js <url> <sortie.png> [largeur] [hauteur] [attente_ms]
//
// Comme `tooling/icons.py`, c'est un outil de dev : il n'est PAS appelé par la
// CI (qui n'a pas d'affichage), et ce sont les PNG commités qui sont publiés.
// La fenêtre est brièvement visible le temps de la capture : WebKit ne rend
// rien tant que la WebView n'est pas mappée.

// --- Choix du backend Gdk AVANT tout import GTK/WebKit (cf. engine) ---
const GLib = imports.gi.GLib;
if (!GLib.getenv('GDK_BACKEND')) {
    const containerLike = GLib.getenv('TOOLBOX_PATH')
        || GLib.getenv('TOOLBOX_ENVIRONMENT')
        || GLib.file_test('/run/.containerenv', GLib.FileTest.EXISTS);
    if (containerLike)
        GLib.setenv('GDK_BACKEND', 'x11', false);
}
if (GLib.getenv('WEBKIT_DISABLE_DMABUF_RENDERER') === null &&
    GLib.file_test('/proc/driver/nvidia/version', GLib.FileTest.EXISTS))
    GLib.setenv('WEBKIT_DISABLE_DMABUF_RENDERER', '1', false);

imports.gi.versions.Gdk = '4.0';
imports.gi.versions.Gtk = '4.0';
imports.gi.versions.WebKit = '6.0';
const { Gio, Gtk, WebKit } = imports.gi;

// Format par défaut : le ratio des vignettes Flathub (752×528 ≈ 16/11), en
// assez grand pour rester net dans le carrousel de GNOME Logiciels.
const DEFAULT_WIDTH = 1504;
const DEFAULT_HEIGHT = 1056;
// Délai après `load-changed: FINISHED` : les webapps continuent de peupler le
// DOM (polices, lazy-loading) bien après la fin du chargement réseau.
const DEFAULT_SETTLE_MS = 4000;

function usage(message) {
    if (message)
        printerr(`shot.js: ${message}`);
    printerr('usage: gjs tooling/shot.js <url> <sortie.png> ' +
             '[largeur] [hauteur] [attente_ms]');
    return 2;
}

function main(argv) {
    const [url, output] = argv;
    if (!url || !output)
        return usage('url et fichier de sortie requis');
    if (!url.startsWith('https://') && !url.startsWith('http://'))
        return usage(`url invalide : ${url}`);

    const width = parseInt(argv[2], 10) || DEFAULT_WIDTH;
    const height = parseInt(argv[3], 10) || DEFAULT_HEIGHT;
    const settleMs = parseInt(argv[4], 10) || DEFAULT_SETTLE_MS;

    const app = new Gtk.Application({ application_id: 'com.tekkengreg.bigbrowser.Shot' });
    let status = 1;

    app.connect('activate', () => {
        // Session éphémère : pas de cookie ni de cache traînant d'une capture
        // à l'autre, donc une page toujours dans son état « premier visiteur ».
        const session = WebKit.NetworkSession.new_ephemeral();
        const webView = new WebKit.WebView({ network_session: session });
        const win = new Gtk.ApplicationWindow({
            application: app,
            title: 'Big Browser — capture',
            default_width: width,
            default_height: height,
            // Sans décoration, la WebView occupe toute la fenêtre : la barre de
            // titre CSD rognerait sinon une quarantaine de pixels en hauteur.
            decorated: false,
        });
        win.set_child(webView);

        const snapshot = () => {
            webView.get_snapshot(
                WebKit.SnapshotRegion.VISIBLE,
                WebKit.SnapshotOptions.NONE,
                null,
                (view, result) => {
                    try {
                        const texture = view.get_snapshot_finish(result);
                        const file = Gio.File.new_for_commandline_arg(output);
                        const parent = file.get_parent();
                        if (parent && !parent.query_exists(null))
                            parent.make_directory_with_parents(null);
                        texture.save_to_png(file.get_path());
                        print(`✓ ${file.get_path()} (${texture.get_width()}×${texture.get_height()})`);
                        status = 0;
                    } catch (e) {
                        printerr(`shot.js: capture échouée : ${e.message}`);
                    }
                    app.quit();
                });
        };

        webView.connect('load-failed', (view, event, failingUri, error) => {
            printerr(`shot.js: chargement échoué (${failingUri}) : ${error.message}`);
            app.quit();
            return true;
        });
        webView.connect('load-changed', (view, event) => {
            if (event === WebKit.LoadEvent.FINISHED)
                GLib.timeout_add(GLib.PRIORITY_DEFAULT, settleMs, () => {
                    snapshot();
                    return GLib.SOURCE_REMOVE;
                });
        });

        // La taille de fenêtre est en pixels logiques, mais WebKit rend (et
        // snapshote) en pixels physiques : sur un écran HiDPI une fenêtre de
        // 1504 px donne un PNG de 3008 px. On divise donc la cible par le
        // facteur d'échelle, connu seulement une fois la fenêtre réalisée,
        // pour que le PNG sorte à la taille demandée sur n'importe quel écran.
        win.connect('map', () => {
            const scale = win.get_scale_factor() || 1;
            if (scale !== 1)
                win.set_default_size(Math.round(width / scale),
                                     Math.round(height / scale));
            webView.load_uri(url);
        });
        win.present();
    });

    app.run([]);
    return status;
}

imports.system.exit(main(ARGV));
