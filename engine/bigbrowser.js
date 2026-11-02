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
//     "languages": [...],
//     "permissions": { "notifications", "geolocation", "media" },
//     "inject_css": "...", "inject_js": "..." }
//
// `url` peut être paramétrée par la langue (`https://{lang}.wikipedia.org`) :
// voir resolveUrl(). Langue et thème suivent le système par défaut et sont
// surchargeables depuis le menu de la fenêtre (préférences persistées par Site).

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

// --- Contournement NVIDIA : renderer DMA-BUF de WebKitGTK défectueux sur le
// pilote propriétaire (contenu figé au redimensionnement, textures blanches —
// https://bugs.webkit.org/show_bug.cgi?id=262607). /proc/driver/nvidia est
// global au noyau, donc visible aussi depuis le sandbox Flatpak. Faux positif
// possible en multi-GPU si la session tourne sur l'autre carte : on perd alors
// un peu d'accélération, mais rien ne casse. Exporter la variable soi-même
// (même vide) garde la main : setenv n'écrase pas.
if (GLib.getenv('WEBKIT_DISABLE_DMABUF_RENDERER') === null &&
    GLib.file_test('/proc/driver/nvidia/version', GLib.FileTest.EXISTS)) {
    GLib.setenv('WEBKIT_DISABLE_DMABUF_RENDERER', '1', false);
    printerr('Big Browser: pilote NVIDIA détecté — renderer DMA-BUF WebKit désactivé.');
}

imports.gi.versions.Gdk = '4.0';
imports.gi.versions.Gtk = '4.0';
imports.gi.versions.Adw = '1';
imports.gi.versions.WebKit = '6.0';
const { Gio, Gdk, Gtk, Adw, WebKit } = imports.gi;

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
    manifest.id = manifest.id || 'com.tekkengreg.bigbrowser.UnnamedSite';
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

// Seules les URLs web ont un sens dans le navigateur système (jamais
// about:blank, blob:, data:… — le portail n'a aucun handler pour elles).
function isWebUri(uri) {
    return /^https?:/i.test(uri || '');
}

// L'hôte de l'URL d'accueil *résolue* est toujours autorisé : avec une `url`
// paramétrée par la langue, il change au fil des surcharges, d'où le recalcul.
function buildAllowedDomains(manifest, homeUrl) {
    const list = Array.isArray(manifest.allowed_domains) ? manifest.allowed_domains.slice() : [];
    const mainHost = hostOf(homeUrl);
    if (mainHost && !list.includes(mainHost))
        list.push(mainHost);
    return list;
}

// ---------------------------------------------------------------------------
// Langues
//
// Un Site n'est pas dédié à une langue : par défaut il suit celle du système
// (Accept-Language + navigator.language), surchargeable depuis le menu. Le jeu
// de langues proposé vient du `languages` du manifeste, sinon de la liste
// ci-dessous.
// ---------------------------------------------------------------------------

const LANGUAGE_NAMES = {
    ar: 'العربية',
    cs: 'Čeština',
    de: 'Deutsch',
    en: 'English',
    es: 'Español',
    fr: 'Français',
    hi: 'हिन्दी',
    it: 'Italiano',
    ja: '日本語',
    ko: '한국어',
    nl: 'Nederlands',
    pl: 'Polski',
    pt: 'Português',
    ru: 'Русский',
    sv: 'Svenska',
    tr: 'Türkçe',
    uk: 'Українська',
    zh: '中文',
};

// Sous-tag principal d'une étiquette BCP 47 : « fr-FR » → « fr ».
function primarySubtag(tag) {
    return String(tag || '').split('-')[0];
}

// Nom POSIX d'une locale → étiquette BCP 47 : « fr_FR.UTF-8@euro » → « fr-FR ».
// La locale neutre (C/POSIX) ne désigne aucune langue : on la laisse tomber.
function toBcp47(name) {
    const base = String(name || '').split('.')[0].split('@')[0];
    if (!base || base === 'C' || base === 'POSIX')
        return '';
    return base.replace(/_/g, '-');
}

// Langues du système, dans l'ordre de préférence ($LANGUAGE, $LC_ALL, $LANG…).
function systemLanguages() {
    const out = [];
    for (const name of GLib.get_language_names()) {
        const tag = toBcp47(name);
        if (tag && !out.includes(tag))
            out.push(tag);
    }
    return out.length ? out : ['en'];
}

