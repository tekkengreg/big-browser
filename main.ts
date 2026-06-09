import { WebUI } from "@webui/deno-webui";

const myWindow = new WebUI();
await myWindow.showBrowser(
  "https://app.sketchup.com/app",
  WebUI.Browser.
);

await WebUI.wait();
