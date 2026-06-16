#!/usr/bin/env gjs
//
// Big Browser — Engine
// Moteur générique : lit un manifeste de Site (site.json) et l'affiche dans une
// WebView GTK4 / WebKitGTK 6.0, isolée et indépendante au niveau système.
//
// Le manifeste est résolu dans l'ordre :
//   1. argument CLI : `bigbrowser.js /chemin/site.json`
//   2. variable d'env `BIGBROWSER_SITE`
//   3. fichier installé `/app/share/<app-id>/site.json` (cas Flatpak)
//
// Schéma minimal du site.json :
//   { "id", "title", "url", "icon",
//     "allowed_domains": [...],
//     "permissions": { "notifications", "geolocation", "media" },
//     "inject_css": "...", "inject_js": "..." }

// --- Choix du backend Gdk AVANT tout import GTK/WebKit ---
const GLib = imports.gi.GLib;
if (!GLib.getenv('GDK_BACKEND')) {
    // Toolbox/podman : Wayland vers l'hôte casse souvent le protocole (erreur 71).
    const containerLike = GLib.getenv('TOOLBOX_PATH')
        || GLib.getenv('TOOLBOX_ENVIRONMENT')
        || GLib.file_test('/run/.containerenv', GLib.FileTest.EXISTS);
    if (containerLike)
        GLib.setenv('GDK_BACKEND', 'x11', false);
}

imports.gi.versions.Gdk = '4.0';
imports.gi.versions.Gtk = '4.0';
imports.gi.versions.WebKit = '6.0';
const { Gio, Gdk, Gtk, WebKit } = imports.gi;

// ---------------------------------------------------------------------------
// Chargement du manifeste
// ---------------------------------------------------------------------------

function readFileText(path) {
    const file = Gio.File.new_for_path(path);
    const [ok, bytes] = file.load_contents(null);
    if (!ok)
        throw new Error(`Impossible de lire ${path}`);
    return new TextDecoder('utf-8').decode(bytes);
}

function resolveManifestPath(argv) {
    if (argv.length > 0 && argv[0])
        return argv[0];

    const fromEnv = GLib.getenv('BIGBROWSER_SITE');
    if (fromEnv)
        return fromEnv;

    // Cas Flatpak : on cherche /app/share/<app-id>/site.json
    const appId = GLib.getenv('FLATPAK_ID');
    if (appId) {
        const installed = `/app/share/${appId}/site.json`;
        if (GLib.file_test(installed, GLib.FileTest.EXISTS))
            return installed;
    }
    // Dernier recours : site.json à côté du script
    return GLib.build_filenamev([GLib.get_current_dir(), 'site.json']);
}

