const tiers = ["conservative", "moderate", "aggressive"] as const;

export function RiskTierTabs({ active, onChange }: { active: (typeof tiers)[number]; onChange: (v: (typeof tiers)[number]) => void }) {
  return <div className="mb-4 flex gap-2">{tiers.map((tier) => <button key={tier} onClick={() => onChange(tier)} className={`rounded-lg px-3 py-2 text-sm capitalize ${active === tier ? "bg-gray-800 text-gray-100" : "bg-gray-900 text-gray-400"}`}>{tier}</button>)}</div>;
}
