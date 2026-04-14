import os
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
import vertexai
from agents.orchestrator import DOMAIN_PERSONAS, get_metis_orchestrator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
location = os.getenv("GOOGLE_CLOUD_LOCATION")

# Initialize Vertex AI
if (
    not os.getenv("OPENROUTER_API_KEY")
    and project_id
    and location
    and project_id != "XXXX"
    and location != "XXXX"
):
    vertexai.init(
        project=project_id,
        location=location
    )

app = FastAPI(title="Metis Intelligence API")

class ResearchRequest(BaseModel):
    domain_id: str
    custom_domain: Optional[str] = None

@app.get("/")
def read_root():
    return {"message": "Welcome to Metis: Trend-to-Content Intelligence API"}

@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)

@app.get("/ui", response_class=HTMLResponse)
def read_ui():
    return """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Metis Intelligence</title>
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Cdefs%3E%3CradialGradient id='g' cx='50%25' cy='38%25' r='60%25'%3E%3Cstop offset='0%25' stop-color='%23f8edca'/%3E%3Cstop offset='45%25' stop-color='%23d2b070'/%3E%3Cstop offset='55%25' stop-color='%23b58d51'/%3E%3Cstop offset='100%25' stop-color='%23a77b42'/%3E%3C/radialGradient%3E%3C/defs%3E%3Crect x='4' y='4' width='56' height='56' rx='14' fill='url(%23g)' stroke='%238a6334' stroke-width='2'/%3E%3Ccircle cx='32' cy='32' r='10' fill='rgba(255,255,255,0.25)'/%3E%3C/svg%3E">
  <style>
    :root{--bg:#d6c1a0;--stone:#d2b187;--stone-2:#a67d4a;--stone-3:#7a5a2f;--panel:#f5ead6;--ink:#2c241c;--muted:#625648;--line:rgba(89,67,38,.22);--gold:#c5a15f;--gold-2:#e3cd97;--danger:#8f3a2b}
    *{box-sizing:border-box}body{margin:0;font-family:Inter,"Segoe UI",sans-serif;color:var(--ink);background:radial-gradient(circle at 10% 8%,rgba(249,233,196,.78),transparent 20%),radial-gradient(circle at 82% 12%,rgba(168,120,62,.28),transparent 18%),radial-gradient(circle at 62% 78%,rgba(114,86,46,.14),transparent 24%),radial-gradient(circle at 30% 60%,rgba(255,245,226,.25),transparent 30%),linear-gradient(180deg,rgba(255,249,236,.3),rgba(112,83,45,.12)),linear-gradient(128deg,#ead9bb 0%,#d6bc93 46%,#c3a97d 100%);position:relative;overflow-x:hidden}
    body:before{content:"";position:fixed;inset:0;pointer-events:none;opacity:.32;background:radial-gradient(circle at 12% 18%,rgba(255,248,234,.22),transparent 46%),radial-gradient(circle at 86% 22%,rgba(128,96,56,.16),transparent 48%),radial-gradient(circle at 44% 78%,rgba(98,72,40,.14),transparent 52%),linear-gradient(135deg,rgba(90,68,38,.06),transparent 60%),linear-gradient(45deg,rgba(255,244,221,.08),transparent 55%);background-size:auto,auto,auto,320px 320px,420px 420px}
    body:after{content:"";position:fixed;inset:-10% -10% -5% -10%;pointer-events:none;opacity:.25;background:radial-gradient(circle at 12% 22%,rgba(88,64,32,.35),transparent 38%),radial-gradient(circle at 82% 30%,rgba(70,50,28,.25),transparent 42%),radial-gradient(circle at 48% 82%,rgba(120,93,56,.22),transparent 40%);mix-blend-mode:multiply;filter:blur(2px)}
    .shell{max-width:1200px;margin:0 auto;padding:18px 16px 56px}
    .masthead{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;margin-bottom:10px}
    .kicker{font-size:9px;letter-spacing:.34em;text-transform:uppercase;color:#7b643e;font-weight:700}
    .masthead h1{margin:4px 0 0;font-family:Georgia,serif;font-size:clamp(1.25rem,2vw,2.1rem);line-height:1.05;max-width:22ch}
    .masthead p{margin:6px 0 0;max-width:44ch;color:var(--muted);line-height:1.55;font-size:.92rem}
    .caption{margin:10px 0 0;font-size:.78rem;letter-spacing:.18em;text-transform:uppercase;color:#7b643e;font-weight:700}
    .sigil{width:56px;height:56px;border-radius:20px;background:radial-gradient(circle at 50% 38%,#f8edca 0,#d2b070 32%,#b58d51 33%,rgba(255,255,255,.15) 100%);box-shadow:0 12px 24px rgba(94,68,34,.16),inset 0 1px 0 rgba(255,255,255,.5),inset 0 -6px 12px rgba(94,68,34,.16)}
    .stage{display:grid;grid-template-columns:minmax(0,1fr);gap:16px;align-items:start}
    .tablet{position:relative;padding:30px 34px 32px 40px;border-radius:36px;background:radial-gradient(circle at 18% 16%,rgba(255,247,227,.55),transparent 22%),radial-gradient(circle at 78% 22%,rgba(145,105,56,.22),transparent 24%),radial-gradient(circle at 46% 76%,rgba(255,245,227,.38),transparent 30%),linear-gradient(180deg,rgba(233,213,182,.98),rgba(184,150,104,.98));border:1px solid rgba(82,58,28,.46);box-shadow:0 34px 84px rgba(66,46,20,.32),inset 0 1px 0 rgba(255,255,255,.36),inset 0 -26px 34px rgba(90,67,36,.3),inset 0 0 0 1px rgba(140,108,63,.12);clip-path:polygon(.6% 6.2%,2.6% 1.8%,7.4% 0%,82% 0%,90% 2%,96% 6%,99.5% 13%,99.5% 85%,96.5% 93%,91.5% 100%,10.5% 100%,4% 97%,.6% 90.5%)}
    .tablet:before{content:"";position:absolute;inset:6px;border-radius:30px;border:1px solid rgba(109,82,47,.22);box-shadow:inset 0 0 0 2px rgba(255,248,232,.16)}
    .tablet:after{content:"";position:absolute;inset:-10px;border-radius:44px;pointer-events:none;background:
      radial-gradient(circle at 2% 6%,rgba(78,56,29,.24),transparent 42%),
      radial-gradient(circle at 98% 6%,rgba(78,56,29,.22),transparent 40%),
      radial-gradient(circle at 4% 98%,rgba(78,56,29,.22),transparent 42%),
      radial-gradient(circle at 98% 96%,rgba(78,56,29,.24),transparent 40%),
      radial-gradient(circle at 14% 10%,rgba(88,64,33,.18) 0 1.4%,transparent 1.5%),
      radial-gradient(circle at 88% 14%,rgba(88,64,33,.16) 0 1.2%,transparent 1.3%),
      radial-gradient(circle at 10% 88%,rgba(88,64,33,.16) 0 1.5%,transparent 1.6%),
      radial-gradient(circle at 92% 86%,rgba(88,64,33,.18) 0 1.3%,transparent 1.4%),
      linear-gradient(128deg,transparent 0 84%,rgba(74,54,27,.16) 84.6%,transparent 85.4%),
      linear-gradient(52deg,transparent 0 86%,rgba(255,248,230,.12) 86.6%,transparent 87.4%);
      background-size:auto;mix-blend-mode:multiply;opacity:.36}
    .tablet>*{position:relative;z-index:1}
    .tablet-head{display:flex;justify-content:space-between;align-items:end;gap:16px}.tablet-head h2{margin:0;font-family:Georgia,serif;font-size:clamp(1.45rem,2vw,2rem);text-transform:uppercase;letter-spacing:.06em}.tablet-head p{margin:8px 0 0;color:var(--muted);line-height:1.6;max-width:46ch}.state-pill{padding:8px 12px;border-radius:999px;border:1px solid rgba(109,82,47,.14);background:rgba(255,255,255,.22);font-size:.72rem;letter-spacing:.18em;text-transform:uppercase;color:#7b643e;font-weight:700;white-space:nowrap}
    .selection{margin-top:18px;padding:18px;border-radius:22px;background:linear-gradient(180deg,rgba(255,248,231,.14),rgba(115,88,51,.06));border:1px solid rgba(109,82,47,.16);box-shadow:inset 0 1px 0 rgba(255,255,255,.16),inset 0 -12px 18px rgba(110,82,47,.1)}
    .selection h3{margin:0 0 6px;font-family:Georgia,serif}
    .selection p{margin:0 0 14px;color:var(--muted);line-height:1.6}
    .inscription{display:inline-block;padding:0 0 2px;border-radius:0;background:linear-gradient(180deg,rgba(255,249,238,.22),rgba(255,249,238,.08));border:0;border-bottom:1px solid rgba(140,108,63,.24);box-shadow:none}
    .inscription.sub{padding:0;border-radius:0;background:linear-gradient(180deg,rgba(255,249,238,.18),rgba(255,249,238,.05));border:0;font-size:.96rem}
    .topic-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
    .topic-tile{appearance:none;border:1px solid rgba(90,66,33,.52);border-radius:18px;padding:14px;text-align:left;background:linear-gradient(180deg,rgba(223,203,168,.98),rgba(160,128,84,.98));box-shadow:inset 0 2px 0 rgba(255,255,255,.28),inset 0 -16px 20px rgba(76,55,27,.3),inset 5px 0 0 rgba(255,247,230,.16),inset -5px 0 0 rgba(88,64,33,.16),0 8px 14px rgba(65,45,22,.12);cursor:pointer;transition:transform .16s ease,box-shadow .16s ease,border-color .16s ease,filter .16s ease;min-height:92px;display:grid;gap:8px;align-content:space-between;position:relative;overflow:hidden}
    .topic-tile:before{content:"";display:none}
    .topic-tile:after{content:"";position:absolute;inset:0;border-radius:18px;border:1px solid rgba(255,248,232,.24);box-shadow:inset 0 0 0 1px rgba(77,55,29,.16);opacity:.85}
    .topic-tile:hover,.topic-tile:focus-visible{outline:none;transform:translateY(-2px);border-color:rgba(145,108,49,.75);box-shadow:0 0 0 4px rgba(216,191,138,.2),0 16px 28px rgba(86,63,32,.22),inset 0 2px 0 rgba(255,255,255,.32),inset 0 -14px 18px rgba(86,63,32,.3);filter:saturate(1.04)}
    .topic-tile.active{background:linear-gradient(180deg,#e5c98f,#b78d48);box-shadow:0 0 0 5px rgba(216,191,138,.26),0 18px 34px rgba(86,63,32,.26),inset 0 2px 0 rgba(255,255,255,.3),inset 0 -14px 18px rgba(86,63,32,.32)}.tablet h2,.tablet h3,.tablet p{background:rgba(253,248,238,.18);box-decoration-break:clone;padding:0 .12em;border-radius:6px}.report-head h2,.report-head p,.section h3{background:rgba(255,250,242,.18);box-decoration-break:clone;padding:0 .08em;border-radius:5px}.topic-name{font-family:Georgia,serif;font-size:1.03rem;font-weight:700;text-shadow:0 1px 0 rgba(255,247,232,.24)}.topic-meta{font-size:.72rem;text-transform:uppercase;letter-spacing:.12em;color:#5f4a2e}
    .custom-panel{display:none;gap:10px;margin-top:14px;padding:14px;border-radius:18px;background:rgba(255,248,235,.24);border:1px solid rgba(109,82,47,.14);box-shadow:inset 0 1px 0 rgba(255,255,255,.18)}.custom-panel.active{display:grid}.custom-panel label{font-size:.78rem;text-transform:uppercase;letter-spacing:.16em;color:#7b643e;font-weight:700}.custom-panel input{width:100%;padding:13px 14px;border-radius:14px;border:1px solid rgba(109,82,47,.26);background:linear-gradient(180deg,#faf4e8,#efe4ce);font-size:1rem;box-shadow:inset 0 1px 2px rgba(92,68,37,.08)}
    .invoke-row{display:flex;justify-content:space-between;align-items:center;gap:14px;margin-top:16px;flex-wrap:wrap}.readout-label{display:block;font-size:.72rem;text-transform:uppercase;letter-spacing:.16em;color:#7b643e;font-weight:700}.readout-value{display:block;margin-top:4px;font-family:Georgia,serif;font-size:1.15rem;font-weight:700}.invoke-btn{appearance:none;border:1px solid rgba(109,82,47,.24);border-radius:999px;padding:15px 24px;min-width:220px;background:linear-gradient(90deg,#70522a,#c39b56 52%,#e7d3a2);color:#fff9ed;font-family:Georgia,serif;font-size:1rem;letter-spacing:.06em;cursor:pointer;box-shadow:0 14px 28px rgba(109,74,26,.22),inset 0 1px 0 rgba(255,255,255,.22)}.invoke-btn:disabled{opacity:.72;cursor:not-allowed}
    .status{min-height:24px;margin-top:16px;color:var(--muted)}.status.error{color:var(--danger)}.status.success{color:#5e4d31}
    .report-shell{display:none;margin-top:16px;border-radius:22px;overflow:hidden;background:radial-gradient(circle at 18% 10%,rgba(255,247,232,.42),transparent 20%),radial-gradient(circle at 84% 18%,rgba(176,132,74,.12),transparent 22%),linear-gradient(180deg,rgba(244,232,210,.94),rgba(232,216,188,.97));border:1px solid rgba(109,82,47,.18);box-shadow:inset 0 1px 0 rgba(255,255,255,.26),inset 0 -12px 20px rgba(101,75,42,.1),0 10px 22px rgba(78,56,29,.08)}.tablet.revealed .report-shell{display:block;animation:rise .24s ease}.report-head{display:flex;justify-content:space-between;align-items:end;gap:16px;padding:18px 20px;border-bottom:1px solid rgba(109,82,47,.14);background:linear-gradient(180deg,rgba(255,248,234,.32),rgba(198,167,120,.08))}.report-kicker{margin:0 0 6px;font-size:.72rem;text-transform:uppercase;letter-spacing:.18em;color:#7b643e;font-weight:700}.report-head h2{margin:0;font-family:Georgia,serif;font-size:clamp(1.4rem,2vw,1.95rem);color:#2d2217;line-height:1.15}.report-head p{margin:6px 0 0;color:#584933;line-height:1.6;max-width:54ch}.report-marker{padding:8px 12px;border-radius:999px;border:1px solid rgba(109,82,47,.16);background:rgba(255,247,233,.34);font-size:.72rem;letter-spacing:.16em;text-transform:uppercase;color:#7b643e;font-weight:700;white-space:nowrap}.report{padding:20px}.placeholder{color:#5d503d;font-style:italic}.section{margin:0 0 20px;padding:18px;border-radius:18px;background:linear-gradient(180deg,rgba(248,241,229,.58),rgba(238,226,203,.72));border:1px solid rgba(109,82,47,.12);box-shadow:inset 0 1px 0 rgba(255,255,255,.26),inset 0 -8px 14px rgba(101,75,42,.05)}.section h3{margin:0 0 12px;font-family:Georgia,serif;font-size:1rem;text-transform:uppercase;letter-spacing:.08em;display:flex;gap:10px;align-items:center;color:#34281c}.section h3 .prefix{display:inline-flex;align-items:center;justify-content:center;min-width:1.6em;height:1.6em;border-radius:999px;background:rgba(197,161,95,.22);border:1px solid rgba(109,82,47,.16);font-size:.78rem;color:#71552d;font-weight:700}.section ul{margin:0;padding-left:20px}.section li{margin:10px 0;line-height:1.68;color:#3f3428}.section.sources a{color:#523c1d;text-decoration:none;border-bottom:1px solid rgba(82,60,29,.34)}.section.sources a:hover{border-bottom-color:rgba(82,60,29,.62)}.error-box{color:var(--danger);background:rgba(143,58,43,.08);border:1px solid rgba(143,58,43,.18);border-radius:12px;padding:10px 12px}
    .loading-ritual{display:grid;justify-items:center;gap:14px;padding:20px 14px;text-align:center}
    .loading-glyph{position:relative;width:74px;height:74px;border-radius:50%;border:1px solid rgba(109,82,47,.22);background:radial-gradient(circle at 36% 34%,rgba(255,248,230,.78),rgba(216,188,138,.92) 44%,rgba(140,103,53,.94) 100%);box-shadow:inset 0 2px 0 rgba(255,255,255,.34),inset 0 -10px 14px rgba(83,60,31,.28),0 12px 26px rgba(92,67,35,.14)}
    .loading-glyph:before,.loading-glyph:after{content:"";position:absolute;inset:12px;border-radius:50%;border:1px solid rgba(92,67,35,.22)}
    .loading-glyph:before{border-top-color:rgba(255,248,230,.88);border-bottom-color:rgba(92,67,35,.44);animation:tablet-spin 2.8s linear infinite}
    .loading-glyph:after{inset:24px;background:radial-gradient(circle,rgba(255,250,238,.9) 0 18%,rgba(197,161,95,.4) 19% 46%,transparent 47% 100%);box-shadow:0 0 0 1px rgba(109,82,47,.12)}
    .loading-copy{max-width:34ch;color:var(--muted);line-height:1.65}
    @keyframes tablet-spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}
    @keyframes rise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}@media (max-width:980px){.stage{grid-template-columns:1fr}.tablet{padding:28px 26px 30px 32px;clip-path:polygon(.6% 5.2%,2.8% 1.6%,7.8% 0%,84% 0%,91% 2.2%,96.5% 6.2%,99.2% 13%,99.2% 87%,96% 94%,91% 100%,10% 100%,3.5% 97%,.6% 91%)}}@media (max-width:760px){.shell{padding:24px 14px 40px}.masthead,.tablet-head,.report-head,.invoke-row{flex-direction:column;align-items:stretch}.tablet{padding:26px 20px 28px 24px;clip-path:polygon(.4% 4.4%,2.2% 1.2%,6.2% 0%,88% 0%,94% 2.8%,98.8% 7%,99.2% 92%,95.5% 98%,10% 100%,3.2% 97%,.4% 90.5%,.4% 10%)}.tablet:before{inset:8px 7px}.topic-grid{grid-template-columns:1fr}.invoke-btn{width:100%}.sigil{align-self:flex-start}}
  </style>
</head>
<body>
  <div class="shell">
    <header class="masthead">
      <div>
        <div class="kicker">Metis Intelligence</div>
        <h1>Oracle Tablet for High-Signal Discovery</h1>
        <p>Direction B reframes the experience as a single artifact: engraved topic selection, ritualized invocation, then a revealed bulletin within the same tablet shell.</p>
        <div class="caption">Single artifact, multi-state interface</div>
      </div>
      <div class="sigil" aria-hidden="true"></div>
    </header>
    <main class="stage">
      <section class="tablet" id="tablet" aria-label="Metis tablet interface">
        <div class="tablet-head">
          <div>
            <h2><span class="inscription">Tablet of Inquiry</span></h2>
            <p><span class="inscription sub">Select a domain inscription, invoke synthesis, and let the bulletin emerge without a jarring page change.</span></p>
          </div>
          <div class="state-pill" id="statePill">Inquiry State</div>
        </div>
        <div class="selection">
          <h3><span class="inscription">Choose the domain inscription</span></h3>
          <p><span class="inscription sub">Each tile stands in for a research path. The custom domain route becomes explicit instead of living as a generic second field.</span></p>
          <div class="topic-grid" id="topicGrid">
            <button class="topic-tile" type="button" data-domain-id="1"><span class="topic-name">AI Infrastructure</span><span class="topic-meta">Foundational systems</span></button>
            <button class="topic-tile" type="button" data-domain-id="2"><span class="topic-name">Cybersecurity and Zero Trust</span><span class="topic-meta">Defensive posture</span></button>
            <button class="topic-tile" type="button" data-domain-id="3"><span class="topic-name">Edge Computing</span><span class="topic-meta">Distributed compute</span></button>
            <button class="topic-tile" type="button" data-domain-id="4"><span class="topic-name">Sustainable Tech</span><span class="topic-meta">Energy and efficiency</span></button>
            <button class="topic-tile" type="button" data-domain-id="5"><span class="topic-name">FinTech and DeFi</span><span class="topic-meta">Capital systems</span></button>
            <button class="topic-tile" type="button" data-domain-id="6"><span class="topic-name">BioTech and HealthTech</span><span class="topic-meta">Life sciences</span></button>
            <button class="topic-tile" type="button" data-domain-id="7"><span class="topic-name">AI Robotics</span><span class="topic-meta">Embodied intelligence</span></button>
            <button class="topic-tile" type="button" data-domain-id="8"><span class="topic-name">Crypto and Digital Currency</span><span class="topic-meta">Networked assets</span></button>
            <button class="topic-tile" type="button" data-domain-id="9"><span class="topic-name">Custom Domain</span><span class="topic-meta">Named invocation</span></button>
          </div>
          <div class="custom-panel" id="customPanel">
            <label for="customDomain">Name the custom domain</label>
            <input id="customDomain" placeholder="Enter a custom research domain" />
          </div>
          <div class="invoke-row">
            <div><span class="readout-label">Current inscription</span><span class="readout-value" id="selectionValue">No inscription selected</span></div>
            <button id="runBtn" class="invoke-btn" type="button" disabled>Invoke Insight</button>
          </div>
        </div>
        <div id="status" class="status">Awaiting invocation.</div>
        <div class="report-shell" id="reportShell">
          <div class="report-head">
            <div>
              <div class="report-kicker">Revealed Bulletin</div>
              <h2 id="reportTitle">Final High-Signal Report</h2>
              <p>The shell remains mythic, while the reading surface stays calm enough for real scanning.</p>
            </div>
            <div class="report-marker" id="reportMarker">Oracle Output</div>
          </div>
          <div id="reportRoot" class="report"><div class="placeholder">Invoke a topic to reveal the bulletin.</div></div>
        </div>
      </section>
    </main>
  </div>
  <script>
    const runBtn=document.getElementById("runBtn"),tablet=document.getElementById("tablet"),topicTiles=Array.from(document.querySelectorAll(".topic-tile")),customPanel=document.getElementById("customPanel"),customDomain=document.getElementById("customDomain"),statusEl=document.getElementById("status"),selectionValue=document.getElementById("selectionValue"),statePill=document.getElementById("statePill"),reportTitle=document.getElementById("reportTitle"),reportMarker=document.getElementById("reportMarker"),reportRoot=document.getElementById("reportRoot");
    const domainNames={"1":"AI Infrastructure","2":"Cybersecurity and Zero Trust","3":"Edge Computing","4":"Sustainable Tech","5":"FinTech and DeFi","6":"BioTech and HealthTech","7":"AI Robotics","8":"Crypto and Digital Currency","9":"Custom Domain"};
    let selectedDomainId="",lastStyleHint="";
    function escapeHtml(text){return text.replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;")}
    function sectionThemeFromHint(styleHint){const s=(styleHint||"").toLowerCase(),m=s.match(/icon density:\\s*(low|medium|high)/),d=m?m[1]:"medium",rich=d==="high",lean=d==="low";if(s.includes("security"))return{executive:rich?"III":lean?"I":"II",signals:rich?"SIG":lean?"S":"SI",risks:rich?"RIII":lean?"R":"RII",actions:rich?"AIII":lean?"A":"AII",sources:"SRC"};if(s.includes("infra")||s.includes("llm")||s.includes("gpu"))return{executive:rich?"ARC":lean?"A":"AR",signals:rich?"ION":lean?"I":"IO",risks:rich?"RSK":lean?"R":"RK",actions:rich?"ACT":lean?"A":"AC",sources:"SRC"};if(s.includes("sustainability")||s.includes("carbon")||s.includes("green"))return{executive:rich?"VER":lean?"V":"VE",signals:rich?"GRN":lean?"G":"GN",risks:rich?"RTH":lean?"R":"RT",actions:rich?"SED":lean?"S":"SD",sources:"SRC"};return{executive:rich?"I":"IN",signals:rich?"II":"SI",risks:rich?"III":"RI",actions:rich?"IV":"AC",sources:"V"}}
    function headingPrefix(title,styleHint){const t=title.toLowerCase(),themed=sectionThemeFromHint(styleHint||"");if(t==="executive snapshot")return themed.executive;if(t==="key signals")return themed.signals;if(t==="risks / unknowns")return themed.risks;if(t==="recommended actions")return themed.actions;if(t==="sources")return themed.sources;return ""}
    function renderMarkdownReport(report){const lines=report.split("\\n"),sections=[];let current=null;for(const raw of lines){const line=raw.trim();if(line.startsWith("## ")){if(current)sections.push(current);current={title:line.replace(/^##\\s+/,""),items:[]};continue}if(line.startsWith("- ")){if(!current)continue;current.items.push(line.replace(/^-\\s+/,""))}}if(current)sections.push(current);if(!sections.length)return `<pre>${escapeHtml(report)}</pre>`;return sections.map((section)=>{const isSources=section.title.toLowerCase()==="sources",cls=isSources?"section sources":"section",prefix=headingPrefix(section.title,lastStyleHint),heading=prefix?`<span class="prefix" aria-hidden="true">${escapeHtml(prefix)}</span><span>${escapeHtml(section.title)}</span>`:`<span>${escapeHtml(section.title)}</span>`,items=section.items.length?section.items.map((item)=>{if(isSources){const m=item.match(/^\\[([^\\]]+)\\]\\((https?:\\/\\/[^)]+)\\)$/);if(m){return `<li><a href="${m[2]}" target="_blank" rel="noopener noreferrer">${escapeHtml(m[1])}</a></li>`}}return `<li>${escapeHtml(item)}</li>`}).join(""):"<li>N/A</li>";return `<section class="${cls}"><h3>${heading}</h3><ul>${items}</ul></section>`}).join("")}
    function setStatus(message,type=""){statusEl.className=`status${type?` ${type}`:""}`;statusEl.textContent=message}
    function loadingMarkup(){return '<div class="loading-ritual"><div class="loading-glyph" aria-hidden="true"></div><div class="loading-copy">The tablet is aligning fragments into a readable bulletin.</div></div>'}
    function syncInvocationState(){const customReady=selectedDomainId==="9"?Boolean(customDomain.value.trim()):true;runBtn.disabled=!selectedDomainId||!customReady}
    function setSelectedDomain(id){selectedDomainId=id||"";topicTiles.forEach((tile)=>tile.classList.toggle("active",tile.dataset.domainId===selectedDomainId));customPanel.classList.toggle("active",selectedDomainId==="9");if(selectedDomainId!=="9")customDomain.value="";selectionValue.textContent=!selectedDomainId?"No inscription selected":selectedDomainId==="9"?(customDomain.value.trim()||"Custom Domain"):domainNames[selectedDomainId];syncInvocationState()}
    async function runResearch(){const id=selectedDomainId,custom=customDomain.value.trim();if(!id){setStatus("Choose an inscription before invocation.","error");return}if(id==="9"&&!custom){setStatus("Custom domain is required before invocation.","error");return}runBtn.disabled=true;statePill.textContent="Invocation State";reportMarker.textContent="Tablet Aligning";tablet.classList.add("revealed");reportRoot.innerHTML=loadingMarkup();setStatus("Metis is synthesizing the inscription into a revealed bulletin...");try{const res=await fetch("/research",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({domain_id:id,custom_domain:id==="9"?custom:null})}),data=await res.json();if(!res.ok)throw new Error(data.detail||"Request failed");lastStyleHint=data.style_hint||"";reportTitle.textContent=`Final High-Signal Report - ${data.domain}`;reportRoot.innerHTML=renderMarkdownReport(data.report||"");reportMarker.textContent="Oracle Output";statePill.textContent="Revealed State";tablet.classList.add("revealed");setStatus("The bulletin has been revealed.","success")}catch(err){lastStyleHint="";statePill.textContent="Inquiry State";reportMarker.textContent="Invocation Failed";reportRoot.innerHTML='<div class="error-box">No report available. Adjust the topic and try again.</div>';setStatus(`Error: ${String(err.message||err)}`,"error")}finally{syncInvocationState()}}
    topicTiles.forEach((tile)=>tile.addEventListener("click",()=>setSelectedDomain(tile.dataset.domainId)));customDomain.addEventListener("input",()=>{if(selectedDomainId==="9")selectionValue.textContent=customDomain.value.trim()||"Custom Domain";syncInvocationState()});runBtn.addEventListener("click",runResearch);setSelectedDomain("");
  </script>
</body>
</html>
"""

@app.get("/domains")
def get_domains():
    return {key: name for key, (name, _) in DOMAIN_PERSONAS.items()}

@app.post("/research")
def run_research(request: ResearchRequest):
    """
    Run the Metis trend-to-content process.
    """
    domain_id = request.domain_id
    custom_domain = request.custom_domain
    
    if domain_id not in DOMAIN_PERSONAS:
        raise HTTPException(status_code=400, detail="Invalid domain ID")

    topic = DOMAIN_PERSONAS.get(domain_id, DOMAIN_PERSONAS["9"])[0]
    if domain_id == "9":
        if not custom_domain:
            raise HTTPException(status_code=400, detail="Custom domain is required for domain_id '9'")
        topic = custom_domain

    # Initialize the Metis Orchestrator only after request validation passes.
    metis = get_metis_orchestrator(domain_id, custom_domain)

    # Run the orchestration process
    response = metis.ask(f"Discover high-signal trends in {topic} and draft a synthesis report.")
    report_text = response if isinstance(response, str) else response.text
    
    return {
        "domain": topic,
        "report": report_text,
        "style_hint": (
            f"{getattr(metis, 'style_profile', '')} "
            f"Grader icon density: {getattr(metis, 'last_icon_density', 'medium')}."
        ).strip()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))




