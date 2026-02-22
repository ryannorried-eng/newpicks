import type { ParlayLeg } from "../../types";

export function ParlayLegList({ legs }: { legs: ParlayLeg[] }) {
  return <ul className="mt-2 space-y-1 text-xs text-gray-300">{legs.map((leg) => <li key={leg.id}>#{leg.leg_order} {leg.pick.side} {leg.pick.line ?? ""} ({leg.pick.odds_american})</li>)}</ul>;
}
