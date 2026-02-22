import type { SignalBreakdown as SignalType } from "../../types";

export function SignalBreakdown({ signals }: { signals: SignalType }) {
  const items = [
    ["EV", signals.ev_magnitude],
    ["Steam", signals.steam_move],
    ["RLM", signals.reverse_line_movement],
    ["Best Line", signals.best_line_available],
    ["Consensus", signals.consensus_deviation],
    ["CLV Trend", signals.closing_line_trend],
    ["Data", signals.data_quality_score],
  ] as const;
  return <div className="grid gap-2 md:grid-cols-2">{items.map(([name, score]) => <div key={name} className="text-xs"><div className="mb-1 flex justify-between text-gray-400"><span>{name}</span><span>{score.toFixed(2)}</span></div><div className="h-2 rounded bg-gray-800"><div className="h-2 rounded bg-emerald-500" style={{ width: `${Math.min(100, Math.max(0, score * 100))}%` }} /></div></div>)}</div>;
}
