import { SizeHint, Webview } from "@webview/webview";

// const html = `
//   <html>
//   <body>
//     <h1>Hello from deno v${Deno.version.deno}</h1>
//   </body>
//   </html>
// `;

// const buttonWV = new Webview();

// buttonWV.navigate(`data:text/html,${encodeURIComponent(html)}`);


const webview = new Webview();
webview.navigate(Deno.args[0] || "https://www.wikipedia.org");

webview.size = { width: 512, height: 1024, hint: SizeHint.NONE };
webview.title = "BigBrowser";




// await Promise.all([buttonWV.run(), webview.run()]);
await webview.run();


