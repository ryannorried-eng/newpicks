import { BalanceCard } from "../components/bankroll/BalanceCard";
import { BalanceChart } from "../components/bankroll/BalanceChart";
import { useBankroll } from "../hooks/usePerformance";
import { usePicksToday } from "../hooks/usePicks";

export default function BankrollPage() {
  const { data } = useBankroll();
  const { data: picks = [] } = usePicksToday();
  const balance = data?.balance ?? 1000;
  return (
    <div className="space-y-4">
      <BalanceCard balance={balance} />
      <BalanceChart data={data?.history ?? []} />
      <div className="rounded-xl border border-gray-800 bg-gray-900 p-4">
        <h3 className="mb-2 text-lg">Kelly sizing reference</h3>
        <table className="w-full text-sm"><thead className="text-gray-400"><tr><th className="text-left">Pick</th><th className="text-left">Kelly %</th><th className="text-left">Suggested Amount</th></tr></thead><tbody>{picks.map((pick) => <tr key={pick.id} className="border-t border-gray-800"><td className="py-2">{pick.side}</td><td>{(pick.suggested_kelly_fraction * 100).toFixed(2)}%</td><td>${(balance * pick.suggested_kelly_fraction).toFixed(2)}</td></tr>)}</tbody></table>
      </div>
    </div>
  );
}