// Liste Accept-Language effective : la surcharge d'abord (étiquette complète
// puis forme courte), le système ensuite — un Site qui ne parle pas la langue
// demandée retombe ainsi sur celle du bureau plutôt que sur son défaut à lui.
function preferredLanguages(override) {
    const list = [];
    const push = (tag) => {
        if (tag && !list.includes(tag))
            list.push(tag);
    };
    push(override);
    push(primarySubtag(override));
    for (const tag of systemLanguages())
        push(tag);
    return list;
}

// Libellé d'une langue, en endonyme quand on le connaît. Une étiquette
// régionale garde son code en clair : « Português (pt-BR) ».
function languageLabel(code) {
    const name = LANGUAGE_NAMES[code];
    if (name)
        return name;
    const generic = LANGUAGE_NAMES[primarySubtag(code)];
    return generic ? `${generic} (${code})` : code;
}

// Langues proposées au menu, triées par libellé.
function offeredLanguages(manifest) {
    const codes = Array.isArray(manifest.languages) && manifest.languages.length
        ? manifest.languages.map(String)
        : Object.keys(LANGUAGE_NAMES);
    return [...new Set(codes)].sort((a, b) =>
        languageLabel(a).localeCompare(languageLabel(b)));
}

// L'URL d'accueil peut être paramétrée par la langue : `{lang}` reçoit le
// sous-tag principal (fr), `{locale}` l'étiquette complète (fr-FR). C'est ce
// qui permet à un Site comme Wikipédia de suivre la langue du système sans
// être figé sur une édition : `https://{lang}.wikipedia.org`.
function resolveUrl(template, languages) {
    const locale = languages[0] || 'en';
    return String(template)
        .replace(/\{locale\}/g, locale)
        .replace(/\{lang\}/g, primarySubtag(locale));
}

// ---------------------------------------------------------------------------
// Thème
//
// `Adw.StyleManager` pilote d'un coup le thème GTK *et* le `prefers-color-scheme`
// vu par la page : WebKitGTK suit la clarté du thème GTK. DEFAULT = réglage du
// bureau (portail org.freedesktop.appearance).
// ---------------------------------------------------------------------------

const COLOR_SCHEMES = {
    system: Adw.ColorScheme.DEFAULT,
    light: Adw.ColorScheme.FORCE_LIGHT,
    dark: Adw.ColorScheme.FORCE_DARK,
};

const COLOR_SCHEME_LABELS = {
    system: 'Système',
    light: 'Clair',
    dark: 'Sombre',
};

// ---------------------------------------------------------------------------
// Persistance : géométrie de la fenêtre et préférences du Site
// ---------------------------------------------------------------------------

function stateDir(appId) {
    return GLib.build_filenamev([GLib.get_user_data_dir(), 'bigbrowser', appId]);
}

function readJson(path, fallback) {
    if (!GLib.file_test(path, GLib.FileTest.EXISTS))
        return fallback;
    try {
        return Object.assign({}, fallback, JSON.parse(readFileText(path)));
    } catch (_e) {
        return fallback;
    }
}

function writeJson(path, data, what) {
    try {
        const dir = Gio.File.new_for_path(path).get_parent();
        try { dir.make_directory_with_parents(null); }
        catch (_e) { /* existe déjà */ }
        Gio.File.new_for_path(path).replace_contents(
            JSON.stringify(data), null, false,
            Gio.FileCreateFlags.REPLACE_DESTINATION, null);
    } catch (e) {
        printerr(`Big Browser: échec sauvegarde ${what} : ${e.message}`);
    }
}

function loadWindowState(appId) {
    return readJson(GLib.build_filenamev([stateDir(appId), 'window-state.json']),
                    { width: 1024, height: 768 });
}

function saveWindowState(appId, width, height) {
    writeJson(GLib.build_filenamev([stateDir(appId), 'window-state.json']),
              { width, height }, 'géométrie');
}

// Préférences de l'utilisateur : chaîne vide = « suivre le système ».
function loadPrefs(appId) {
    const prefs = readJson(GLib.build_filenamev([stateDir(appId), 'prefs.json']),
                           { language: '', color_scheme: 'system' });
    if (!(prefs.color_scheme in COLOR_SCHEMES))
        prefs.color_scheme = 'system';
    prefs.language = String(prefs.language || '');
    return prefs;
}

