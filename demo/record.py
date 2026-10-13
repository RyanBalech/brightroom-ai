"""Record the narrated demo video of the real app.

    python api.py &                 # app must be running on :8611
    python demo/record.py           # -> demo/BrightRoom_demo.mp4

Speech: macOS `say` (see demo/narration.json). Screen: Chrome driven by Playwright, frames captured
through the DevTools screencast. Audio and video are aligned on wall-clock timestamps and muxed with ffmpeg.
"""
import asyncio
import base64
import json
import pathlib
import re
import shutil
import subprocess
import time

import imageio_ffmpeg
from playwright.async_api import async_playwright

HERE = pathlib.Path(__file__).parent
FRAMES = HERE / "frames"
URL = "http://localhost:8611/"
W, H = 1600, 900
GAP = 0.7  # silence between segments

INIT_JS = r"""
(() => {
  const css = `
  #__cur{position:fixed;left:0;top:0;width:22px;height:22px;margin:-11px 0 0 -11px;border-radius:50%;
    background:rgba(74,67,196,.28);border:2px solid #4a43c4;z-index:2147483647;pointer-events:none;
    transition:transform .12s ease, background .12s ease}
  main{padding-bottom:300px}
  #__cur.down{transform:scale(.6);background:rgba(74,67,196,.6)}
  #__cap{position:fixed;left:50%;bottom:26px;transform:translateX(-50%);max-width:1180px;z-index:2147483646;
    background:rgba(23,22,29,.90);color:#fff;font:500 19px/1.4 Inter,system-ui,sans-serif;padding:11px 20px;
    border-radius:14px;text-align:center;pointer-events:none;opacity:0;transition:opacity .2s;
    box-shadow:0 12px 30px -10px rgba(0,0,0,.5)}
  #__slide{position:fixed;inset:0;z-index:2147483640;display:none;align-items:center;justify-content:center;
    background:radial-gradient(1200px 700px at 20% 10%,#4a43c4 0%,#1f1c57 55%,#141238 100%);color:#fff;
    font-family:Inter,system-ui,sans-serif;opacity:0;transition:opacity .45s}
  #__slide .in{width:1180px}
  #__slide .eyebrow{font:600 15px Inter;letter-spacing:.14em;text-transform:uppercase;color:#fbbf24}
  #__slide h1{font:400 76px/1.04 "Instrument Serif",Georgia,serif;margin:14px 0 0;letter-spacing:-.01em}
  #__slide h1 em{color:#c7c3ff}
  #__slide p.sub{font-size:24px;color:rgba(255,255,255,.78);margin-top:18px}
  #__slide .grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:34px}
  #__slide .box{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.16);border-radius:18px;
    padding:20px 24px;font-size:21px;line-height:1.4}
  #__slide .box b{display:block;font:600 13px Inter;letter-spacing:.12em;text-transform:uppercase;
    color:#fbbf24;margin-bottom:8px}
  #__slide .box.wide{grid-column:1 / -1}
  #__slide [data-r]{opacity:0;transform:translateY(14px);transition:opacity .5s,transform .5s}
  #__slide [data-r].on{opacity:1;transform:none}
  #__slide .quote{font:italic 400 30px/1.3 "Instrument Serif",Georgia,serif;color:#fff}
  `;
  const boot = () => {
    if (document.getElementById('__cur')) return;
    const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);
    for (const id of ['__slide', '__cap', '__cur']) { const d = document.createElement('div'); d.id = id; document.body.appendChild(d); }
    const cur = document.getElementById('__cur');
    addEventListener('mousemove', e => { cur.style.left = e.clientX + 'px'; cur.style.top = e.clientY + 'px'; }, true);
    addEventListener('mousedown', () => cur.classList.add('down'), true);
    addEventListener('mouseup', () => cur.classList.remove('down'), true);
  };
  if (document.body) boot(); else addEventListener('DOMContentLoaded', boot);
  window.__caption = t => { const c = document.getElementById('__cap'); if (!c) return; if (!t) { c.style.opacity = 0; return; } c.textContent = t; c.style.opacity = 1; };
  window.__slide = html => { const s = document.getElementById('__slide');
    if (html === null) { s.style.opacity = 0; setTimeout(() => s.style.display = 'none', 450); return; }
    s.innerHTML = '<div class="in">' + html + '</div>'; s.style.display = 'flex'; requestAnimationFrame(() => s.style.opacity = 1); };
  window.__reveal = n => document.querySelectorAll('#__slide [data-r]').forEach(e => { if (+e.dataset.r <= n) e.classList.add('on'); });
})();
"""

