export default function FeedStatusIcon({ status, url }) {
  if (status === "checking") return (
    <span title="Validating…" style={{ display: "flex", alignItems: "center" }}>
      <svg
        width="13" height="13" viewBox="0 0 13 13"
        style={{ animation: "spin 1s linear infinite", flexShrink: 0 }}
      >
        <circle
          cx="6.5" cy="6.5" r="5.5"
          stroke="#c7c7cc" strokeWidth="1.2" fill="none"
          strokeDasharray="20 14"
        />
      </svg>
    </span>
  );

  if (status === "ok") return (
    <a
      href={`#validator?url=${encodeURIComponent(url)}`}
      title="Feed validated — click for details"
      style={{ display: "flex", alignItems: "center", flexShrink: 0 }}
    >
      <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
        <circle cx="6.5" cy="6.5" r="5.75" stroke="#22c55e" strokeWidth="1.2" />
        <path
          d="M4 6.8l1.8 1.8 3.4-3.4"
          stroke="#22c55e" strokeWidth="1.2"
          strokeLinecap="round" strokeLinejoin="round"
        />
      </svg>
    </a>
  );

  if (status === "partial" || status === "error") return (
    <a
      href={`#validator?url=${encodeURIComponent(url)}`}
      title="Feed has issues — click for details"
      style={{ display: "flex", alignItems: "center", flexShrink: 0 }}
    >
      <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
        <path
          d="M6.5 1.5L12 11.5H1L6.5 1.5Z"
          stroke={status === "error" ? "#ef4444" : "#f59e0b"}
          strokeWidth="1.2" strokeLinejoin="round"
        />
        <path
          d="M6.5 5.5v2.5"
          stroke={status === "error" ? "#ef4444" : "#f59e0b"}
          strokeWidth="1.2" strokeLinecap="round"
        />
        <circle
          cx="6.5" cy="9.5" r="0.6"
          fill={status === "error" ? "#ef4444" : "#f59e0b"}
        />
      </svg>
    </a>
  );

  return null;
}
