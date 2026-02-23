import { useState, useEffect } from "react";
import { Rss, Search, Loader2, X, ExternalLink } from "lucide-react";
import PageShell from "./components/PageShell.jsx";
import Card from "./components/Card.jsx";

const CHECK_META = {
  reachable:  "Reachable",
  parseable:  "Valid RSS/Atom",
  has_dates:  "Entry timestamps",
  scrapeable: "Article scraping",
};

function CheckIcon({ ok }) {
  return ok ? (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <circle cx="8" cy="8" r="7.25" stroke="#22c55e" strokeWidth="1.5" />
      <path d="M5 8.5l2 2 4-4" stroke="#22c55e" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ) : (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path d="M8 1.5L14.5 13.5H1.5L8 1.5Z" stroke="#f59e0b" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M8 6.5v3" stroke="#f59e0b" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="8" cy="11" r="0.75" fill="#f59e0b" />
    </svg>
  );
}

function OverallBadge({ status }) {
  const cfg = {
    ok:      { stroke: "#22c55e", color: "#22c55e",  label: "Fully supported"      },
    partial: { stroke: "#f59e0b", color: "#b45309",  label: "Partially supported"  },
    error:   { stroke: "#ef4444", color: "#ef4444",  label: "Not supported"        },
  }[status] || { stroke: "#c7c7cc", color: "#86868b", label: "Unknown" };

  const isOk = status === "ok";
  return (
    <div className="flex items-center gap-2">
      <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
        {isOk ? (
          <>
            <circle cx="11" cy="11" r="10.25" stroke={cfg.stroke} strokeWidth="1.5" />
            <path d="M6.5 11.5l3 3 6-6" stroke={cfg.stroke} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </>
        ) : (
          <>
            <path d="M11 2L20.5 19H1.5L11 2Z" stroke={cfg.stroke} strokeWidth="1.5" strokeLinejoin="round" />
            <path d="M11 9v4" stroke={cfg.stroke} strokeWidth="1.5" strokeLinecap="round" />
            <circle cx="11" cy="15.5" r="1" fill={cfg.stroke} />
          </>
        )}
      </svg>
      <span className="text-[13px] font-medium" style={{ color: cfg.color }}>{cfg.label}</span>
    </div>
  );
}

