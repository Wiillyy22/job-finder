import type { JobResponse } from "./api/types";

export type SortKey = "company" | "title" | "match" | "is_new";
export type SortDir = "asc" | "desc";

export interface SortedJobsResult {
  jobs: JobResponse[];
  effectiveSortKey: SortKey;
  effectiveSortDir: SortDir;
  matchSortDisabled: boolean;
}

function hasUniformMatchValue(jobs: JobResponse[]) {
  return jobs.length > 0 && jobs.every((job) => job.match === jobs[0].match);
}

export function sortJobs(
  jobs: JobResponse[],
  sortKey: SortKey,
  sortDir: SortDir
): SortedJobsResult {
  const matchSortDisabled = hasUniformMatchValue(jobs);
  const effectiveSortKey =
    sortKey === "match" && matchSortDisabled ? "company" : sortKey;
  const effectiveSortDir =
    sortKey === "match" && matchSortDisabled ? "asc" : sortDir;

  const sortedJobs = [...jobs].sort((a, b) => {
    if (effectiveSortKey === "match" || effectiveSortKey === "is_new") {
      const av = Number(a[effectiveSortKey]);
      const bv = Number(b[effectiveSortKey]);
      return effectiveSortDir === "asc" ? av - bv : bv - av;
    }

    const av = a[effectiveSortKey].toLowerCase();
    const bv = b[effectiveSortKey].toLowerCase();
    return effectiveSortDir === "asc"
      ? av.localeCompare(bv)
      : bv.localeCompare(av);
  });

  return {
    jobs: sortedJobs,
    effectiveSortKey,
    effectiveSortDir,
    matchSortDisabled,
  };
}
