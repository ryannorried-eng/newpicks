export function EVBadge({ ev }: { ev: number }) {
  return <span className="rounded-md bg-emerald-500/10 px-2 py-1 text-xs text-emerald-400">{ev >= 0 ? "+" : ""}{ev.toFixed(1)}%</span>;
}
