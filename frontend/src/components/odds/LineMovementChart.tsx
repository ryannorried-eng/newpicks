import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { OddsSnapshot } from "../../types";

export function LineMovementChart({ odds, gameId }: { odds: OddsSnapshot[]; gameId: number | null }) {
  const chartData = (gameId ? odds.filter((o) => o.game_id === gameId) : []).map((o) => ({ time: new Date(o.snapshot_time).toLocaleTimeString(), [o.bookmaker]: o.odds }));
  const books = [...new Set((gameId ? odds.filter((o) => o.game_id === gameId) : []).map((o) => o.bookmaker))].slice(0, 5);
  return <div className="h-72 rounded-xl border border-gray-800 bg-gray-900 p-3"><ResponsiveContainer width="100%" height="100%"><LineChart data={chartData}><XAxis dataKey="time" stroke="#9ca3af" /><YAxis stroke="#9ca3af" /><Tooltip />{books.map((book, i) => <Line key={book} dataKey={book} stroke={["#34d399", "#60a5fa", "#f59e0b", "#f87171", "#a78bfa"][i]} dot={false} />)}</LineChart></ResponsiveContainer></div>;
}
