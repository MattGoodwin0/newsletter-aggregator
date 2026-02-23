import Nav from "./Nav.jsx";
import NoiseBackground from "./NoiseBackground.jsx";

export default function PageShell({ active, children }) {
  return (
    <div
      className="min-h-screen bg-[#f5f5f7] flex flex-col items-center relative overflow-x-hidden"
      style={{ fontFamily: "'Mona Sans', -apple-system, BlinkMacSystemFont, sans-serif" }}
    >
      <NoiseBackground />
      <Nav active={active} />
      {children}
      <footer className="z-[1] pb-8 mt-auto">
        <p className="text-[11px] text-[#c7c7cc] tracking-[0.01em] text-center">
          Digest · Built with newspaper3k, Playwright &amp; Jinja2
        </p>
      </footer>
    </div>
  );
}