function loadManifest(argv) {
    const path = resolveManifestPath(argv);
    if (!GLib.file_test(path, GLib.FileTest.EXISTS)) {
        printerr(`Big Browser: manifeste introuvable (${path}).`);
        printerr('Indiquez-le via argument, $BIGBROWSER_SITE, ou /app/share/<id>/site.json.');
        return null;
    }
    let manifest;
    try {
        manifest = JSON.parse(readFileText(path));
    } catch (e) {
        printerr(`Big Browser: site.json invalide (${path}) : ${e.message}`);
        return null;
    }
    if (!manifest.url) {
        printerr('Big Browser: le manifeste doit contenir au moins "url".');
        return null;
    }
    manifest.id = manifest.id || 'io.bigbrowser.UnnamedSite';
    manifest.title = manifest.title || manifest.id;
    manifest.permissions = manifest.permissions || {};
    return manifest;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function hostOf(uri) {
    try {
        return GLib.Uri.parse(uri, GLib.UriFlags.NONE).get_host() || '';
    } catch (_e) {
        return '';
    }
}

// Un domaine est autorisé s'il correspond exactement ou est un sous-domaine.
function domainMatches(host, allowed) {
    host = host.toLowerCase();
    allowed = allowed.toLowerCase();
    return host === allowed || host.endsWith('.' + allowed);
}

function buildAllowedDomains(manifest) {
    const list = Array.isArray(manifest.allowed_domains) ? manifest.allowed_domains.slice() : [];
    // Toujours autoriser au moins l'hôte de l'URL principale.
    const mainHost = hostOf(manifest.url);
    if (mainHost && !list.includes(mainHost))
        list.push(mainHost);
    return list;
}

// ---------------------------------------------------------------------------
// Persistance de la géométrie de la fenêtre
// ---------------------------------------------------------------------------

function stateFilePath(appId) {
    return GLib.build_filenamev([GLib.get_user_data_dir(), 'bigbrowser', appId, 'window-state.json']);
}

function loadWindowState(appId) {
    const path = stateFilePath(appId);
    if (!GLib.file_test(path, GLib.FileTest.EXISTS))
        return { width: 1024, height: 768 };
    try {
        return JSON.parse(readFileText(path));
    } catch (_e) {
        return { width: 1024, height: 768 };
    }
}

function saveWindowState(appId, width, height) {
    const path = stateFilePath(appId);
    try {
        const dir = Gio.File.new_for_path(path).get_parent();
        dir.make_directory_with_parents(null);
    } catch (_e) { /* existe déjà */ }
    try {
        const file = Gio.File.new_for_path(path);
        file.replace_contents(
            JSON.stringify({ width, height }), null, false,
            Gio.FileCreateFlags.REPLACE_DESTINATION, null);
    } catch (e) {
        printerr(`Big Browser: échec sauvegarde géométrie : ${e.message}`);
    }
}

// ---------------------------------------------------------------------------
// Construction de la WebView
// ---------------------------------------------------------------------------

function makeWebView(manifest) {
    // Session réseau isolée par app-id : cookies/stockage propres au Site.
    const base = GLib.build_filenamev([GLib.get_user_data_dir(), 'bigbrowser', manifest.id]);
    const cache = GLib.build_filenamev([GLib.get_user_cache_dir(), 'bigbrowser', manifest.id]);
    const session = WebKit.NetworkSession.new(base, cache);

    // Politique TLS. Par défaut on REFUSE les certificats invalides (sécurité).
    // `ignore_tls_errors` n'est qu'une aide au diagnostic, à ne PAS utiliser en prod.
    if (manifest.ignore_tls_errors) {
        session.set_tls_errors_policy(WebKit.TLSErrorsPolicy.IGNORE);
        printerr('Big Browser: ⚠️  ignore_tls_errors actif — validation TLS désactivée.');
    } else {
        session.set_tls_errors_policy(WebKit.TLSErrorsPolicy.FAIL);
    }

    // Persistance des cookies.
    const cookies = session.get_cookie_manager();
    const cookieFile = GLib.build_filenamev([base, 'cookies.sqlite']);
    cookies.set_persistent_storage(cookieFile, WebKit.CookiePersistentStorage.SQLITE);

    // Téléchargements → dossier Téléchargements, sans dialogue.
    setupDownloads(session);

    // Injection CSS/JS optionnelle.
    const ucm = new WebKit.UserContentManager();
    if (manifest.inject_css) {
        ucm.add_style_sheet(new WebKit.UserStyleSheet(
            manifest.inject_css,
            WebKit.UserContentInjectedFrames.ALL_FRAMES,
            WebKit.UserStyleLevel.USER, null, null));
    }
    if (manifest.inject_js) {
        ucm.add_script(new WebKit.UserScript(
            manifest.inject_js,
            WebKit.UserContentInjectedFrames.TOP_FRAME,
            WebKit.UserScriptInjectionTime.END, null, null));
    }

    const webView = new WebKit.WebView({
        network_session: session,
        user_content_manager: ucm,
    });

    return webView;
}

// Ouvre une URL hors périmètre dans le navigateur système.
function openExternal(parentWindow, uri) {
    try {
        const launcher = new Gtk.UriLauncher({ uri });
        launcher.launch(parentWindow, null, (l, res) => {
            try { l.launch_finish(res); }
            catch (e) { printerr(`Big Browser: lien externe non ouvert : ${e.message}`); }
        });
    } catch (e) {
        printerr(`Big Browser: UriLauncher indisponible : ${e.message}`);
    }
}

// ---------------------------------------------------------------------------
// Téléchargements : enregistrés dans le dossier Téléchargements (XDG), sans
// boîte de dialogue. En Flatpak, l'écriture passe par le portail de fichiers.
// ---------------------------------------------------------------------------

function downloadsDir() {
    return GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD)
        || GLib.get_home_dir();
}

