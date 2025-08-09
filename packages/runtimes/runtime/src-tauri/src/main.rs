// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::Builder;
use tauri::webview::WebviewWindowBuilder;


fn main() {
    let args: Vec<String> = std::env::args().collect();
    let url = args.get(1).unwrap_or(&"https://www.wikipedia.org".to_string()).to_string();

    Builder::default()
        .setup( move|app| {
            let _webview_window = WebviewWindowBuilder::new(
                app, 
                "label", 
                tauri::WebviewUrl::External(url.parse().unwrap())
            )
            .title("BigBrowser")
            .inner_size(720.0, 1280.0)
            .build()?;
            // webview_window.show();
            // webview_window.set_focus();




            // app.manage(url);
            // let main_window = app.get_webview_window("main").unwrap();
            // main_window.eval(format!("window.location.href = '{}';", &url).as_str());
            // main_window.set_title("BigBrowser");
            // main_window.show();
            // main_window.set_focus();
            // let window = WindowBuilder::new(
            //     app,
            //     "main",
            //     tauri::WindowUrl::External(url.parse().unwrap())
            // )
            // .title("BigBrowser")
            // .inner_size(720.0, 1280.0)
            // .build()?;
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
