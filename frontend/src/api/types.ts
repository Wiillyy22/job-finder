export interface RunSummary {
  run_id: string;
  timestamp: string;
  job_count: number;
  match_count: number;
  company_count: number;
}

export interface JobResponse {
  job_id: string;
  title: string;
  company: string;
  department: string;
  location: string;
  url: string;
  description: string;
  match: boolean;
  reason: string;
  is_new: boolean;
}

export interface JobsResponse {
  run_id: string;
  timestamp: string;
  jobs: JobResponse[];
  total: number;
  matching: number;
  non_matching: number;
  new: number;
}

export interface CompanyStat {
  name: string;
  total: number;
  matching: number;
}

export interface StatsResponse {
  run_id: string;
  timestamp: string;
  total_jobs: number;
  matching_jobs: number;
  non_matching_jobs: number;
  new_jobs: number;
  match_rate: number;
  companies: CompanyStat[];
}
