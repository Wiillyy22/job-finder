import { useState } from "react";
import type { JobResponse } from "../api/types";
import JobDetailModal from "./JobDetailModal";
import { sortJobs, type SortDir, type SortKey } from "../sortJobs";

export default function JobTable({ jobs }: { jobs: JobResponse[] }) {
  const [sortKey, setSortKey] = useState<SortKey>("company");
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const {
    jobs: sorted,
    effectiveSortKey,
    effectiveSortDir,
    matchSortDisabled,
  } = sortJobs(jobs, sortKey, sortDir);

  const selected =
    selectedJobId ?
      sorted.find((job) => job.job_id === selectedJobId) ?? null
    : null;

  const arrow = (key: SortKey) =>
    effectiveSortKey === key ? (effectiveSortDir === "asc" ? " ↑" : " ↓") : "";

  const ariaSort = (key: SortKey) => {
    if (effectiveSortKey !== key) return "none";
    return effectiveSortDir === "asc" ? "ascending" : "descending";
  };

  return (
    <>
      <div className="bg-white dark:bg-gray-800/50 rounded-xl border border-gray-200 dark:border-gray-700/50 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-gray-50 dark:bg-gray-800 text-gray-600 dark:text-gray-400 text-xs uppercase tracking-wider">
              <tr>
                <th
                  scope="col"
                  aria-sort={ariaSort("company")}
                  className="px-4 py-3"
                >
                  <button
                    type="button"
                    className="inline-flex items-center gap-1 hover:text-gray-900 dark:hover:text-gray-200"
                    onClick={() => toggleSort("company")}
                  >
                    Company{arrow("company")}
                  </button>
                </th>
                <th
                  scope="col"
                  aria-sort={ariaSort("title")}
                  className="px-4 py-3"
                >
                  <button
                    type="button"
                    className="inline-flex items-center gap-1 hover:text-gray-900 dark:hover:text-gray-200"
                    onClick={() => toggleSort("title")}
                  >
                    Title{arrow("title")}
                  </button>
                </th>
                <th scope="col" className="px-4 py-3">
                  Location
                </th>
                <th
                  scope="col"
                  aria-sort={ariaSort("match")}
                  className="px-4 py-3"
                >
                  <button
                    type="button"
                    disabled={matchSortDisabled}
                    title={
                      matchSortDisabled
                        ? "Match sorting is unavailable when all visible rows have the same match status."
                        : undefined
                    }
                    className={`inline-flex items-center gap-1 ${
                      matchSortDisabled
                        ? "cursor-not-allowed opacity-50"
                        : "hover:text-gray-900 dark:hover:text-gray-200"
                    }`}
                    onClick={() => toggleSort("match")}
                  >
                    Match{arrow("match")}
                  </button>
                </th>
                <th
                  scope="col"
                  aria-sort={ariaSort("is_new")}
                  className="px-4 py-3"
                >
                  <button
                    type="button"
                    className="inline-flex items-center gap-1 hover:text-gray-900 dark:hover:text-gray-200"
                    onClick={() => toggleSort("is_new")}
                  >
                    Status{arrow("is_new")}
                  </button>
                </th>
                <th scope="col" className="px-4 py-3">
                  Reason
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700/50">
              {sorted.map((job) => (
                <tr
                  key={job.job_id}
                  className="hover:bg-gray-50 dark:hover:bg-gray-700/30 cursor-pointer transition-colors"
                  onClick={() => setSelectedJobId(job.job_id)}
                >
                  <td className="px-4 py-3 font-medium text-gray-900 dark:text-gray-100 whitespace-nowrap">
                    {job.company}
                  </td>
                  <td className="px-4 py-3 text-gray-700 dark:text-gray-300 max-w-xs truncate">
                    {job.title}
                  </td>
                  <td className="px-4 py-3 text-gray-500 dark:text-gray-400 whitespace-nowrap">
                    {job.location || "—"}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${
                        job.match
                          ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400"
                          : "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400"
                      }`}
                    >
                      {job.match ? "Match" : "No match"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {job.is_new && (
                      <span className="inline-flex px-2 py-0.5 text-xs font-medium rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400">
                        NEW
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-500 dark:text-gray-400 max-w-sm truncate">
                    {job.reason}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {sorted.length === 0 && (
          <div className="text-center py-12 text-gray-400">
            No jobs match your filters.
          </div>
        )}
      </div>

      {selected && (
        <JobDetailModal job={selected} onClose={() => setSelectedJobId(null)} />
      )}
    </>
  );
}
