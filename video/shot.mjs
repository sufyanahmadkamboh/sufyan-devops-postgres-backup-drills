// Screenshots pages with one headless Edge/Chrome over the DevTools protocol.
//   node shot.mjs <jobs.json> <browser-profile-dir>
// jobs.json: [{"url": "...", "out": "...", "w": 1920, "h": 1080}, ...]
import { spawn } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { setTimeout as sleep } from "node:timers/promises";

const BROWSER = process.env.BROWSER || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const PORT = 9341;
const jobs = JSON.parse(readFileSync(process.argv[2], "utf8"));
const browser = spawn(BROWSER, ["--headless=new", "--disable-gpu", "--hide-scrollbars", "--disable-extensions", "--disable-sync", "--no-first-run", `--remote-debugging-port=${PORT}`,
  `--user-data-dir=${process.argv[3]}`, "--allow-file-access-from-files", "about:blank"], { stdio: "ignore" });

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
const ready = "document.fonts.ready.then(() => Promise.all([...document.images].map(i => i.complete ? 1 : new Promise(r => { i.onload = i.onerror = r; })))).then(() => 1)";

await send("Page.enable");
let n = 0;
for (const job of jobs) {
  await send("Emulation.setDeviceMetricsOverride", { width: job.w || 1920, height: job.h || 1080, deviceScaleFactor: 1, mobile: false });
  await send("Page.navigate", { url: job.url });
  for (let i = 0; i < 100; i++) {
    const r = await send("Runtime.evaluate", { expression: "document.readyState === 'complete' && window.__ready === true", returnByValue: true });
    if (r.result?.result?.value) break;
    await sleep(50);
  }
  // fonts and images, but never wait forever (a stalled web-font request once hung a whole build)
  await Promise.race([send("Runtime.evaluate", { expression: ready, awaitPromise: true }), sleep(8000)]);
  const shot = await send("Page.captureScreenshot", { format: "png" });
  writeFileSync(job.out, Buffer.from(shot.result.data, "base64"));
  if (++n % 20 === 0) console.log(`${n}/${jobs.length}`);
}
console.log(`captured ${n} frames`);
ws.close();
browser.kill();
process.exit(0);
