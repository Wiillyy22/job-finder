import { useEffect, useMemo, useRef, useState } from "react";
import { fetchRuns, fetchJobs, fetchStats } from "./api/client";
import type {
  RunSummary,
  JobsResponse,
  StatsResponse,
} from "./api/types";
import StatsCards from "./components/StatsCards";
import CompanyChart from "./components/CompanyChart";
import FilterBar from "./components/FilterBar";
import JobTable from "./components/JobTable";
import ExportCSV from "./components/ExportCSV";
import { filterJobs } from "./filterJobs";

type Tab = "dashboard" | "jobs";

export default function App() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [runsError, setRunsError] = useState<string | null>(null);
  const [runsLoading, setRunsLoading] = useState(true);
  const [selectedRunId, setSelectedRunId] = useState<string>("");
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [jobsData, setJobsData] = useState<JobsResponse | null>(null);
  const [dataError, setDataError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("dashboard");
  const [dark, setDark] = useState(() =>
    window.matchMedia("(prefers-color-scheme: dark)").matches
  );
  const [now, setNow] = useState<number | null>(null);
  const requestVersionRef = useRef(0);

  // Filters
  const [matchFilter, setMatchFilter] = useState<boolean | null>(null);
  const [newOnly, setNewOnly] = useState(false);
  const [company, setCompany] = useState("");
  const [search, setSearch] = useState("");

  function selectRun(runId: string) {
    requestVersionRef.current += 1;
    setSelectedRunId(runId);
    setStats(null);
    setJobsData(null);
    setDataError(null);
  }

  // Toggle dark mode
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);

  useEffect(() => {
    const updateNow = () => setNow(Date.now());
    updateNow();

    const intervalId = window.setInterval(updateNow, 60_000);
    return () => window.clearInterval(intervalId);
  }, []);

  // Load runs on mount
  useEffect(() => {
    const controller = new AbortController();

    fetchRuns({ signal: controller.signal })
      .then((nextRuns) => {
        setRuns(nextRuns);
        selectRun(nextRuns[0]?.run_id ?? "");
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;

        setRuns([]);
        setSelectedRunId("");
        setRunsError(
          error instanceof Error ? error.message : "Failed to load runs."
        );
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setRunsLoading(false);
        }
      });

    return () => controller.abort();
  }, []);

  // Load data when run changes
  useEffect(() => {
    if (!selectedRunId) return;

    const controller = new AbortController();
    const requestVersion = requestVersionRef.current;

    Promise.all([
      fetchStats(selectedRunId, { signal: controller.signal }),
      fetchJobs(selectedRunId, undefined, { signal: controller.signal }),
    ])
      .then(([nextStats, nextJobs]) => {
        if (
          controller.signal.aborted ||
          requestVersionRef.current !== requestVersion
        ) {
          return;
        }

        setStats(nextStats);
        setJobsData(nextJobs);
      })
      .catch((error: unknown) => {
        if (
          controller.signal.aborted ||
          requestVersionRef.current !== requestVersion
        ) {
          return;
        }

        setDataError(
          error instanceof Error
            ? error.message
            : "Failed to load run details."
        );
      });

    return () => controller.abort();
  }, [selectedRunId]);

  const currentStats =
    stats && stats.run_id === selectedRunId ? stats : null;
  const currentJobsData =
    jobsData && jobsData.run_id === selectedRunId ? jobsData : null;

  const {
    jobs: filteredJobs,
    companies,
    activeCompany,
    matchLabel,
    otherFilterLabels,
    hasActiveFilters,
  } = useMemo(
    () =>
      filterJobs(currentJobsData?.jobs ?? [], {
        matchFilter,
        newOnly,
        company,
        search,
      }),
    [company, currentJobsData, matchFilter, newOnly, search]
  );

  const relativeTime = (ts: string, currentTime: number) => {
    const timestamp = new Date(ts).getTime();
    if (Number.isNaN(timestamp)) return ts;

    const diff = Math.max(0, currentTime - timestamp);
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  };

  const tabBtn = (t: Tab, label: string) => (
    <button
      className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
        tab === t
          ? "bg-indigo-600 text-white"
          : "text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
      }`}
      onClick={() => setTab(t)}
    >
      {label}
    </button>
  );

  const formatRunLabel = (run: RunSummary) => {
    const timestamp = new Date(run.timestamp);
    if (Number.isNaN(timestamp.getTime())) {
      return `${run.run_id} (${run.job_count} jobs)`;
    }

    return `${timestamp.toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    })} (${run.job_count} jobs)`;
  };

  const loading =
    runsLoading || (!!selectedRunId && !dataError && (!currentStats || !currentJobsData));
  const totalJobs = currentJobsData?.jobs.length ?? 0;
  const jobsSummary =
    totalJobs === 0
      ? "No jobs in this run."
      : hasActiveFilters
        ? `Showing ${filteredJobs.length} of ${totalJobs} jobs.`
        : `Showing all ${totalJobs} jobs.`;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors">
      {/* Navigation */}
      <nav className="sticky top-0 z-40 bg-white/80 dark:bg-gray-800/80 backdrop-blur-md border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14">
            <div className="flex items-center gap-4">
              <h1 className="text-lg font-bold text-gray-900 dark:text-gray-100">
                Job Finder
              </h1>
              <div className="flex gap-1">
                {tabBtn("dashboard", "Dashboard")}
                {tabBtn("jobs", "Jobs")}
              </div>
            </div>
            <div className="flex items-center gap-3">
              {runs.length > 0 && (
                <select
                  value={selectedRunId}
                  onChange={(e) => selectRun(e.target.value)}
                  className="px-3 py-1.5 text-sm rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200"
                >
                  {runs.map((r) => (
                    <option key={r.run_id} value={r.run_id}>
                      {formatRunLabel(r)}
                    </option>
                  ))}
                </select>
              )}
              {currentStats && now !== null && (
                <span className="text-xs text-gray-400">
                  {relativeTime(currentStats.timestamp, now)}
                </span>
              )}
              <button
                onClick={() => setDark(!dark)}
                className="p-2 rounded-lg text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                title="Toggle dark mode"
              >
                {dark ? "\u2600\uFE0F" : "\uD83C\uDF19"}
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {runsError ? (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-6 text-red-700 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-300">
            {runsError}
          </div>
        ) : !selectedRunId && !runsLoading ? (
          <div className="rounded-xl border border-gray-200 bg-white px-4 py-10 text-center text-gray-500 dark:border-gray-700 dark:bg-gray-800/50 dark:text-gray-400">
            No runs found.
          </div>
        ) : dataError ? (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-6 text-red-700 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-300">
            {dataError}
          </div>
        ) : loading ? (
          <div className="text-center py-20 text-gray-400">Loading...</div>
        ) : tab === "dashboard" ? (
          <div className="space-y-6">
            <StatsCards stats={currentStats!} />
            <CompanyChart companies={currentStats!.companies} />
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <FilterBar
                matchFilter={matchFilter}
                setMatchFilter={setMatchFilter}
                newOnly={newOnly}
                setNewOnly={setNewOnly}
                company={activeCompany}
                setCompany={setCompany}
                search={search}
                setSearch={setSearch}
                companies={companies}
              />
              <ExportCSV jobs={filteredJobs} />
            </div>
            <div
              role="status"
              className="flex flex-wrap items-center gap-2 text-sm text-gray-500 dark:text-gray-400"
            >
              <span>{jobsSummary}</span>
              <span className="inline-flex rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-700 dark:bg-indigo-950/40 dark:text-indigo-300">
                {matchLabel}
              </span>
              {otherFilterLabels.map((label) => (
                <span
                  key={label}
                  className="inline-flex rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600 dark:bg-gray-800 dark:text-gray-300"
                >
                  {label}
                </span>
              ))}
            </div>
            <JobTable jobs={filteredJobs} />
          </div>
        )}
      </main>
    </div>
  );
}
