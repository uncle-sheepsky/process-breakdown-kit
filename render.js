// 프로세스 브레이크다운 렌더 (3/3) — page/index.html 을 한 프레임씩 찍어 → build/frames → ffmpeg + inputs/song.wav → out/<tag>.mp4
// 화면 = 시각 T 하나의 함수(window.__seekTo) — 같은 입력이면 프레임이 매번 같다(두 번 렌더 해시 대조로 확인).
// 사용: node render.js --tag my_video [--fps 25] [--scale 1920:1080] [--q 92] [--crf 17]
//       node render.js --stills 3,66,124,150            (몇 장만 찍어 보기 → build/still_<T>.jpg)
const fs = require("fs"), path = require("path"), crypto = require("crypto"), { execFileSync } = require("child_process")
const { pathToFileURL } = require("url"), { chromium } = require("playwright")
const KIT = __dirname, PAGE = path.join(KIT, "page", "index.html"), BUILD = path.join(KIT, "build"), FR = path.join(BUILD, "frames")
const arg = (k, d) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : d }
const FPS = Number(arg("--fps", 25)), TAG = arg("--tag", "process_breakdown"), STILLS = arg("--stills", null)
const SCALE = arg("--scale", "1920:1080"), JQ = Number(arg("--q", 92)), CRF = arg("--crf", "17"), AUDIO = arg("--audio", path.join(KIT, "inputs", "song.wav"))
;(async () => {
  const b = await chromium.launch({ args: ["--allow-file-access-from-files"] })
  const pg = await b.newPage({ viewport: { width: 1920, height: 1080 } })
  pg.on("pageerror", e => console.log("PAGEERROR", e.message))
  await pg.goto(pathToFileURL(PAGE).href, { waitUntil: "load" })
  await pg.waitForFunction(() => window.__ready === true, null, { timeout: 180000 })
  console.log("missing", JSON.stringify(await pg.evaluate(() => window.__missing)))
  const END = await pg.evaluate(() => window.__end)
  if (STILLS) {
    for (const t of STILLS.split(",").map(Number)) {
      await pg.evaluate(t => window.__seekTo(t), t)
      await pg.screenshot({ path: path.join(BUILD, `still_${t}.jpg`), type: "jpeg", quality: 85 })
    }
    await b.close(); return
  }
  fs.rmSync(FR, { recursive: true, force: true }); fs.mkdirSync(FR, { recursive: true })
  const N = Math.round(END * FPS), h = crypto.createHash("sha256")
  for (let f = 0; f < N; f++) {
    await pg.evaluate(t => window.__seekTo(t), f / FPS)
    const buf = await pg.screenshot({ type: "jpeg", quality: JQ })
    fs.writeFileSync(path.join(FR, `f${String(f).padStart(5, "0")}.jpg`), buf); h.update(buf)
    if (f % 300 === 0) console.log("frame", f, "/", N)
  }
  await b.close()
  fs.mkdirSync(path.join(KIT, "out"), { recursive: true })
  const out = path.join(KIT, "out", `${TAG}.mp4`)
  execFileSync("ffmpeg", ["-y", "-v", "error", "-framerate", String(FPS), "-i", path.join(FR, "f%05d.jpg"), "-i", AUDIO,
    "-vf", `scale=${SCALE}`, "-c:v", "libx264", "-preset", "medium", "-crf", CRF, "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out])
  console.log("frames", N, "sha", h.digest("hex").slice(0, 16), "->", out)
})()
