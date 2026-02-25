import PageShell from "./components/PageShell.jsx";
import Card from "./components/Card.jsx";

function ContentCard({ eyebrow, heading, body, dark = false, footer }) {
  return (
    <Card dark={dark}>
      <div className="px-8 py-7">
        <p className="text-[11px] font-semibold tracking-[0.08em] uppercase text-[#86868b] mb-3">
          {eyebrow}
        </p>
        <h2
          className={`text-[19px] font-semibold leading-snug tracking-[-0.02em] mb-3 ${dark ? "text-white" : "text-[#1d1d1f]"}`}
        >
          {heading}
        </h2>
        <p
          className={`text-[14px] leading-relaxed ${dark ? "text-[#86868b]" : "text-[#6e6e73]"}`}
        >
          {body}
        </p>
        {footer && (
          <p className="text-[11px] text-[#52525b] mt-4 pt-4 border-t border-white/10">
            {footer}
          </p>
        )}
      </div>
    </Card>
  );
}

export default function About() {
  return (
    <PageShell active="About">
      {/* Hero */}
      <section className="z-[1] w-full max-w-[680px] mx-auto px-8 pt-20 pb-16 text-center animate-fade-up">
        <p className="text-[12px] font-medium tracking-[0.08em] text-[#86868b] uppercase mb-4">
          The story
        </p>
        <h1 className="text-[clamp(32px,4.5vw,52px)] font-semibold leading-[1.08] tracking-[-0.03em] text-[#1d1d1f] mb-5">
          Built for developers
          <br />
          <span className="font-light text-[#6e6e73]">who love great UX.</span>
        </h1>
        <p className="text-[16px] text-[#6e6e73] leading-relaxed max-w-[480px] mx-auto">
          One beautifully designed magazine. All your sources. End of the week,
          coffee in hand.
        </p>
        <a
          href="#roadmap"
          className="inline-block mt-4 px-4 py-2 bg-black/[0.05] hover:bg-black/[0.09] text-[#1d1d1f] text-[13px] font-medium rounded-[10px] transition-colors"
        >
          View changelog
        </a>
      </section>

      {/* Content cards */}
      <main className="z-[1] w-full max-w-[680px] mx-auto px-6 pb-24 flex flex-col gap-4 animate-fade-up-delay">
        <ContentCard
          eyebrow="The Problem"
          heading="Too many sources. Not enough signal."
          body="I found that staying current as a developer meant subscribing to newsletters, bookmarking media sources, and constantly switching between tabs. The content is valuable — the experience of reading it really isn't. Daily emails, weekly digests, saved links scattered across browsers. It adds up to a lot of friction between you and the ideas that matter."
        />
        <ContentCard
          eyebrow="The Idea"
          heading="What if it felt like reading a magazine?"
          body="Consolidate every source into one beautifully designed digital magazine. Sit down at the end of the week, coffee in hand, relaxing music on the headphones, and catch up on the latest developments across the industry. Something that inspires, that sparks ideas you can bring back to your day-to-day work."
          dark
        />
        <ContentCard
          eyebrow="The Solution"
          heading="A Python script, an RSS feed, and a PDF."
          body="Starting with TLDR — one of the most loved tech newsletters — a relatively simple Python script fetches and scrapes content from RSS feeds for a configurable number of days back, then renders everything into a fully customisable PDF using an HTML and CSS template. The result lands in your downloads ready to read."
        />
        <ContentCard
          eyebrow="What's next"
          heading="More sources. Better design. Same ritual."
          body="The roadmap is about adding more sources and refining the magazine layout until it matches the original vision. But honestly? The ritual already works. End of the week, coffee in hand, headphones on — catching up on the industry, one TLDR edition at a time. More sources coming soon."
          footer="Currently in beta"
        />

        {/* CTA */}
        <Card className="mt-2">
          <div className="px-8 py-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-5">
            <div>
              <p className="text-[15px] font-medium text-[#1d1d1f] tracking-[-0.01em] mb-1">
                Ready to try it?
              </p>
              <p className="text-[13px] text-[#86868b]">
                Add your feeds and generate your first digest.
              </p>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <a
                href="#validator"
                className="px-4 py-[9px] rounded-[10px] bg-black/[0.05] hover:bg-black/[0.09] text-[#1d1d1f] text-[13px] font-medium transition-colors"
              >
                Validate a feed
              </a>
              <a
                href="#"
                className="px-4 py-[9px] rounded-[10px] bg-[#1d1d1f] hover:bg-[#3a3a3c] text-white text-[13px] font-medium transition-colors"
              >
                Open generator
              </a>
            </div>
          </div>
        </Card>
      </main>
    </PageShell>
  );
}
