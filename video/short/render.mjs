// Renders every frame of the short with one headless Edge/Chrome (DevTools protocol).
//   node render.mjs <page url> <frames dir> <frame count> <fps> <browser-profile-dir>
// The page exposes render(t); each frame sets the time and takes a JPEG screenshot (1080x1920).
import { spawn } from "node:child_process";
import { writeFileSync } from "node:fs";
import { setTimeout as sleep } from "node:timers/promises";

const [url, dir, count, fps, profile] = process.argv.slice(2);
const BROWSER = process.env.BROWSER || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const PORT = 9343;
const browser = spawn(BROWSER, ["--headless=new", "--disable-gpu", "--hide-scrollbars", "--disable-extensions",
  "--disable-sync", "--no-first-run", `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`,
  "--allow-file-access-from-files", "about:blank"], { stdio: "ignore" });

let target;
for (let i = 0; i < 80 && !target; i++) {
  try { target = (await (await fetch(`http://127.0.0.1:${PORT}/json`)).json()).find(t => t.type === "page"); } catch { await sleep(250); }
}
if (!target) { console.error("browser did not start"); process.exit(1); }
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener("open", r));
let id = 0;
const pending = new Map();
ws.addEventListener("message", e => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } });
const send = (method, params = {}) => new Promise(res => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });

await send("Page.enable");
await send("Emulation.setDeviceMetricsOverride", { width: 1080, height: 1920, deviceScaleFactor: 1, mobile: false });
await send("Page.navigate", { url });
for (let i = 0; i < 200; i++) {
  const r = await send("Runtime.evaluate", { expression: "document.readyState === 'complete' && window.__ready === true", returnByValue: true });
  if (r.result?.result?.value) break;
  await sleep(50);
}
const ready = "document.fonts.ready.then(() => Promise.all([...document.images].map(i => i.complete ? 1 : new Promise(r => { i.onload = i.onerror = r; })))).then(() => 1)";
await Promise.race([send("Runtime.evaluate", { expression: ready, awaitPromise: true }), sleep(8000)]);
// background images (screenshots) load lazily: touch every scene once so they are decoded before frame 0
await send("Runtime.evaluate", { expression: "document.querySelectorAll('.scene').forEach(s => s.classList.add('on')); 1" });
await sleep(1500);

const n = +count, rate = +fps;
for (let f = 0; f < n; f++) {
  await send("Runtime.evaluate", { expression: `render(${(f / rate).toFixed(4)})` });
  const shot = await send("Page.captureScreenshot", { format: "jpeg", quality: 92 });
  writeFileSync(`${dir}/${String(f).padStart(5, "0")}.jpg`, Buffer.from(shot.result.data, "base64"));
  if ((f + 1) % 300 === 0) console.log(`${f + 1}/${n}`);
}
console.log(`rendered ${n} frames`);
ws.close();
browser.kill();
process.exit(0);
