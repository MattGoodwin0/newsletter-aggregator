export default function Card({ children, className = "", dark = false, style = {} }) {
  return (
    <div
      className={`rounded-[20px] overflow-hidden ${className}`}
      style={{
        background: dark ? "rgba(29,29,31,0.96)" : "rgba(255,255,255,0.88)",
        backdropFilter: "blur(40px)",
        WebkitBackdropFilter: "blur(40px)",
        border: dark
          ? "0.5px solid rgba(255,255,255,0.1)"
          : "0.5px solid rgba(0,0,0,0.1)",
        boxShadow: dark
          ? "0 2px 40px rgba(0,0,0,0.18), inset 0 0 0 0.5px rgba(255,255,255,0.06)"
          : "0 2px 40px rgba(0,0,0,0.06), inset 0 0 0 0.5px rgba(255,255,255,0.8)",
        ...style,
      }}
    >
      {children}
    </div>
  );
}