// Évite d'écraser un fichier existant : « doc.pdf » → « doc (1).pdf ».
function uniqueDestination(dir, filename) {
    let candidate = GLib.build_filenamev([dir, filename]);
    if (!GLib.file_test(candidate, GLib.FileTest.EXISTS))
        return candidate;
    const dot = filename.lastIndexOf('.');
    const stem = dot > 0 ? filename.slice(0, dot) : filename;
    const ext = dot > 0 ? filename.slice(dot) : '';
    let i = 1;
    do {
        candidate = GLib.build_filenamev([dir, `${stem} (${i})${ext}`]);
        i++;
    } while (GLib.file_test(candidate, GLib.FileTest.EXISTS));
    return candidate;
}

function setupDownloads(session) {
    const dir = downloadsDir();
    session.connect('download-started', (_s, download) => {
        download.connect('decide-destination', (d, suggested) => {
            d.set_destination(uniqueDestination(dir, suggested || 'download'));
            return true;
        });
        download.connect('finished', () => {
            printerr(`Big Browser: téléchargement terminé → ${download.get_destination()}`);
        });
        download.connect('failed', (_d, error) => {
            printerr(`Big Browser: téléchargement échoué : ${error.message}`);
        });
    });
}

// ---------------------------------------------------------------------------
// Menu contextuel minimal : on garde l'édition (copier/coller…), les liens et
// téléchargements, mais on retire ce qui n'a pas de sens dans une app mono-site
// (ouverture en nouvelle fenêtre — déjà bloquée — et l'inspecteur).
// ---------------------------------------------------------------------------

const HIDDEN_CONTEXT_ACTIONS = [
    'OPEN_LINK_IN_NEW_WINDOW',
    'OPEN_IMAGE_IN_NEW_WINDOW',
    'OPEN_FRAME_IN_NEW_WINDOW',
    'OPEN_MEDIA_IN_NEW_WINDOW',
    'INSPECT_ELEMENT',
];

function hiddenContextActions() {
    const set = new Set();
    for (const key of HIDDEN_CONTEXT_ACTIONS) {
        const value = WebKit.ContextMenuAction[key];
        if (value !== undefined)
            set.add(value);
    }
    return set;
}

// ---------------------------------------------------------------------------
// Application
// ---------------------------------------------------------------------------

