export function BalanceCard({ balance }: { balance: number }) {
  return <div className="rounded-xl border border-gray-800 bg-gray-900 p-4"><div className="text-sm text-gray-400">Current Balance</div><div className="mt-1 font-mono text-3xl text-emerald-400">${balance.toFixed(2)}</div></div>;
}
