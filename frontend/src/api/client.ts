import type { RunSummary, JobsResponse, StatsResponse } from "./types";

const BASE = "/api";

type RequestOptions = {
  signal?: AbortSignal;
};

async function requestJson<T>(
  path: string,
  options?: RequestOptions
): Promise<T> {
  const res = await fetch(path, { signal: options?.signal });

  if (!res.ok) {
    const details = await res.text().catch(() => "");
    throw new Error(details || `Request failed with status ${res.status}`);
  }

  return res.json() as Promise<T>;
}

export async function fetchRuns(
  options?: RequestOptions
): Promise<RunSummary[]> {
  return requestJson<RunSummary[]>(`${BASE}/runs`, options);
}

export async function fetchJobs(
  runId: string,
  params?: {
    match?: boolean | null;
    company?: string | null;
    new_only?: boolean;
    search?: string;
  },
  options?: RequestOptions
): Promise<JobsResponse> {
  const query = new URLSearchParams();
  if (params?.match !== undefined && params.match !== null)
    query.set("match", String(params.match));
  if (params?.company) query.set("company", params.company);
  if (params?.new_only) query.set("new_only", "true");
  if (params?.search) query.set("search", params.search);

  const qs = query.toString();
  return requestJson<JobsResponse>(
    `${BASE}/runs/${runId}/jobs${qs ? `?${qs}` : ""}`,
    options
  );
}

export async function fetchStats(
  runId: string,
  options?: RequestOptions
): Promise<StatsResponse> {
  return requestJson<StatsResponse>(`${BASE}/runs/${runId}/stats`, options);
}
