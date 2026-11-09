"""Build the static showcase page for a run (default: the committed sample run) into site/.

Deploy: cd site && vercel deploy --prod --yes   (Vercel project: ecom-ai-studio)
Usage:  python scripts/build_site.py [--run output/sample_run]
"""
import html
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from studio.data import load_brand  # noqa: E402

RUN = ROOT / (sys.argv[sys.argv.index("--run") + 1] if "--run" in sys.argv else "output/sample_run")
SITE = ROOT / "site"
REPO = "https://github.com/cainticjohncarlo-pixel/ecom-ai-studio"
E = html.escape

# Which layer caught each planted problem in the red-team (from redteam/result.json of the sample run).
REDTEAM_ROWS = [
    ("A1", "Subhead says 'leak-proof' and claims 36 hours cold", True, True, "Forbidden phrase; 36 is not in our evidence (24 h is)"),
    ("A1", "Testimonial swapped to the 5-star 'I've lost 10 pounds' review", False, True, "Verbatim and 5 stars, but a weight-loss claim"),
    ("A2", "Headline: 'Lighter than SummitSip'", True, True, "Competitor name; unsupported comparison"),
    ("A3", "Subhead borrows 'The last bottle you'll ever buy'", False, True, "A competitor's slogan; implies lifetime durability"),
    ("V1", "Caption: 'Drink more, lose weight'", True, True, "Forbidden phrase and health claim"),
    ("V1", "Voiceover: 'boosts your energy all day'", False, True, "A competitor's health claim reworded; also broke its caption"),
]


def trunc(text, n):
    return text if len(text) <= n else text[:n].rsplit(" ", 1)[0] + "…"


def load(name):
    return json.loads((RUN / name).read_text(encoding="utf-8"))


def section(n, title, sub, inner):
    return (f'<section id="s{n}"><div class="sec-head"><span class="sec-num">{n:02d}</span><div><h2>{title}</h2>'
            f'<p class="sub">{sub}</p></div></div>{inner}</section>')


