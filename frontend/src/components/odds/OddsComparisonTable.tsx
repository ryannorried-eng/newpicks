import type { OddsSnapshot } from "../../types";

export function OddsComparisonTable({ odds, gameId }: { odds: OddsSnapshot[]; gameId: number | null }) {
  const gameOdds = gameId ? odds.filter((o) => o.game_id === gameId) : [];
  const grouped = gameOdds.reduce<Record<string, OddsSnapshot[]>>((acc, item) => {
    acc[item.bookmaker] = acc[item.bookmaker] ?? [];
    acc[item.bookmaker].push(item);
    return acc;
  }, {});
  return (
    <div className="overflow-x-auto rounded-xl border border-gray-800 bg-gray-900">
      <table className="w-full text-sm"><thead className="bg-gray-950 text-gray-400"><tr><th className="p-3">Bookmaker</th><th>Market</th><th>Side</th><th>Odds</th><th>Line</th></tr></thead>
      <tbody>{Object.entries(grouped).map(([book, items]) => items?.map((item, idx) => <tr key={`${book}-${idx}`} className="border-t border-gray-800"><td className="p-3">{book}</td><td>{item.market}</td><td>{item.side}</td><td className="font-mono">{item.odds}</td><td>{item.line ?? "-"}</td></tr>))}</tbody></table>
    </div>
  );
}
