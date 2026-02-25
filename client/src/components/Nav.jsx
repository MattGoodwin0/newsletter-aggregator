const NAV_LINKS = [
  { label: "Generator", hash: "#" },
  { label: "Validator", hash: "#validator" },
  { label: "About", hash: "#about" },
];

export default function Nav({ active }) {
  return (
    <nav
      className="w-full sticky top-0 z-50 border-b border-black/10"
      style={{
        background: "rgba(245,245,247,0.72)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
      }}
    >
      <div className="max-w-[960px] mx-auto px-8 h-12 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-[7px] h-[7px] rounded-full bg-[#1d1d1f]" />
          <a
            href="#"
            className="text-[14px] font-serif font-medium text-[#1d1d1f] tracking-[-0.01em]"
          >
            Serifdigest
          </a>
          {active && (
            <>
              <span className="text-[#c7c7cc] mx-1 text-[14px]">/</span>
              <span className="text-[14px] text-[#86868b]">{active}</span>
            </>
          )}
        </div>

        <div className="flex items-center gap-5">
          {NAV_LINKS.filter((l) => l.label !== active).map((link) => (
            <a
              key={link.label}
              href={link.hash}
              className="text-[13px] text-[#86868b] hover:text-[#1d1d1f] transition-colors tracking-[-0.01em]"
            >
              {link.label}
            </a>
          ))}
          <span className="text-[10px] font-medium text-[#86868b] bg-black/5 px-[7px] py-[2px] rounded-full tracking-[0.02em]">
            Beta
          </span>
        </div>
      </div>
    </nav>
  );
}
