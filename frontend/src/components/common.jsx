export function StatusPill({ status }) {
  const config = {
    Confirmed: ["confirmed", "✓ Confirmed"],
    Pending: ["pending", "◷ Pending"],
    False: ["false", "× False"],
  }[status];
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
