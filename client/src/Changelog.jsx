import PageShell from "./components/PageShell.jsx";
import Card from "./components/Card.jsx";

const CHANGELOG = [
  {
    version: "0.1.0",
    date: "February 2026",
    tag: "Latest",
    dark: true,
    changes: [
      {
        type: "new",
        text: "Improvements to security and API traffic",
      },
    ],
  },
  {
    version: "0.1.0",
    date: "February 2026",
    tag: "Previous",
    dark: false,
    changes: [
      {
        type: "new",
        text: "Web frontend — generator, validator, and about pages",
      },
      { type: "new", text: "Feed validator with 4-point health check" },
      { type: "new", text: "Inline feed status indicators on the generator" },
      {
        type: "new",
        text: "Deployed to Cloud with HTTPS via Let's Encrypt",
      },
    ],
  },
];

const ROADMAP = [
  {
    status: "working",
    heading: "Consume email digests",
    body: "Consume directly from your favourite email digest providers. No more copy-pasting URLs into the generator.",
  },
  {
    status: "next",
    heading: "Improved PDF layout",
    body: "A proper magazine grid — pull quotes, better image placement, section dividers, and a table of contents on the cover. Fully customisable templates so you can make it your own.",
  },
  {
    status: "planned",
    heading: "Saved feed presets",
    body: "Save and name your favourite feed combinations so you can regenerate your digest in one click.",
  },
  {
    status: "planned",
    heading: "Scheduled digests",
    body: "Set a schedule — daily, weekly, or custom — and have your digest land in your inbox automatically.",
  },
  {
    status: "planned",
    heading: "More source types",
    body: "Support for newsletters, Substack, Hacker News digests, and YouTube channel transcripts.",
  },
  {
    status: "exploring",
    heading: "AI summaries",
    body: "Optional Claude-powered summaries that distil each article into a sharper, more readable brief.",
  },
];

const TYPE_STYLES = {
  new: { dot: "bg-[#34c759]", label: "New" },
  fix: { dot: "bg-[#ff9f0a]", label: "Fix" },
};

const STATUS_STYLES = {
  working: { pill: "bg-[#34c759] text-white", label: "In progress" },
  next: { pill: "bg-[#1d1d1f] text-white", label: "Up next" },
  planned: { pill: "bg-black/[0.06] text-[#3a3a3c]", label: "Planned" },
  exploring: { pill: "bg-black/[0.04] text-[#86868b]", label: "Exploring" },
};

export default function Changelog() {
  return (
    <PageShell active="Changelog">
      {/* Hero */}
      <section className="z-[1] w-full max-w-[680px] mx-auto px-8 pt-20 pb-16 text-center animate-fade-up">
        <p className="text-[12px] font-medium tracking-[0.08em] text-[#86868b] uppercase mb-4">
          What's changed
        </p>
        <h1 className="text-[clamp(32px,4.5vw,52px)] font-semibold leading-[1.08] tracking-[-0.03em] text-[#1d1d1f] mb-5">
          Changelog
          <br />
          <span className="font-light text-[#6e6e73]">&amp; roadmap.</span>
        </h1>
        <p className="text-[16px] text-[#6e6e73] leading-relaxed max-w-[480px] mx-auto">
          A running record of what's shipped and what's coming next.
        </p>
      </section>

      <main className="z-[1] w-full max-w-[680px] mx-auto px-6 pb-24 flex flex-col gap-10 animate-fade-up-delay">
        {/* Changelog */}
        <div>
          <p className="text-[11px] font-semibold tracking-[0.08em] uppercase text-[#86868b] mb-4 px-2">
            Releases
          </p>
          <div className="flex flex-col gap-4">
            {CHANGELOG.map((release) => (
              <Card key={release.version} dark={release.dark}>
                <div className="px-8 py-7">
                  <div className="flex items-center justify-between mb-5">
                    <div className="flex items-center gap-3">
                      <span
                        className={`text-[11px] font-semibold tracking-[0.04em] px-[8px] py-[3px] rounded-full ${release.dark ? "bg-white/10 text-white" : "bg-black/[0.06] text-[#3a3a3c]"}`}
                      >
                        v{release.version}
                      </span>
                      <span
                        className={`text-[12px] ${release.dark ? "text-[#86868b]" : "text-[#86868b]"}`}
                      >
                        {release.date}
                      </span>
                    </div>
                    <span
                      className={`text-[10px] font-semibold tracking-[0.06em] uppercase px-[7px] py-[2px] rounded-full ${release.dark ? "bg-white text-[#1d1d1f]" : "bg-black/[0.05] text-[#6e6e73]"}`}
                    >
                      {release.tag}
                    </span>
                  </div>
                  <ul className="flex flex-col gap-[10px]">
                    {release.changes.map((change, i) => (
                      <li key={i} className="flex items-start gap-3">
                        <div className="flex items-center gap-[6px] flex-shrink-0 mt-[3px]">
                          <div
                            className={`w-[6px] h-[6px] rounded-full flex-shrink-0 ${TYPE_STYLES[change.type].dot}`}
                          />
                          <span
                            className={`text-[10px] font-semibold tracking-[0.04em] uppercase w-6 ${release.dark ? "text-[#86868b]" : "text-[#86868b]"}`}
                          >
                            {TYPE_STYLES[change.type].label}
                          </span>
                        </div>
                        <span
                          className={`text-[13px] leading-relaxed ${release.dark ? "text-[#e5e5ea]" : "text-[#3a3a3c]"}`}
                        >
                          {change.text}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              </Card>
            ))}
          </div>
        </div>

        {/* Roadmap */}
        <div>
          <p className="text-[11px] font-semibold tracking-[0.08em] uppercase text-[#86868b] mb-4 px-2">
            Roadmap
          </p>
          <div className="flex flex-col gap-3">
            {ROADMAP.map((item, i) => (
              <Card key={i}>
                <div className="px-8 py-6 flex items-start gap-5">
                  <span
                    className={`text-[11px] font-semibold tracking-[0.04em] px-[8px] py-[3px] rounded-full flex-shrink-0 mt-[2px] ${STATUS_STYLES[item.status].pill}`}
                  >
                    {STATUS_STYLES[item.status].label}
                  </span>
                  <div>
                    <p className="text-[14px] font-medium text-[#1d1d1f] tracking-[-0.01em] mb-[3px]">
                      {item.heading}
                    </p>
                    <p className="text-[13px] text-[#6e6e73] leading-relaxed">
                      {item.body}
                    </p>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      </main>
    </PageShell>
  );
}