export default function FeedValidator() {
  const getUrlParam = () => {
    const hash  = window.location.hash;
    const query = hash.includes("?") ? hash.split("?")[1] : "";
    return decodeURIComponent(new URLSearchParams(query).get("url") || "");
  };

  const [url, setUrl]       = useState(getUrlParam);
  const [phase, setPhase]   = useState("idle");
  const [report, setReport] = useState(null);
  const [errMsg, setErrMsg] = useState("");

  const validate = async (targetUrl) => {
    const val = (targetUrl ?? url).trim();
    if (!val || phase === "loading") return;
    try { new URL(val); } catch { setErrMsg("Enter a valid URL."); setPhase("error"); return; }

    setPhase("loading");
    setReport(null);
    setErrMsg("");

    try {
      const res  = await fetch("/api/validate", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ url: val }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Validation failed");
      setReport(data);
      setPhase("done");
    } catch (err) {
      setErrMsg(err.message);
      setPhase("error");
    }
  };

  useEffect(() => {
    const prefilled = getUrlParam();
    if (prefilled) { setUrl(prefilled); validate(prefilled); }
  }, []); // eslint-disable-line

  const reset = () => { setPhase("idle"); setReport(null); setErrMsg(""); setUrl(""); };

  return (
    <PageShell active="Validator">
      {/* Hero */}
      <section className="z-[1] text-center pt-20 pb-12 px-8 max-w-[540px] mx-auto animate-fade-up">
        <p className="text-[12px] font-medium tracking-[0.08em] text-[#86868b] uppercase mb-4">Compatibility check</p>
        <h1 className="text-[clamp(32px,4.5vw,50px)] font-semibold leading-[1.08] tracking-[-0.03em] text-[#1d1d1f] mb-4">
          Will your feed<br /><span className="font-light text-[#6e6e73]">work with Digest?</span>
        </h1>
        <p className="text-[15px] text-[#6e6e73] leading-relaxed">Paste an RSS or Atom URL to check compatibility.</p>
      </section>

      {/* Card */}
      <main className="z-[1] w-full max-w-[560px] px-6 pb-24 mx-auto animate-fade-up-delay">
        <Card>
          {/* Input row */}
          <div className="p-5 border-b border-black/[0.06]">
            <div className="flex gap-2">
              <div className="flex-1 flex items-center gap-2 bg-[#f5f5f7] border border-black/[0.12] rounded-[12px] px-3 py-[10px]">
                <Rss size={13} className="text-[#86868b] flex-shrink-0" />
                <input
                  value={url}
                  onChange={e => { setUrl(e.target.value); if (phase === "error") setPhase("idle"); }}
                  onKeyDown={e => e.key === "Enter" && validate()}
                  placeholder="https://example.com/feed.xml"
                  className="flex-1 bg-transparent border-none text-[13px] text-[#1d1d1f]"
                  style={{ fontFamily: "inherit" }}
                />
                {url && (
                  <button onClick={reset} className="text-[#c7c7cc] hover:text-[#86868b] transition-colors flex-shrink-0">
                    <X size={12} />
                  </button>
                )}
              </div>
              <button onClick={() => validate()} disabled={!url.trim() || phase === "loading"}
                className="px-4 rounded-[12px] bg-[#1d1d1f] hover:bg-[#3a3a3c] text-white text-[13px] font-medium flex items-center gap-[6px] transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex-shrink-0">
                {phase === "loading" ? <Loader2 size={13} style={{ animation: "spin 1s linear infinite" }} /> : <Search size={13} />}
                {phase === "loading" ? "Checking" : "Check"}
              </button>
            </div>
            {phase === "error" && errMsg && (
              <p className="text-[11px] text-[#ef4444] mt-2 pl-1">{errMsg}</p>
            )}
          </div>

          {/* Idle — what we check */}
          {phase === "idle" && (
            <div className="px-5 py-6 flex flex-col gap-[10px]">
              {Object.values(CHECK_META).map(label => (
                <div key={label} className="flex items-center gap-3">
                  <div className="w-[5px] h-[5px] rounded-full bg-[#d4d4d8] flex-shrink-0" />
                  <span className="text-[13px] text-[#86868b]">{label}</span>
                </div>
              ))}
            </div>
          )}

          {/* Loading skeleton */}
          {phase === "loading" && (
            <div className="px-5 py-6 flex flex-col gap-[10px]">
              {[100, 120, 90, 110].map((w, i) => (
                <div key={i} className="flex items-center gap-3">
                  <div className="w-4 h-4 rounded-full bg-black/[0.06] flex-shrink-0" style={{ animation: `pulse 1.4s ease-in-out ${i * 0.15}s infinite` }} />
                  <div className="h-[13px] rounded-full bg-black/[0.05] flex-shrink-0" style={{ width: w, animation: `pulse 1.4s ease-in-out ${i * 0.15}s infinite` }} />
                </div>
              ))}
            </div>
          )}

          {/* Results */}
          {phase === "done" && report && (
            <div>
              {/* Check rows */}
              <div className="px-5 pt-5 pb-2 flex flex-col gap-[2px]">
                {Object.entries(report.checks).map(([id, check]) => (
                  <div key={id} className="flex items-center justify-between py-[9px] border-b border-black/[0.05] last:border-0">
                    <div className="flex items-center gap-3">
                      <CheckIcon ok={check.ok} />
                      <span className="text-[13px] font-medium text-[#1d1d1f]">{CHECK_META[id]}</span>
                    </div>
                    <span className="text-[11px] text-[#86868b] text-right max-w-[200px] truncate">{check.detail}</span>
                  </div>
                ))}
              </div>

              {/* Overall verdict */}
              <div className="mx-5 my-3 px-4 py-3 rounded-[12px] bg-[#f5f5f7] border border-black/[0.06] flex items-center justify-between">
                <OverallBadge status={report.status} />
                {report.status === "ok" && <span className="text-[11px] text-[#86868b]">Ready to use</span>}
              </div>

              {/* Sample article */}
              {report.sample_article && (
                <div className="mx-5 mb-5 rounded-[12px] border border-black/[0.07] overflow-hidden">
                  {report.sample_article.image && (
                    <div className="h-24 overflow-hidden">
                      <img src={report.sample_article.image} alt="" className="w-full h-full object-cover" />
                    </div>
                  )}
                  <div className="p-4">
                    <p className="text-[10px] font-semibold tracking-[0.07em] uppercase text-[#86868b] mb-[6px]">Sample article</p>
                    <p className="text-[13px] font-medium text-[#1d1d1f] leading-snug mb-2 line-clamp-2">{report.sample_article.title}</p>
                    <p className="text-[12px] text-[#6e6e73] leading-relaxed line-clamp-3 mb-3">{report.sample_article.summary}</p>
                    <a href={report.sample_article.url} target="_blank" rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-[11px] text-[#86868b] hover:text-[#1d1d1f] transition-colors">
                      Open article <ExternalLink size={10} />
                    </a>
                  </div>
                </div>
              )}

              {/* Reset */}
              <div className="px-5 pb-5">
                <button onClick={reset}
                  className="w-full py-[10px] rounded-[12px] bg-black/[0.04] hover:bg-black/[0.08] text-[#3a3a3c] text-[13px] font-medium transition-colors">
                  Check another feed
                </button>
              </div>
            </div>
          )}
        </Card>
      </main>
    </PageShell>
  );
}
