#!/usr/bin/env gjs

// Avant tout import Gtk/WebKit : le backend Gdk est choisi au premier chargement.
const GLib = imports.gi.GLib;
if (!GLib.getenv('GDK_BACKEND')) {
    // Toolbox/podman : Wayland vers l’hôte casse souvent le protocole (erreur 71).
    let containerLike = GLib.getenv('TOOLBOX_PATH')
        || GLib.getenv('TOOLBOX_ENVIRONMENT')
        || GLib.file_test('/run/.containerenv', GLib.FileTest.EXISTS);
    if (containerLike)
        GLib.setenv('GDK_BACKEND', 'x11', false);
}

imports.gi.versions.WebKit2 = '4.1';
const { Gtk, WebKit2, Gdk } = imports.gi;

Gtk.init(null);

let win = new Gtk.Window({
    type: Gtk.WindowType.TOPLEVEL,
    default_width: 1024,
    default_height: 768,
    title: "WikiSSB"
});
win.connect('destroy', () => Gtk.main_quit());

// Contexte dédié avec répertoires de données (pas de set_* sur le contexte par défaut via GI)
let storage_path = GLib.get_user_data_dir() + "/wikissb";
let context = WebKit2.WebContext.new_with_website_data_manager(
    new WebKit2.WebsiteDataManager({
        'base-data-directory': storage_path,
        'local-storage-directory': storage_path + "/localstorage",
    })
);

let webView = new WebKit2.WebView({ web_context: context });
win.add(webView);

// Gérer les redirections externes
webView.connect('decide-policy', (view, decision, decision_type) => {
    if (decision_type === WebKit2.PolicyDecisionType.NAVIGATION_ACTION) {
        let uri = decision.get_navigation_action().get_request().get_uri();
        if (!uri.startsWith("https://fr.wikipedia.org")) {
            try {
                Gtk.show_uri(null, uri, Gdk.CURRENT_TIME);
            } catch (e) {
                print("Erreur lors de l'ouverture du lien externe: " + e);
            }
            decision.ignore();
            return true;
        }
    }
    return false;
});

// Charger Wikipedia
webView.load_uri("https://fr.wikipedia.org");

// Afficher la fenêtre
win.show_all();
Gtk.main();