function main(argv) {
    const manifest = loadManifest(argv);
    if (!manifest)
        return 1;

    const allowed = buildAllowedDomains(manifest);
    const app = new Gtk.Application({
        application_id: manifest.id,
        flags: Gio.ApplicationFlags.FLAGS_NONE,
    });

    app.connect('activate', () => {
        const state = loadWindowState(manifest.id);
        const win = new Gtk.ApplicationWindow({
            application: app,
            title: manifest.title,
            default_width: state.width,
            default_height: state.height,
        });

        const webView = makeWebView(manifest);
        win.set_child(webView);

        // Titre dynamique = <title> de la page (préfixé du nom du Site).
        webView.connect('notify::title', () => {
            const t = webView.title;
            win.title = t ? `${t} — ${manifest.title}` : manifest.title;
        });

        // Diagnostic TLS : si un certificat est refusé, on logge la cause exacte.
        // Cause la plus fréquente d'un refus sur un site valide : `glib-networking`
        // absent → aucune base de certificats → tout est rejeté.
        webView.connect('load-failed-with-tls-errors', (_v, uri, _cert, errors) => {
            const flags = [];
            if (errors & 0x01) flags.push('UNKNOWN_CA');
            if (errors & 0x02) flags.push('BAD_IDENTITY');
            if (errors & 0x04) flags.push('NOT_ACTIVATED');
            if (errors & 0x08) flags.push('EXPIRED');
            if (errors & 0x10) flags.push('REVOKED');
            if (errors & 0x20) flags.push('INSECURE');
            if (errors & 0x40) flags.push('GENERIC_ERROR');
            printerr(`Big Browser: TLS refusé pour ${uri} — ${flags.join(', ') || 'inconnu'}.`);
            printerr('  → "UNKNOWN_CA" sur un site valide = installez `glib-networking` + `ca-certificates`.');
            return false; // laisse WebKit afficher sa page d'erreur
        });

        // Politique de navigation : tout ce qui sort du périmètre part dans
        // le navigateur système. Le Site reste cantonné à ses domaines.
        webView.connect('decide-policy', (_v, decision, type) => {
            if (type !== WebKit.PolicyDecisionType.NAVIGATION_ACTION &&
                type !== WebKit.PolicyDecisionType.NEW_WINDOW_ACTION)
                return false;

            const action = decision.get_navigation_action();
            const uri = action.get_request().get_uri();
            const host = hostOf(uri);
            const internal = host && allowed.some(d => domainMatches(host, d));

            if (type === WebKit.PolicyDecisionType.NEW_WINDOW_ACTION) {
                // Pas de pop-up : on ouvre dehors et on refuse la nouvelle fenêtre.
                if (!internal)
                    openExternal(win, uri);
                decision.ignore();
                return true;
            }

            if (!internal) {
                openExternal(win, uri);
                decision.ignore();
                return true;
            }
            return false;
        });

        // Permissions, pilotées par le manifeste (refus par défaut).
        webView.connect('permission-request', (_v, request) => {
            const p = manifest.permissions;
            let grant = false;
            if (request instanceof WebKit.NotificationPermissionRequest)
                grant = !!p.notifications;
            else if (request instanceof WebKit.GeolocationPermissionRequest)
                grant = !!p.geolocation;
            else if (request instanceof WebKit.UserMediaPermissionRequest)
                grant = !!p.media;

            if (grant) request.allow();
            else request.deny();
            return true;
        });

        // Menu contextuel épuré : on retire les entrées sans objet pour un Site.
        const hidden = hiddenContextActions();
        webView.connect('context-menu', (_v, menu, _hit) => {
            for (const item of menu.get_items()) {
                if (hidden.has(item.get_stock_action()))
                    menu.remove(item);
            }
            return false; // false = afficher le menu (épuré)
        });

        // Raccourcis : zoom (Ctrl +/-/0) et rechargement (F5, Ctrl+R).
        const keys = new Gtk.EventControllerKey();
        keys.connect('key-pressed', (_c, keyval, _code, mods) => {
            const ctrl = (mods & Gdk.ModifierType.CONTROL_MASK) !== 0;
            if (ctrl && (keyval === Gdk.KEY_plus || keyval === Gdk.KEY_equal)) {
                webView.zoom_level += 0.1; return true;
            }
            if (ctrl && keyval === Gdk.KEY_minus) {
                webView.zoom_level = Math.max(0.3, webView.zoom_level - 0.1); return true;
            }
            if (ctrl && keyval === Gdk.KEY_0) {
                webView.zoom_level = 1.0; return true;
            }
            if (keyval === Gdk.KEY_F5 || (ctrl && keyval === Gdk.KEY_r)) {
                webView.reload(); return true;
            }
            return false;
        });
        win.add_controller(keys);

        // Sauvegarde de la géométrie à la fermeture.
        win.connect('close-request', () => {
            saveWindowState(manifest.id, win.default_width, win.default_height);
            return false;
        });

        webView.load_uri(manifest.url);
        win.present();
    });

    return app.run([]);
}

imports.system.exit(main(ARGV));
