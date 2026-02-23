export function EVBadge({ ev }: { ev: number }) {
  const evPercent = ev * 100;
  return <span className="rounded-md bg-emerald-500/10 px-2 py-1 text-xs text-emerald-400">{evPercent >= 0 ? "+" : ""}{evPercent.toFixed(1)}%</span>;
}
