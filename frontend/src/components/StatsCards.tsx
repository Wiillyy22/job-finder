import type { StatsResponse } from "../api/types";

const cards = [
  {
    key: "total_jobs" as const,
    label: "Total Jobs",
    icon: "📋",
    color: "text-indigo-600 dark:text-indigo-400",
    bg: "bg-indigo-50 dark:bg-indigo-950/40",
  },
  {
    key: "matching_jobs" as const,
    label: "Matching",
    icon: "✅",
    color: "text-emerald-600 dark:text-emerald-400",
    bg: "bg-emerald-50 dark:bg-emerald-950/40",
  },
  {
    key: "new_jobs" as const,
    label: "New Since Last Run",
    icon: "🆕",
    color: "text-amber-600 dark:text-amber-400",
    bg: "bg-amber-50 dark:bg-amber-950/40",
  },
  {
    key: "match_rate" as const,
    label: "Match Rate",
    icon: "📊",
    color: "text-purple-600 dark:text-purple-400",
    bg: "bg-purple-50 dark:bg-purple-950/40",
    suffix: "%",
  },
];

export default function StatsCards({ stats }: { stats: StatsResponse }) {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((c) => (
        <div
          key={c.key}
          className={`${c.bg} rounded-xl p-5 border border-gray-200 dark:border-gray-700/50`}
        >
          <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">
            {c.label}
          </div>
          <div className={`text-3xl font-bold ${c.color}`}>
            {stats[c.key]}
            {c.suffix ?? ""}
          </div>
        </div>
      ))}
    </div>
  );
}