def table(head, rows, cls=""):
    return (f'<div class="tbl {cls}"><table><thead><tr>' + "".join(f"<th>{h}</th>" for h in head) + "</tr></thead><tbody>"
            + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</tbody></table></div>")


def flowchart():
    def node(n, t, s, kind=""):
        return f'<div class="fl-node {kind}"><span class="fl-n">{n}</span><div><b>{t}</b><span>{s}</span></div></div>'
    return f'''<div class="flow">
  {node("in", "Brand data", "Shopify product, reviews, competitor ads, brand guide, b-roll library", "src")}
  <div class="fl-arrow">&darr;</div>
  {node("1", "Research agent", "Decides which of 5 tools to call; returns a cited research brief", "ai")}
  <div class="fl-arrow">&darr;</div>
  {node("2", "Copywriter agent", "3 static ads + a video script; every claim cites evidence ids", "ai")}
  <div class="fl-arrow">&darr;</div>
  <div class="fl-pair">{node("3", "Deterministic checks", "Limits, exact offer and CTA, evidence ids, numbers, forbidden words, competitors", "rule")}
  {node("4", "Reviewer agent", "Reads every claim against the evidence it cites; pass or fail with fixes", "ai")}</div>
  <div class="fl-loop">&#8634; any issue goes back to the copywriter (max 2 rewrites), then the asset is blocked</div>
  <div class="fl-arrow">&darr; approved only</div>
  <div class="fl-pair">{node("5", "Static ad engine", "Feed 4:5 and story 9:16 PNGs in the brand colours", "eng")}
  {node("6", "Video editor", "Voiceover per beat &rarr; edit plan &rarr; ffmpeg &rarr; ffprobe check", "eng")}</div>
  <div class="fl-arrow">&darr;</div>
  {node("7", "Publish + monitor", "Meta ads created paused, Drive, Notion, Slack; every step logged with cost and alerts", "out")}
</div>'''


def page():
    s, research, trace = load("summary.json"), load("research.json"), load("research_trace.json")
    copy, plan, qa = load("final_copy.json"), load("video/edit_plan.json"), load("video/qa.json")
    rounds = sorted(RUN.glob("review_round*.json"))
    kit = load_brand(ROOT / "data" / "sample_brand")
    ev = kit.evidence()
    ads = copy["static_ads"]

    gallery = "".join(f'''
      <figure class="ad"><a href="out/ads/{a['id']}_feed.png" target="_blank" rel="noopener"><img src="out/ads/{a['id']}_feed.png" alt="{E(a['headline'])}" loading="lazy"></a>
      <figcaption><b>{a['id']} &middot; {E(a['angle'])}</b><span>Feed 4:5 &middot; <a href="out/ads/{a['id']}_story.png" target="_blank" rel="noopener">story 9:16</a></span></figcaption></figure>''' for a in ads)
    output = f'''<div class="out-grid">
      <figure class="vid"><video controls preload="metadata" playsinline poster="out/video/V1_poster.jpg"><source src="out/video/V1_9x16.mp4" type="video/mp4"></video>
      <figcaption><b>V1 &middot; {E(copy['video']['angle'])}</b><span>{qa['duration']:.1f}s &middot; 1080x1920 &middot; voiceover + b-roll + captions</span></figcaption></figure>
      <div class="ads">{gallery}</div></div>
      <p class="note">The brand (Ridgeline Supply Co.) and its reviews and competitor ads are fictional test data with deliberate traps. Photos are openly licensed stand-ins (<a href="{REPO}/blob/main/data/sample_brand/assets/SOURCES.md">sources</a>).</p>'''

    tools = table(["#", "Tool the agent chose", "Input"], [[i, f"<code>{t['tool']}</code>", f"<code>{E(json.dumps(t['input']))}</code>"] for i, t in enumerate(trace, 1)])
    quotes = "".join(f'<li>&ldquo;{E(q["text"])}&rdquo; <span class="id">{q["review_id"]}</span></li>' for q in research["customer_language"][:5])
    angles = "".join(f'<li><b>{E(a["name"])}</b>: {E(a["hook_idea"])} <span class="id">{", ".join(a["evidence_ids"][:4])}</span></li>' for a in research["recommended_angles"])
    avoid = "".join(f"<li>{E(x)}</li>" for x in research["avoid"][:7])
    research_html = f'''<div class="grid2">
      <div class="card"><h3>Tool calls</h3>{tools}</div>
      <div class="card"><h3>Customer language (verbatim, cited)</h3><ul class="q">{quotes}</ul></div></div>
      <div class="grid2"><div class="card"><h3>Ad angles it recommended</h3><ul>{angles}</ul></div>
      <div class="card warn"><h3>Traps it flagged on its own</h3><ul>{avoid}</ul></div></div>'''

    review_rows = []
    for r in rounds:
        rd = json.loads(r.read_text(encoding="utf-8"))
        for aid, v in rd["verdicts"].items():
            checks = sum(1 for i in v["issues"] if i["from"] == "checks")
            rev = sum(1 for i in v["issues"] if i["from"] == "reviewer")
            review_rows.append([rd["round"], aid, checks, rev, '<span class="ok">&#10003; approved</span>' if v["approved"] else '<span class="bad">&#10005; sent back</span>',
                                E((v["notes"] or ["-"])[0])[:160]])
    yes, no = '<span class="ok">&#10003; caught</span>', '<span class="muted">missed</span>'
    red = table(["Asset", "Planted problem", "Code checks", "Reviewer agent", "Why it matters"],
                [[a, E(p), yes if c else no, yes if r else no, E(w)] for a, p, c, r, w in REDTEAM_ROWS])
    checking = (table(["Round", "Asset", "Check issues", "Reviewer issues", "Result", "Reviewer note"], review_rows)
                + f'<h3 class="h3">Red-team: 6 problems planted in the approved copy</h3>{red}'
                + '<p class="note">All four assets were blocked. Rules caught the exact problems; only the reviewer caught meaning: a verbatim 5-star review that is still a '
                  f'weight-loss claim, and a competitor\'s slogan and health claim reworded into our copy. <a href="{REPO}/blob/main/output/sample_run/REDTEAM.md">Full red-team report</a>.</p>')

    evid = ""
    for a in ads:
        rows = [[E(c["text"]), "<br>".join(f'<span class="id">{i}</span> {E(trunc(ev[i].text, 120))}' for i in c["evidence_ids"] if i in ev)] for c in a["claims"]]
        t = a.get("testimonial")
        if t:
            rows.append([f"Testimonial: &ldquo;{E(t['text'])}&rdquo;", f'<span class="id">{t["review_id"]}</span> {E(trunc(ev[t["review_id"]].text, 120))}'])
        evid += f'<h3 class="h3">{a["id"]} &middot; &ldquo;{E(a["headline"])}&rdquo;</h3>' + table(["Claim in the ad", "Evidence it cites"], rows)

    beats = copy["video"]["beats"]
    vrows = [[str(p["beat"]), E(p["line"]) or "-", E(p["caption"]), f"<code>{p['broll_id']}</code>", f"{p['seconds']:.2f}s",
              ", ".join(beats[p["beat"] - 1]["evidence_ids"]) if isinstance(p["beat"], int) else ""] for p in plan["segments"]]
    video_html = (table(["Beat", "Voiceover", "Caption", "B-roll", "Length", "Evidence"], vrows)
                  + f'<p class="note">Planned {plan["total_seconds"]:.2f}s, rendered {qa["duration"]:.2f}s. ffprobe checks: '
                  + ("<span class='ok'>all passed</span> (1080x1920, audio present, length matches the plan)." if not qa["problems"] else E("; ".join(qa["problems"])))
                  + "</p>")

    integ = table(["Integration", "What it does", "This run"], [
        ["Shopify", "Pulls the product (Admin GraphQL or public JSON)", "dry run: product from the brand folder"],
        ["Meta Ads", "Uploads each approved ad and creates it <b>PAUSED</b>", "dry run: 3 creative + ad payloads"],
        ["Google Drive", "Uploads the finished files", "dry run: 7 upload payloads"],
        ["Notion", "One tracker row per asset", "dry run: 4 rows"],
        ["Slack", "Run summary and failure alerts", "dry run: summary payload"],
    ])
    steps = table(["Step", "Status", "Seconds"], [[E(x["step"]), x["status"], x["seconds"]] for x in s["steps"]])
    ops = (f'<div class="grid2"><div class="card"><h3>Integrations</h3>{integ}<p class="note">Each runs live when its env vars are set, '
           f'otherwise it writes the exact payload it would send (<a href="{REPO}/tree/main/output/sample_run/integrations">payloads</a>).</p></div>'
           f'<div class="card"><h3>Monitoring (this run)</h3>{steps}<p class="note">{s["llm_calls"]} Claude calls &middot; {s["input_tokens"]:,} in / '
           f'{s["output_tokens"]:,} out tokens &middot; ${s["usd"]:.2f} &middot; logged to <a href="{REPO}/blob/main/output/sample_run/run.jsonl">run.jsonl</a>; failures alert Slack.</p></div></div>')

    run_html = f'''<div class="card"><pre>pip install -r requirements.txt      # plus ffmpeg
cp .env.example .env                 # add ANTHROPIC_API_KEY
python -m studio run --brand data/sample_brand --out output/my_run

# no API key: replay this exact run through the whole pipeline
python -m studio run --out output/replay --replay --cassette output/sample_run/llm_cassette.json --tts silent
python -m pytest -q                  # 14 tests, run in CI on every push</pre>
<p>Code, tests and the full run files: <a href="{REPO}">{REPO.replace("https://", "")}</a></p></div>'''

    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>ecom-ai-studio</title><meta name="description" content="AI creative pipeline for e-commerce: research, copy and reviewer agents, static ad engine and an ffmpeg video editor. Sample run by John Carlo Caintic.">
<meta name="robots" content="noindex">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&family=Playfair+Display:wght@600;700&display=swap" rel="stylesheet">
<style>
:root{{--ink:#1C1917;--muted:#6B645B;--cream:#F6F4EF;--card:#fff;--line:#E6E1D8;--green:#2E5A47;--green-soft:#E7F0EA;--gold:#C9A96E;--rust:#C4622D;--rust-soft:#FBEEE6;--amber:#9A6A0B;--amber-soft:#FFF4DC;--red:#A33A2A;--blue-soft:#E8EEF8;--chip:#F2EEE6}}
*{{box-sizing:border-box}} html{{scroll-behavior:smooth}}
body{{margin:0;background:var(--cream);color:var(--ink);font:16px/1.6 Inter,system-ui,sans-serif}}
a{{color:var(--rust)}} code{{font:500 .8em 'JetBrains Mono',monospace;background:var(--chip);border:1px solid var(--line);border-radius:5px;padding:.05em .35em;word-break:break-word}}
pre{{font:13px/1.6 'JetBrains Mono',monospace;background:var(--ink);color:#F1EDE6;padding:14px 16px;border-radius:10px;overflow-x:auto;margin:0 0 12px}}
header{{background:var(--ink);color:#fff;text-align:center;padding:60px 16px 72px}}
.eyebrow{{font:600 .78rem 'Playfair Display',serif;color:var(--gold);letter-spacing:.24em;text-transform:uppercase}}
h1{{font:700 clamp(2rem,5vw,3.1rem)/1.12 'Playfair Display',serif;margin:.35em auto .3em;max-width:860px}}
.lead{{color:#CFCAC0;max-width:720px;margin:0 auto}}
.btns{{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;margin-top:24px}}
.btn{{padding:10px 16px;border-radius:999px;font-weight:600;font-size:.9rem;text-decoration:none;border:1px solid #3A3530;color:#fff;background:#2A2522}}
.btn.primary{{background:var(--green);border-color:var(--green)}}
.byline{{color:#9C958A;font-size:.85rem;margin-top:16px}}
main{{max-width:1040px;margin:0 auto;padding:0 16px 80px}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-top:-38px}}
.stat{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px}}
.stat b{{display:block;font:700 1.55rem 'Playfair Display',serif;color:var(--green)}} .stat span{{font-size:.82rem;color:var(--muted)}}
section{{margin-top:56px}}
.sec-head{{display:flex;gap:14px;align-items:flex-start;margin-bottom:18px}}
.sec-num{{flex:none;width:40px;height:40px;border-radius:50%;background:var(--green);color:#fff;display:grid;place-items:center;font:600 .9rem 'JetBrains Mono',monospace}}
h2{{font:700 1.6rem/1.2 'Playfair Display',serif;margin:2px 0}} h3{{font-size:1rem;margin:0 0 10px}} .h3{{margin:22px 0 8px;font-size:1rem}}
.sub{{font:400 .8rem 'JetBrains Mono',monospace;color:var(--muted);margin:0}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 20px}}
.card.warn{{background:var(--amber-soft);border-color:#EBD7A4}}
.grid2{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px;margin-bottom:14px}}
.note{{font-size:.86rem;color:var(--muted)}} .muted{{color:var(--muted)}}
.ok{{color:var(--green);font-weight:700;white-space:nowrap}} .bad{{color:var(--red);font-weight:700;white-space:nowrap}}
.id{{font:500 .74rem 'JetBrains Mono',monospace;background:var(--chip);border:1px solid var(--line);border-radius:4px;padding:0 4px;color:var(--green)}}
ul{{margin:0;padding-left:18px}} li{{margin:6px 0;font-size:.92rem}} ul.q li{{font-style:italic}}
/* output */
.out-grid{{display:grid;grid-template-columns:minmax(0,300px) minmax(0,1fr);gap:18px;align-items:start}}
.vid video{{width:100%;aspect-ratio:9/16;background:#000;border-radius:14px;display:block}}
.ads{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}}
.ad img{{width:100%;display:block;border-radius:10px;border:1px solid var(--line)}}
figure{{margin:0}} figcaption{{padding:8px 2px 0;font-size:.84rem}} figcaption b{{display:block}} figcaption span{{color:var(--muted)}}
/* flow */
.flow{{display:flex;flex-direction:column;align-items:center;gap:6px}}
.fl-node{{display:flex;gap:12px;align-items:center;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 16px;width:min(560px,100%)}}
.fl-node b{{display:block}} .fl-node span{{font-size:.84rem;color:var(--muted)}}
.fl-node .fl-n{{flex:none;min-width:30px;height:30px;padding:0 6px;border-radius:15px;background:var(--ink);color:#fff;display:grid;place-items:center;font:600 .74rem 'JetBrains Mono',monospace}}
.fl-node.ai{{background:var(--green-soft);border-color:#B9D2C3}} .fl-node.ai .fl-n{{background:var(--green)}}
.fl-node.ai b::after{{content:"AGENT";margin-left:8px;font:700 .6rem 'JetBrains Mono',monospace;background:var(--green);color:#fff;border-radius:4px;padding:1px 6px;vertical-align:middle}}
.fl-node.rule{{background:var(--amber-soft);border-color:#EBD7A4}} .fl-node.rule .fl-n{{background:var(--amber)}}
.fl-node.eng{{background:var(--blue-soft);border-color:#C9D6EC}} .fl-node.eng .fl-n{{background:#2F5597}}
.fl-node.src .fl-n,.fl-node.out .fl-n{{background:var(--rust)}}
.fl-pair{{display:grid;grid-template-columns:1fr 1fr;gap:10px;width:min(900px,100%)}} .fl-pair .fl-node{{width:100%}}
.fl-arrow{{color:var(--gold);font:600 .85rem 'JetBrains Mono',monospace}}
.fl-loop{{font:500 .8rem 'JetBrains Mono',monospace;color:var(--rust);background:var(--rust-soft);border:1px dashed #E7C3B0;border-radius:999px;padding:4px 14px;text-align:center}}
/* tables */
.tbl{{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:12px}}
.card .tbl{{border:0;border-radius:0}}
table{{border-collapse:collapse;width:100%;font-size:.86rem}}
th{{text-align:left;font:700 .64rem Inter;letter-spacing:.12em;text-transform:uppercase;background:#FBFAF7;padding:9px 11px;border-bottom:1px solid var(--line);white-space:nowrap}}
td{{padding:9px 11px;border-bottom:1px solid var(--line);vertical-align:top}} tr:last-child td{{border-bottom:0}}
footer{{text-align:center;color:var(--muted);font-size:.82rem;padding:24px 16px 48px}}
@media (max-width:760px){{.out-grid{{grid-template-columns:1fr}} .vid{{max-width:320px;margin:0 auto}} .ads{{grid-template-columns:1fr 1fr}} .fl-pair{{grid-template-columns:1fr}}}}
</style></head><body>
<header>
  <div class="eyebrow">ecom-ai-studio &middot; Python</div>
  <h1>An AI creative pipeline for e-commerce brands</h1>
  <p class="lead">A research agent studies the product, reviews and competitor ads. A copywriter agent writes the ads. A reviewer agent checks that work against the evidence. Then a static ad engine and an ffmpeg video editor produce the finished creative.</p>
  <div class="btns"><a class="btn primary" href="#s1">See the output</a><a class="btn" href="{REPO}">Code on GitHub</a><a class="btn" href="#s4">Red-team</a></div>
  <div class="byline">Built by John Carlo Caintic &middot; one real run, committed with every file</div>
</header>
<main>
  <div class="stats">
    <div class="stat"><b>{s["approved"]}/{s["approved"] + s["blocked"]}</b><span>assets approved</span></div>
    <div class="stat"><b>{s["research_tool_calls"]}</b><span>tool calls by the research agent</span></div>
    <div class="stat"><b>6/6</b><span>planted problems caught</span></div>
    <div class="stat"><b>${s["usd"]:.2f}</b><span>per run, {s["llm_calls"]} Claude calls</span></div>
    <div class="stat"><b>{round(s["seconds"])}s</b><span>end to end, video included</span></div>
  </div>
{section(1, "The output", "one run: 3 static ads (2 sizes each) and a vertical video ad", output)}
{section(2, "How it works", "three agents, two checkers, two render engines", flowchart())}
{section(3, "Research agent", "it picked its own tool calls, then wrote a cited brief", research_html)}
{section(4, "Agents checking agents", "deterministic checks + a reviewer agent; both must pass", checking)}
{section(5, "Evidence behind every claim", "copy that cites anything outside the brand's evidence fails", evid)}
{section(6, "Video edit plan", "each beat gets b-roll for exactly the length of its line", video_html)}
{section(7, "Integrations and monitoring", "Shopify, Meta, Drive, Notion, Slack; every step timed and costed", ops)}
{section(8, "Run it", "Python 3.12, Claude Opus 5.5, Pillow, ffmpeg", run_html)}
</main>
<footer>ecom-ai-studio &middot; John Carlo Caintic &middot; <a href="{REPO}">GitHub</a></footer>
</body></html>'''


def main():
    out = SITE / "out"
    shutil.rmtree(out, ignore_errors=True)
    (out / "ads").mkdir(parents=True)
    (out / "video").mkdir(parents=True)
    for p in (RUN / "ads").glob("*.png"):
        shutil.copy(p, out / "ads" / p.name)
    for name in ("V1_9x16.mp4", "V1_poster.jpg"):
        shutil.copy(RUN / "video" / name, out / "video" / name)
    (SITE / "index.html").write_text(page(), encoding="utf-8")
    print("built", SITE / "index.html")


if __name__ == "__main__":
    main()
