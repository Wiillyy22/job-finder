import type { JobResponse } from "./api/types";

export interface JobFilterState {
  matchFilter: boolean | null;
  newOnly: boolean;
  company: string;
  search: string;
}

export interface FilteredJobsResult {
  jobs: JobResponse[];
  companies: string[];
  activeCompany: string;
  matchLabel: string;
  otherFilterLabels: string[];
  hasActiveFilters: boolean;
}

const MATCH_ALL_LABEL = "Match: All";
const MATCHING_ONLY_LABEL = "Match: Matching only";
const NON_MATCHING_ONLY_LABEL = "Match: Non-matching only";

function normalizeValue(value: string) {
  return value.trim().toLowerCase();
}

function getCompanies(jobs: JobResponse[]) {
  return [...new Set(jobs.map((job) => job.company).filter(Boolean))].sort(
    (a, b) => a.localeCompare(b)
  );
}

function getActiveCompanyFilter(company: string, companies: string[]) {
  const normalizedCompany = normalizeValue(company);
  if (!normalizedCompany) return "";

  return (
    companies.find(
      (candidate) => normalizeValue(candidate) === normalizedCompany
    ) ?? ""
  );
}

function getMatchLabel(matchFilter: boolean | null) {
  if (matchFilter === true) return MATCHING_ONLY_LABEL;
  if (matchFilter === false) return NON_MATCHING_ONLY_LABEL;
  return MATCH_ALL_LABEL;
}

export function filterJobs(
  jobs: JobResponse[],
  filters: JobFilterState
): FilteredJobsResult {
  const companies = getCompanies(jobs);
  const activeCompany = getActiveCompanyFilter(filters.company, companies);
  const activeSearch = filters.search.trim();
  const searchTerm = activeSearch.toLowerCase();

  let filteredJobs = jobs;

  if (filters.matchFilter !== null) {
    filteredJobs = filteredJobs.filter(
      (job) => job.match === filters.matchFilter
    );
  }

  if (filters.newOnly) {
    filteredJobs = filteredJobs.filter((job) => job.is_new);
  }

  if (activeCompany) {
    filteredJobs = filteredJobs.filter(
      (job) => normalizeValue(job.company) === normalizeValue(activeCompany)
    );
  }

  if (searchTerm) {
    filteredJobs = filteredJobs.filter(
      (job) =>
        job.title.toLowerCase().includes(searchTerm) ||
        job.description.toLowerCase().includes(searchTerm) ||
        job.reason.toLowerCase().includes(searchTerm) ||
        job.company.toLowerCase().includes(searchTerm)
    );
  }

  const otherFilterLabels = [
    filters.newOnly ? "New only" : null,
    activeCompany ? `Company: ${activeCompany}` : null,
    activeSearch ? `Search: ${activeSearch}` : null,
  ].filter((value): value is string => Boolean(value));

  return {
    jobs: filteredJobs,
    companies,
    activeCompany,
    matchLabel: getMatchLabel(filters.matchFilter),
    otherFilterLabels,
    hasActiveFilters:
      filters.matchFilter !== null || otherFilterLabels.length > 0,
  };
}
