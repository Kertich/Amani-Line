export function StatusPill({ status }) {
  const normalizedStatus =
    typeof status === "string"
      ? status.charAt(0).toUpperCase() + status.slice(1).toLowerCase()
      : "";
  const config = {
    Confirmed: ["confirmed", "✓ Confirmed"],
    Pending: ["pending", "◷ Pending"],
    False: ["false", "× False"],
  }[normalizedStatus] || ["pending", status || "Unknown"];
  return <span className={`pill ${config[0]}`}>{config[1]}</span>;
}

export function Icon({ name }) {
  const icons = {
    shield: "♢",
    arrow: "→",
    close: "×",
    send: "↑",
    check: "✓",
    menu: "☰",
    back: "←",
    phone: "⌕",
    lock: "⌑",
    map: "⌖",
    calendar: "□",
  };
  return <span aria-hidden="true">{icons[name] || name}</span>;
}
