import type { CompanyStat } from "../api/types";

export default function CompanyChart({
  companies,
}: {
  companies: CompanyStat[];
}) {
  if (!companies.length) return null;
  const max = Math.max(...companies.map((c) => c.total));

  return (
    <div className="bg-white dark:bg-gray-800/50 rounded-xl border border-gray-200 dark:border-gray-700/50 p-5">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
        Jobs per Company
      </h2>
      <div className="space-y-2 max-h-[400px] overflow-y-auto pr-2">
        {companies.map((c) => {
          const matchPct = max > 0 ? (c.matching / max) * 100 : 0;
          const nonMatchPct = max > 0 ? ((c.total - c.matching) / max) * 100 : 0;
          return (
            <div key={c.name} className="flex items-center gap-3">
              <div className="w-32 text-sm text-gray-700 dark:text-gray-300 truncate shrink-0 text-right">
                {c.name}
              </div>
              <div className="flex-1 flex h-6 bg-gray-100 dark:bg-gray-700/40 rounded overflow-hidden">
                {c.matching > 0 && (
                  <div
                    className="bg-emerald-500 dark:bg-emerald-400 transition-all duration-500"
                    style={{ width: `${matchPct}%` }}
                    title={`${c.matching} matching`}
                  />
                )}
                <div
                  className="bg-gray-300 dark:bg-gray-600 transition-all duration-500"
                  style={{ width: `${nonMatchPct}%` }}
                  title={`${c.total - c.matching} non-matching`}
                />
              </div>
              <div className="w-16 text-sm text-gray-500 dark:text-gray-400 shrink-0">
                {c.matching}/{c.total}
              </div>
            </div>
          );
        })}
      </div>
      <div className="flex gap-4 mt-3 text-xs text-gray-500 dark:text-gray-400">
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-emerald-500 dark:bg-emerald-400 inline-block" />
          Matching
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-gray-300 dark:bg-gray-600 inline-block" />
          Non-matching
        </span>
      </div>
    </div>
  );
}