function savePrefs(appId, prefs) {
    writeJson(GLib.build_filenamev([stateDir(appId), 'prefs.json']),
              prefs, 'préférences');
}

// ---------------------------------------------------------------------------
// Construction de la WebView
// ---------------------------------------------------------------------------

function makeWebView(manifest, context) {
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
        web_context: context,
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
// Menu principal : langue et thème, en groupes de boutons radio. Les deux
// réglages ont une entrée « système » en tête, qui est l'état par défaut.
// ---------------------------------------------------------------------------

function radioItem(label, action, target) {
    const item = Gio.MenuItem.new(label, null);
    item.set_action_and_target_value(action, GLib.Variant.new_string(target));
    return item;
}

function buildMainMenu(manifest) {
    const languages = new Gio.Menu();
    const systemSection = new Gio.Menu();
    // Sous-tag seul dans le libellé : « Deutsch », pas « Deutsch (de-DE) ».
    systemSection.append_item(radioItem(
        `Langue du système (${languageLabel(primarySubtag(systemLanguages()[0]))})`,
        'win.language', ''));
    languages.append_section(null, systemSection);

    const choices = new Gio.Menu();
    for (const code of offeredLanguages(manifest))
        choices.append_item(radioItem(languageLabel(code), 'win.language', code));
    languages.append_section(null, choices);

    const theme = new Gio.Menu();
    for (const [key, label] of Object.entries(COLOR_SCHEME_LABELS))
        theme.append_item(radioItem(label, 'win.color-scheme', key));

    const menu = new Gio.Menu();
    menu.append_submenu('_Langue', languages);
    menu.append_submenu('_Thème', theme);
    return menu;
}

// ---------------------------------------------------------------------------
// Application
// ---------------------------------------------------------------------------

function main(argv) {
    const manifest = loadManifest(argv);
    if (!manifest)
        return 1;

    const prefs = loadPrefs(manifest.id);
    const app = new Adw.Application({
        application_id: manifest.id,
        flags: Gio.ApplicationFlags.FLAGS_NONE,
    });

    // Contexte web propre au Site : c'est lui qui porte la liste Accept-Language.
    const context = new WebKit.WebContext();

    // Langue et URL d'accueil effectives. `languages`/`home`/`allowed` sont
    // recalculés à chaque changement de langue (l'hôte d'accueil peut changer).
    let languages = preferredLanguages(prefs.language);
    let home = resolveUrl(manifest.url, languages);
    let allowed = buildAllowedDomains(manifest, home);
    context.set_preferred_languages(languages);

    app.connect('activate', () => {
        // Après l'init GTK (donc pas avant `run`) : le gestionnaire de style a
        // besoin du display pour suivre le réglage du bureau.
        Adw.StyleManager.get_default().set_color_scheme(COLOR_SCHEMES[prefs.color_scheme]);

        const state = loadWindowState(manifest.id);
        const win = new Adw.ApplicationWindow({
            application: app,
            title: manifest.title,
            default_width: state.width,
            default_height: state.height,
        });

        const webView = makeWebView(manifest, context);

        // --- Barre d'en-tête : retour de navigation + menu principal ---
        const back = new Gtk.Button({
            icon_name: 'go-previous-symbolic',
            tooltip_text: 'Revenir à la page précédente',
            sensitive: false,
        });
        back.connect('clicked', () => webView.go_back());

        const menuButton = new Gtk.MenuButton({
            icon_name: 'open-menu-symbolic',
            tooltip_text: 'Menu principal',
            primary: true,
            menu_model: buildMainMenu(manifest),
        });

        // Titre de la page en ligne 1, nom du Site en sous-titre : le même
        // texte dans les deux donnerait « Wikipédia — Wikipédia ».
        const windowTitle = new Adw.WindowTitle({ title: manifest.title });
        const header = new Adw.HeaderBar({ title_widget: windowTitle });
        header.pack_start(back);
        header.pack_end(menuButton);

        const layout = new Adw.ToolbarView({ content: webView });
        layout.add_top_bar(header);
        win.set_content(layout);

        // Titre dynamique = <title> de la page (préfixé du nom du Site).
        webView.connect('notify::title', () => {
            const t = webView.title;
            win.title = t ? `${t} — ${manifest.title}` : manifest.title;
            windowTitle.title = t || manifest.title;
            windowTitle.subtitle = t ? manifest.title : '';
        });

        // Le bouton retour suit l'historique de la WebView.
        const syncBack = () => { back.sensitive = webView.can_go_back(); };
        webView.get_back_forward_list().connect('changed', syncBack);
        webView.connect('load-changed', syncBack);

        // --- Actions du menu ---------------------------------------------

        // Changement de langue : nouvelle liste Accept-Language, puis rechargement.
        // Si l'URL d'accueil dépend de la langue (`{lang}`), l'hôte change : on
        // repart de l'accueil plutôt que de recharger une page d'une autre édition.
        const languageAction = Gio.SimpleAction.new_stateful(
            'language', GLib.VariantType.new('s'),
            GLib.Variant.new_string(prefs.language));
        languageAction.connect('activate', (action, target) => {
            const code = target.unpack();
            action.set_state(GLib.Variant.new_string(code));
            prefs.language = code;
            savePrefs(manifest.id, prefs);

            languages = preferredLanguages(code);
            context.set_preferred_languages(languages);
            const newHome = resolveUrl(manifest.url, languages);
            const moved = newHome !== home;
            home = newHome;
            allowed = buildAllowedDomains(manifest, home);
            if (moved)
                webView.load_uri(home);
            else
                webView.reload();
        });
        win.add_action(languageAction);

        const schemeAction = Gio.SimpleAction.new_stateful(
            'color-scheme', GLib.VariantType.new('s'),
            GLib.Variant.new_string(prefs.color_scheme));
        schemeAction.connect('activate', (action, target) => {
            const key = target.unpack();
            if (!(key in COLOR_SCHEMES))
                return;
            action.set_state(GLib.Variant.new_string(key));
            prefs.color_scheme = key;
            savePrefs(manifest.id, prefs);
            Adw.StyleManager.get_default().set_color_scheme(COLOR_SCHEMES[key]);
        });
        win.add_action(schemeAction);

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

        // Politique de navigation. Confinement au périmètre du Site :
        //  - un CLIC sur un lien hors domaine part dans le navigateur système ;
        //  - redirections, formulaires et iframes (captcha, SSO, paiement…)
        //    restent dans la WebView : les envoyer dehors casse ces flux ;
        //  - pas de pop-up : les internes se chargent dans la même fenêtre,
        //    les externes partent dehors, le reste (about:blank…) est refusé.
        webView.connect('decide-policy', (_v, decision, type) => {
            if (type !== WebKit.PolicyDecisionType.NAVIGATION_ACTION &&
                type !== WebKit.PolicyDecisionType.NEW_WINDOW_ACTION)
                return false;

            const action = decision.get_navigation_action();
            const uri = action.get_request().get_uri();
            const host = hostOf(uri);
            const internal = host && allowed.some(d => domainMatches(host, d));

            if (type === WebKit.PolicyDecisionType.NEW_WINDOW_ACTION) {
                if (internal)
                    webView.load_uri(uri);
                else if (isWebUri(uri))
                    openExternal(win, uri);
                decision.ignore();
                return true;
            }

            if (!internal && isWebUri(uri) &&
                action.get_navigation_type() === WebKit.NavigationType.LINK_CLICKED &&
                !action.is_redirect()) {
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

        // Raccourcis : retour (Alt+←, touche « Précédent » du clavier/souris),
        // zoom (Ctrl +/-/0) et rechargement (F5, Ctrl+R).
        const keys = new Gtk.EventControllerKey();
        keys.connect('key-pressed', (_c, keyval, _code, mods) => {
            const ctrl = (mods & Gdk.ModifierType.CONTROL_MASK) !== 0;
            const alt = (mods & Gdk.ModifierType.ALT_MASK) !== 0;
            if ((alt && keyval === Gdk.KEY_Left) || keyval === Gdk.KEY_Back) {
                if (webView.can_go_back()) webView.go_back();
                return true;
            }
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

        webView.load_uri(home);
        win.present();
    });

    return app.run([]);
}

imports.system.exit(main(ARGV));
