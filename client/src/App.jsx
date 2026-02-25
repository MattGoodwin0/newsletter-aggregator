import { useState, useRef, useEffect } from "react";
import {
  Plus,
  X,
  Download,
  Rss,
  ChevronRight,
  Check,
  AlertCircle,
} from "lucide-react";
import PageShell from "./components/PageShell.jsx";
import Card from "./components/Card.jsx";
import ProgressRing from "./components/ProgressRing.jsx";
import FeedStatusIcon from "./components/FeedStatusIcon.jsx";
import { post, get } from "./api.js";

const PRESETS = [
  {
    label: "Technology",
    feeds: [
      "https://techcrunch.com/feed/",
      "https://www.theverge.com/rss/index.xml",
      "https://www.wired.com/feed/rss",
    ],
  },
  // {
  //   label: "Science",
  //   feeds: [
  //     "https://www.nasa.gov/rss/dyn/breaking_news.rss",
  //     "https://www.sciencedaily.com/rss/top/science.xml",
  //   ],
  // },
  {
    label: "Product",
    feeds: [
      "https://www.producttalk.org/feed/",
      "https://www.productleadership.com/feed/",
    ],
  },
  {
    label: "Custom",
    feeds: [],
  },
];

const STEPS = [
  { id: "fetch", label: "Fetching sources" },
  { id: "scrape", label: "Extracting content" },
  { id: "nlp", label: "Analysing articles" },
  { id: "render", label: "Composing layout" },
  { id: "pdf", label: "Generating PDF" },
];

function SummaryRow({ label, value, last }) {
  return (
    <div
      className={`flex justify-between items-center px-4 py-3 ${!last ? "border-b border-black/[0.06]" : ""}`}
    >
      <span className="text-[13px] text-[#86868b]">{label}</span>
      <span className="text-[13px] text-[#1d1d1f] font-medium">{value}</span>
    </div>
  );
}