SLIDE_TITLE = """<div class="eyebrow">HEC MSc DSAIB · AI Solution Sprint · Case 02</div>
<h1>From a client enquiry<br>to a <em>feasible</em> proposal</h1>
<p class="sub">BrightRoom proposal assistant · Romaissae Melhaoui &amp; Ryan Balech</p>"""

SLIDE_PROBLEM = """<div class="eyebrow">The problem</div>
<h1 style="font-size:58px">A polished proposal is only useful<br>if the package <em>fits the brief</em>.</h1>
<div class="grid">
 <div class="box wide" data-r="1"><b>A typical enquiry</b><span class="quote">“A team day for about 15 people, with food, within a modest budget.”</span></div>
 <div class="box" data-r="2"><b>Today, by hand</b>Clarify the brief → check the catalogue → calculate a package → write the proposal.</div>
 <div class="box" data-r="3"><b>The costly mistake</b>A persuasive proposal that quietly breaks a requirement or the budget.</div>
 <div class="box" data-r="4"><b>User and value target</b>The salesperson. Efficiency with decision support: a first draft in seconds, feasibility visible before sending.</div>
 <div class="box" data-r="5"><b>Baseline</b>A single prompt to a chat assistant, with the catalogue pasted in.</div>
</div>"""

SLIDE_LIMITS = """<div class="eyebrow">Limitations and next step</div>
<h1 style="font-size:58px">What we know, and what we <em>haven't measured</em> yet.</h1>
<div class="grid">
 <div class="box" data-r="1"><b>Brittle offline reader</b>The rule-based reader misses unusual wording. First blind runs: 5/10 and 7/10. Every miss was reading, never pricing.</div>
 <div class="box" data-r="2"><b>Claude mode not run live</b>Built and tested with simulated responses only. Its accuracy is not measured yet.</div>
 <div class="box" data-r="3"><b>Evidence caveats</b>Baseline graded with a rubric, one sample per case. Time and cost figures are estimates.</div>
 <div class="box" data-r="4"><b>Next improvement</b>Run all 36 tests with Claude on, and measure real preparation time with a salesperson.</div>
 <div class="box wide" data-r="5" style="text-align:center"><span class="quote">Thank you for watching.</span><div style="margin-top:8px;font-size:17px;color:rgba(255,255,255,.7)">github.com/RyanBalech/brightroom-ai</div></div>
</div>"""


class Recorder:
    def __init__(self, page, cdp):
        self.page, self.cdp = page, cdp
        self.frames: list[tuple[float, str]] = []
        self.mouse = (W / 2, H / 2)
        self.marks: list[tuple[str, float]] = []

    async def on_frame(self, ev):
        name = f"{len(self.frames):06d}.jpg"
        (FRAMES / name).write_bytes(base64.b64decode(ev["data"]))
        self.frames.append((time.time(), name))
        await self.cdp.send("Page.screencastFrameAck", {"sessionId": ev["sessionId"]})

    async def js(self, fn, arg=None):
        await self.page.evaluate(fn, arg)

    async def move(self, loc, dx=0.5, dy=0.5, dur=0.55):
        """Glide the cursor to a point inside a locator (scrolling it into view first)."""
        try:
            await loc.evaluate("e => { const r = e.getBoundingClientRect(); if (r.top < 90 || r.bottom > innerHeight - 110) e.scrollIntoView({behavior:'smooth', block:'center'}); }", timeout=4000)
            await self.page.wait_for_timeout(450)
            b = await loc.bounding_box(timeout=4000)
        except Exception as e:  # never let a missing element break the recording
            print("  ! move failed:", str(e)[:80]); return
        tx, ty = b["x"] + b["width"] * dx, b["y"] + b["height"] * dy
        sx, sy = self.mouse
        n = max(8, int(dur / 0.022))
        for i in range(1, n + 1):
            t = i / n; t = t * t * (3 - 2 * t)
            await self.page.mouse.move(sx + (tx - sx) * t, sy + (ty - sy) * t)
            await self.page.wait_for_timeout(18)
        self.mouse = (tx, ty)

    async def click(self, loc, **kw):
        await self.move(loc, **kw)
        await self.page.wait_for_timeout(120)
        await self.page.mouse.down(); await self.page.wait_for_timeout(90); await self.page.mouse.up()

    async def top(self):
        await self.js("() => window.scrollTo({top: 0, behavior: 'smooth'})")

    async def segment(self, seg, events):
        """Play one narration segment: captions by sentence + scripted actions at given offsets (seconds)."""
        start = time.time()
        self.marks.append((seg["id"], start))
        print(f"{seg['id']}  ({seg['duration']}s)")
        sentences = [s.strip() for s in re.split(r"(?<=[.?!])\s+", seg["text"]) if s.strip()]
        total = sum(len(s) for s in sentences)
        t, timeline = 0.0, []
        for s in sentences:
            timeline.append((t, ("cap", s)))
            t += seg["duration"] * len(s) / total
        timeline += [(off, ("act", fn)) for off, fn in events]
        timeline.sort(key=lambda x: x[0])
        for off, (kind, payload) in timeline:
            wait = start + off - time.time()
            if wait > 0:
                await self.page.wait_for_timeout(wait * 1000)
            if kind == "cap":
                await self.js("t => window.__caption(t)", payload.replace("A I", "AI").replace("M C P", "MCP"))
            else:
                await payload()
        wait = start + seg["duration"] + GAP - time.time()
        if wait > 0:
            await self.page.wait_for_timeout(wait * 1000)


