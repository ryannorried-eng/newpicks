import clsx from "clsx";

export function ConfidenceBadge({ tier }: { tier: "high" | "medium" | "low" }) {
  return (
    <span
      className={clsx(
        "rounded-md border px-2 py-1 text-xs uppercase",
        tier === "high" && "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
        tier === "medium" && "bg-amber-500/20 text-amber-400 border-amber-500/30",
        tier === "low" && "bg-gray-500/20 text-gray-400 border-gray-500/30",
      )}
    >
      {tier}
    </span>
  );
}