export default function App() {
  const [feeds, setFeeds] = useState([
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/index.xml",
  ]);
  const [feedStatuses, setFeedStatuses] = useState({});
  const [inputVal, setInputVal] = useState("");
  const [inputError, setInputError] = useState(false);
  const [daysBack, setDaysBack] = useState(7);
  const [status, setStatus] = useState("idle");
  const [stepIndex, setStepIndex] = useState(-1);
  const [doneSteps, setDoneSteps] = useState([]);
  const [errorMsg, setErrorMsg] = useState("");
  const [pdfUrl, setPdfUrl] = useState(null);
  const [valid, setValid] = useState(false);
  const [siteHealth, setSiteHealth] = useState(true);
  const inputRef = useRef(null);

  const progressPct =
    status === "done"
      ? 100
      : Math.round((doneSteps.length / STEPS.length) * 100);

  // ── Feed validation ─────────────────────────────────────────────────────────
  const validateFeed = async (url) => {
    setFeedStatuses((s) => ({ ...s, [url]: "checking" }));
    try {
      const res = await post("/api/validate", { url });
      const data = await res.json();
      setFeedStatuses((s) => ({ ...s, [url]: res.ok ? data.status : "error" }));
    } catch {
      setFeedStatuses((s) => ({ ...s, [url]: "error" }));
    }

    if (Object.values(feedStatuses).every((s) => s === "valid")) {
      setValid(true);
    }
  };

  useEffect(() => {
    feeds.forEach(validateFeed);
  }, []); // eslint-disable-line

  useEffect(() => {
    const res = get("/api/health")
      .then((r) => {
        if (r.status !== 200) return r.json();
      })
      .catch(() => ({ healthy: false }));
    res.then((data) => setSiteHealth(data.healthy));
  }, []); // eslint-disable-line

  // ── Feed management ─────────────────────────────────────────────────────────
  const addFeed = () => {
    const val = inputVal.trim();
    if (!val) return;
    try {
      new URL(val);
    } catch {
      setInputError(true);
      return;
    }
    if (feeds.includes(val)) {
      setInputVal("");
      return;
    }
    setFeeds((f) => [...f, val]);
    setInputVal("");
    setInputError(false);
    inputRef.current?.focus();
    validateFeed(val);
  };

  const removeFeed = (i) => setFeeds((f) => f.filter((_, idx) => idx !== i));

  // ── PDF generation ──────────────────────────────────────────────────────────
  const generate = async () => {
    if (!feeds.length || status === "running") return;
    setStatus("running");
    setDoneSteps([]);
    setStepIndex(0);
    setErrorMsg("");
    setPdfUrl(null);

    let stepTimer;
    let currentStep = 0;
    const advanceStep = () => {
      if (currentStep < STEPS.length - 1) {
        setDoneSteps((d) => [...d, STEPS[currentStep].id]);
        currentStep += 1;
        setStepIndex(currentStep);
        stepTimer = setTimeout(advanceStep, 1800 + Math.random() * 600);
      }
    };
    stepTimer = setTimeout(advanceStep, 1400);

    try {
      const res = await post("/api/generate", { feeds, days_back: daysBack });

      clearTimeout(stepTimer);
      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: res.statusText }));
        throw new Error(err.error || "Request failed");
      }
      setDoneSteps(STEPS.map((s) => s.id));
      setStepIndex(-1);
      setPdfUrl(URL.createObjectURL(await res.blob()));
      setStatus("done");
    } catch (err) {
      clearTimeout(stepTimer);
      setErrorMsg(err.message || "An unexpected error occurred.");
      setStatus("error");
      setStepIndex(-1);
    }
  };

  const reset = () => {
    if (pdfUrl) URL.revokeObjectURL(pdfUrl);
    setStatus("idle");
    setDoneSteps([]);
    setPdfUrl(null);
    setErrorMsg("");
    setStepIndex(-1);
  };

  return (
    <PageShell>
      {/* Hero */}
      <section className="z-[1] text-center pt-20 pb-12 px-8 max-w-[600px] mx-auto animate-fade-up">
        <p className="text-[12px] font-medium tracking-[0.08em] text-[#86868b] uppercase mb-4">
          RSS to PDF · Automated
        </p>
        <h1 className="text-[clamp(36px,5vw,56px)] font-semibold leading-[1.08] tracking-[-0.03em] text-[#1d1d1f] mb-[18px]">
          Your feeds.
          <br />
          <span className="font-light text-[#6e6e73]">Your magazine.</span>
        </h1>
        <p className="text-[16px] leading-relaxed text-[#6e6e73] tracking-[-0.01em]">
          Add any RSS sources, set your timeframe,
          <br />
          and receive a beautifully composed PDF digest.
        </p>
      </section>
      {!siteHealth ? (
        <main className="z-[1] max-w-[1280px] px-6 pb-20 mx-auto animate-fade-up-delay">
          <div className="text-center py-12">
            <p className="text-[14px] text-[#ff3b30] font-medium">
              Oops. We look to be down. We're working on a fix — please check
              back soon!
            </p>
          </div>
        </main>
      ) : (
        <main className="z-[1] max-w-[1280px] px-6 pb-20 mx-auto animate-fade-up-delay">
          <Card
            className="
    grid
    grid-cols-1
    md:grid-cols-[1fr_0.5px_1fr]
    min-h-[480px]
  "
          >
            {/* ── Left: sources + timeframe ── */}
            <div className="p-4 md:p-9">
              <p className="text-[11px] font-semibold tracking-[0.08em] uppercase text-[#86868b] mb-[14px]">
                Sources
              </p>

              {/* Presets */}
              <div className="flex gap-[6px] flex-wrap mb-4">
                {PRESETS.map((p) => (
                  <button
                    key={p.label}
                    onClick={() => {
                      setFeeds(p.feeds);
                      p.feeds.forEach(validateFeed);
                    }}
                    className="text-[12px] text-[#1d1d1f] bg-black/[0.03] border border-black/10 rounded-full px-3 py-[5px] hover:bg-black/[0.06] transition-colors"
                  >
                    {p.label}
                  </button>
                ))}
              </div>

              {/* URL input */}
              <div
                className={`flex items-center gap-2 bg-[#f5f5f7] rounded-[10px] px-[10px] py-2 mb-1 border ${inputError ? "border-[#ff3b30]" : "border-black/[0.12]"}`}
              >
                <Rss
                  size={13}
                  className={inputError ? "text-[#ff3b30]" : "text-[#86868b]"}
                />
                <input
                  ref={inputRef}
                  value={inputVal}
                  onChange={(e) => {
                    setInputVal(e.target.value);
                    setInputError(false);
                  }}
                  onKeyDown={(e) => e.key === "Enter" && addFeed()}
                  placeholder="https://example.com/feed.xml"
                  className="flex-1 bg-transparent border-none text-[12px] text-[#1d1d1f]"
                  style={{ fontFamily: "inherit" }}
                />
                <button
                  onClick={addFeed}
                  className="w-[26px] h-[26px] rounded-[7px] bg-[#3a3a3c] hover:bg-[#1d1d1f] text-white flex items-center justify-center flex-shrink-0 transition-colors"
                >
                  <Plus size={13} />
                </button>
              </div>
              {inputError && (
                <p className="text-[11px] text-[#ff3b30] mb-2 pl-[2px]">
                  Please enter a valid URL
                </p>
              )}

              {/* Feed pills */}
              <div className="flex flex-col gap-[6px] mt-[10px] min-h-[60px]">
                {feeds.length === 0 && (
                  <p className="text-[12px] text-[#c7c7cc] py-3">
                    No sources added
                  </p>
                )}
                {feeds.map((f, i) => (
                  <div
                    key={f}
                    className="flex items-center gap-[7px] bg-[#f5f5f7] border border-black/[0.08] rounded-[8px] px-[10px] py-[7px]"
                  >
                    <FeedStatusIcon status={feedStatuses[f]} url={f} />
                    <span className="flex-1 text-[11px] text-[#3a3a3c] overflow-hidden text-ellipsis whitespace-nowrap">
                      {f.replace(/^https?:\/\/(www\.)?/, "")}
                    </span>
                    <button
                      onClick={() => removeFeed(i)}
                      className="text-[#c7c7cc] hover:text-[#1d1d1f] transition-colors flex items-center p-[2px]"
                    >
                      <X size={10} />
                    </button>
                  </div>
                ))}
              </div>

              <div className="h-[0.5px] bg-black/[0.08] my-6" />

              {/* Timeframe */}
              <p className="text-[11px] font-semibold tracking-[0.08em] uppercase text-[#86868b] mb-[14px]">
                Timeframe
              </p>
              <div className="flex gap-[6px]">
                {[1, 3, 7, 14].map((d) => (
                  <button
                    key={d}
                    onClick={() => setDaysBack(d)}
                    className={`flex-1 py-2 rounded-[8px] text-[12px] transition-all border
                    ${daysBack === d ? "bg-[#1d1d1f] text-white border-[#1d1d1f]" : "bg-transparent text-[#6e6e73] border-black/10 hover:bg-black/[0.04]"}`}
                  >
                    {d === 1 ? "Today" : `${d} days`}
                  </button>
                ))}
              </div>
            </div>

            {/* Vertical divider */}
            <div className="bg-black/[0.08] self-stretch" />

            {/* ── Right: action panel ── */}
            <div className="p-4 flex items-center justify-center md:p-9">
              {status === "idle" && (
                <div className="w-full flex flex-col gap-6">
                  <div className="bg-[#f5f5f7] border border-black/[0.08] rounded-[12px] overflow-hidden">
                    <SummaryRow
                      label="Sources"
                      value={`${feeds.length} feed${feeds.length !== 1 ? "s" : ""}`}
                    />
                    <SummaryRow
                      label="Coverage"
                      value={
                        daysBack === 1 ? "Today only" : `Last ${daysBack} days`
                      }
                    />
                    <SummaryRow label="Format" value="PDF" />
                    <SummaryRow label="Output" value="Serifdigest.pdf" last />
                  </div>
                  <button
                    onClick={generate}
                    disabled={!valid}
                    className="
    w-full py-[14px] rounded-[12px] text-[14px] font-medium
    flex items-center justify-center
    bg-[#1d1d1f] text-[#f5f5f7]
    transition-colors

    hover:bg-[#3a3a3c]

    disabled:opacity-30
    disabled:cursor-not-allowed
    disabled:hover:bg-[#1d1d1f]
  "
                  >
                    Generate PDF <ChevronRight size={14} className="ml-1" />
                  </button>
                </div>
              )}

              {status === "running" && (
                <div className="flex flex-col items-center gap-7 w-full">
                  <div className="relative flex items-center justify-center">
                    <ProgressRing progress={progressPct} />
                    <div className="absolute flex items-baseline gap-[2px]">
                      <span className="text-[26px] font-light text-[#1d1d1f] tracking-[-0.04em]">
                        {progressPct}
                      </span>
                      <span className="text-[12px] text-[#86868b]">%</span>
                    </div>
                  </div>
                  <div className="flex flex-col gap-[10px] w-full">
                    {STEPS.map((step, i) => {
                      const done = doneSteps.includes(step.id);
                      const active = stepIndex === i;
                      return (
                        <div
                          key={step.id}
                          className="flex items-center gap-[10px]"
                        >
                          <div
                            className={`w-4 h-4 rounded-full flex items-center justify-center flex-shrink-0 transition-colors
                          ${done ? "bg-[#1d1d1f] text-white" : active ? "bg-black/[0.12]" : "bg-black/[0.06]"}`}
                          >
                            {done && <Check size={8} strokeWidth={3} />}
                            {active && (
                              <span
                                style={{
                                  display: "block",
                                  width: 6,
                                  height: 6,
                                  borderRadius: "50%",
                                  background: "#1d1d1f",
                                  animation: "pulse 1.2s ease-in-out infinite",
                                }}
                              />
                            )}
                          </div>
                          <span
                            className={`text-[13px] transition-colors ${done ? "text-[#1d1d1f]" : active ? "text-[#6e6e73]" : "text-[#c7c7cc]"}`}
                          >
                            {step.label}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {status === "done" && (
                <div className="flex flex-col items-center gap-2 w-full">
                  <div className="w-14 h-14 rounded-full bg-[#f0f0f0] flex items-center justify-center mb-2">
                    <Check
                      size={28}
                      className="text-[#1d1d1f]"
                      strokeWidth={1.5}
                    />
                  </div>
                  <p className="text-[17px] font-medium text-[#1d1d1f] tracking-[-0.02em]">
                    Your digest is ready
                  </p>
                  <p className="text-[12px] text-[#86868b] mb-4">
                    {feeds.length} source{feeds.length !== 1 ? "s" : ""} ·{" "}
                    {daysBack === 1 ? "today" : `${daysBack} days`} · A4
                  </p>
                  <a
                    href={pdfUrl}
                    download="Tech_Weekly_Pro.pdf"
                    className="w-full py-[13px] rounded-[12px] bg-[#1d1d1f] hover:bg-[#3a3a3c] text-[#f5f5f7] text-[13px] font-medium flex items-center justify-center transition-colors"
                  >
                    <Download size={13} className="mr-[6px]" /> Download PDF
                  </a>
                  <button
                    onClick={reset}
                    className="text-[12px] text-[#86868b] hover:text-[#1d1d1f] transition-colors py-1"
                  >
                    Start over
                  </button>
                </div>
              )}

              {status === "error" && (
                <div className="flex flex-col items-center gap-2 w-full text-center">
                  <AlertCircle
                    size={24}
                    className="text-[#ff3b30] mb-1"
                    strokeWidth={1.5}
                  />
                  <p className="text-[15px] font-medium text-[#1d1d1f]">
                    Generation failed
                  </p>
                  <p className="text-[12px] text-[#86868b] leading-relaxed mb-4">
                    {errorMsg}
                  </p>
                  <button
                    onClick={reset}
                    className="px-7 py-[11px] rounded-[10px] bg-[#1d1d1f] hover:bg-[#3a3a3c] text-[#f5f5f7] text-[13px] font-medium transition-colors"
                  >
                    Try again
                  </button>
                </div>
              )}
            </div>
          </Card>
        </main>
      )}
    </PageShell>
  );
}