async def main():
    segs = {s["id"]: s for s in json.loads((HERE / "narration.json").read_text())}
    shutil.rmtree(FRAMES, ignore_errors=True); FRAMES.mkdir()
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        ctx = await browser.new_context(viewport={"width": W, "height": H}, device_scale_factor=1)
        await ctx.grant_permissions(["clipboard-read", "clipboard-write"])
        await ctx.add_init_script(INIT_JS)
        page = await ctx.new_page()
        await page.goto(URL)
        await page.wait_for_selector("text=Prepare draft")
        await page.wait_for_timeout(800)
        cdp = await ctx.new_cdp_session(page)
        R = Recorder(page, cdp)
        cdp.on("Page.screencastFrame", lambda ev: asyncio.ensure_future(R.on_frame(ev)))
        await R.js("h => window.__slide(h)", SLIDE_TITLE)
        await page.wait_for_timeout(700)
        await cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 92, "maxWidth": W, "maxHeight": H, "everyNthFrame": 1})
        await page.wait_for_timeout(1000)

        L = page.locator
        nav = lambda name: L("aside button", has_text=name)
        btn = lambda name: page.get_by_role("button", name=name, exact=False)
        txt = lambda t: page.get_by_text(t, exact=True).first
        prepare = btn("Prepare draft")
        reveal = lambda n: (lambda: R.js("n => window.__reveal(n)", n))

        # 1 · title
        await R.segment(segs["s01_title"], [])

        # 2 · problem, user, value target, baseline
        await R.js("h => window.__slide(h)", SLIDE_PROBLEM)
        await R.segment(segs["s02_problem"], [(4.5, reveal(1)), (11.5, reveal(2)), (18.5, reveal(3)), (25.0, reveal(4)), (34.0, reveal(5))])

        # 3 · solution choice (How it works page)
        async def to_how():
            await nav("How it works").evaluate("e => e.click()")  # the slide covers the page: click underneath it
            await page.wait_for_timeout(350); await R.js("() => window.__slide(null)")
        cards = L("main .grid").first.locator("> div")
        await R.segment(segs["s03_solution"], [
            (0.0, to_how),
            (6.5, lambda: R.move(cards.nth(0))), (9.0, lambda: R.move(cards.nth(3))),
            (11.5, lambda: R.move(cards.nth(1))), (15.5, lambda: R.move(cards.nth(2))),
            (19.0, lambda: R.move(cards.nth(4))),
            (27.5, lambda: R.move(txt("Use the same engine from Claude"), dur=0.8)),
        ])

        # 4 · routine case
        async def to_assistant():
            await R.click(nav("Proposal assistant"))
        await R.segment(segs["s04_routine"], [
            (0.0, to_assistant),
            (1.6, lambda: R.click(btn("Wheelchair + projector"))),
            (4.0, lambda: R.move(L("textarea"), dx=0.45)),
            (9.3, lambda: R.click(prepare)),
            (12.4, lambda: R.move(txt("Feasible — ready for your review"))),
            (14.8, lambda: R.move(txt("Structured brief"), dx=1.6, dy=4)),
            (18.2, lambda: R.move(L("li", has_text="Studio (€240) is cheaper").first, dx=0.4)),
            (23.0, lambda: R.move(txt("Budget margin"), dy=2.2)),
        ])

        # 5 · approval
        await R.segment(segs["s05_approve"], [
            (0.0, lambda: R.move(txt("Salesperson approval"))),
            (1.4, lambda: R.click(page.get_by_role("checkbox"))),
            (3.0, lambda: R.click(btn("Approve draft"))),
            (4.6, lambda: R.move(btn("Copy text"))),
            (5.9, lambda: R.move(btn("Download .md"), dur=0.4)),
        ])

        # 6 · difficult: over budget
        arts = L("article")
        await R.segment(segs["s06_budget"], [
            (0.0, R.top),
            (0.9, lambda: R.click(btn("Over budget"))),
            (5.6, lambda: R.click(prepare)),
            (8.6, lambda: R.move(txt("Package total"), dy=2.2)),
            (11.0, lambda: R.move(txt("Budget margin"), dy=2.2)),
            (14.5, lambda: R.move(txt("Alternatives. Each one changes the client's request."))),
            (19.6, lambda: R.move(arts.nth(0), dur=0.4)), (21.6, lambda: R.move(arts.nth(1), dur=0.4)),
            (23.0, lambda: R.move(arts.nth(2), dur=0.4)), (24.3, lambda: R.move(arts.nth(3), dur=0.4)),
        ])

        # 7 · difficult: capacity + duration + "confirm today"
        await R.segment(segs["s07_capacity"], [
            (0.0, R.top),
            (0.9, lambda: R.click(btn("30 people, 6 hours"))),
            (3.4, lambda: R.click(prepare)),
            (6.6, lambda: R.move(L("section", has_text="Cannot meet the brief as stated").first, dx=0.35, dy=0.7)),
            (11.4, lambda: R.move(L("li", has_text="nothing can be booked or confirmed").first, dx=0.4)),
        ])

        # 8 · missing information
        await R.segment(segs["s08_missing"], [
            (0.0, R.top),
            (0.9, lambda: R.click(btn("Best offer"))),
            (2.6, lambda: R.click(prepare)),
            (5.8, lambda: R.move(txt("Package total"), dy=2.2)),
            (8.0, lambda: R.move(L(".draft ol").first, dx=0.4)),
        ])

        # 9 · evidence
        await R.segment(segs["s09_evidence"], [
            (0.2, lambda: R.click(nav("Test evidence"))),
            (5.6, lambda: R.move(txt("Designed tests"), dy=2.4)),
            (8.6, lambda: R.move(txt("Single-prompt baseline"), dy=2.4)),
            (15.5, lambda: R.move(txt("Forbidden promises"), dy=2.4)),
            (26.0, lambda: R.move(txt("Blind set 1, first run"), dy=2.4)),
            (29.3, lambda: R.move(txt("Blind set 2, first run"), dy=2.4)),
            (34.6, lambda: R.click(btn("Run all tests"))),
            (38.6, lambda: R.move(L("button.h-8").nth(20), dur=0.6)),
            (40.4, lambda: R.move(L("button.h-8").nth(30), dur=0.5)),
        ])

        # 10 · limitations and next improvement
        await R.js("h => window.__slide(h)", SLIDE_LIMITS)
        await R.segment(segs["s10_limits"], [(1.2, reveal(1)), (9.6, reveal(2)), (16.2, reveal(3)), (21.8, reveal(4)), (28.2, reveal(5))])
        await R.js("() => window.__caption(null)")
        await page.wait_for_timeout(1600)
        end = time.time()
        await cdp.send("Page.stopScreencast")
        await page.wait_for_timeout(300)
        await browser.close()

    # ---- assemble ---------------------------------------------------------------------------
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    frames = R.frames
    t0 = frames[0][0]
    lines = ["ffconcat version 1.0"]
    for (t, name), nxt in zip(frames, frames[1:] + [(end, None)]):
        lines += [f"file 'frames/{name}'", f"duration {max(nxt[0] - t, 0.001):.4f}"]
    lines.append(f"file 'frames/{frames[-1][1]}'")
    (HERE / "frames.ffconcat").write_text("\n".join(lines))
    cmd = [ff, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(HERE / "frames.ffconcat")]
    filt, labels = [], []
    for i, (sid, start) in enumerate(R.marks):
        cmd += ["-i", str(HERE / "audio" / f"{sid}.aiff")]
        ms = int((start - t0) * 1000)
        filt.append(f"[{i + 1}:a]aresample=44100,adelay={ms}|{ms}[a{i}]"); labels.append(f"[a{i}]")
    filt.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0,apad[aout]")
    out = HERE / "BrightRoom_demo.mp4"
    cmd += ["-filter_complex", ";".join(filt), "-map", "0:v", "-map", "[aout]",
            "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
            "-c:a", "aac", "-b:a", "160k", "-t", f"{end - t0:.2f}", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)
    (HERE / "marks.json").write_text(json.dumps([(s, round(t - t0, 2)) for s, t in R.marks]))
    print(f"\n{len(frames)} frames, {end - t0:.1f}s -> {out}")


if __name__ == "__main__":
    asyncio.run(main())
