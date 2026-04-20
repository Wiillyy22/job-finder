import assert from "node:assert/strict";
import test from "node:test";

import { filterJobs } from "../src/filterJobs.ts";

const jobs = [
  {
    job_id: "1",
    title: "Frontend Engineer",
    company: "Acme",
    department: "",
    location: "Stockholm",
    url: "",
    description: "React and TypeScript role",
    match: true,
    reason: "Strong frontend fit",
    is_new: true,
  },
  {
    job_id: "2",
    title: "Backend Engineer",
    company: "Acme",
    department: "",
    location: "Stockholm",
    url: "",
    description: "Python backend services",
    match: false,
    reason: "Less aligned",
    is_new: false,
  },
  {
    job_id: "3",
    title: "Product Designer",
    company: "Globex",
    department: "",
    location: "Remote",
    url: "",
    description: "Design systems and product UX",
    match: false,
    reason: "Not the target role",
    is_new: true,
  },
  {
    job_id: "4",
    title: "Platform Engineer",
    company: "Initech",
    department: "",
    location: "Remote",
    url: "",
    description: "Cloud infrastructure and internal tooling",
    match: true,
    reason: "Relevant engineering experience",
    is_new: false,
  },
];

test("returns every job when no filters are active", () => {
  const result = filterJobs(jobs, {
    matchFilter: null,
    newOnly: false,
    company: "",
    search: "",
  });

  assert.equal(result.jobs.length, jobs.length);
  assert.equal(result.matchLabel, "Match: All");
  assert.equal(result.hasActiveFilters, false);
  assert.deepEqual(result.otherFilterLabels, []);
});

test("returns only matching jobs", () => {
  const result = filterJobs(jobs, {
    matchFilter: true,
    newOnly: false,
    company: "",
    search: "",
  });

  assert.deepEqual(
    result.jobs.map((job) => job.job_id),
    ["1", "4"]
  );
  assert.equal(result.matchLabel, "Match: Matching only");
  assert.equal(result.hasActiveFilters, true);
});

test("returns only non-matching jobs", () => {
  const result = filterJobs(jobs, {
    matchFilter: false,
    newOnly: false,
    company: "",
    search: "",
  });

  assert.deepEqual(
    result.jobs.map((job) => job.job_id),
    ["2", "3"]
  );
  assert.equal(result.matchLabel, "Match: Non-matching only");
});

test("keeps non-match filters active when match filter is cleared", () => {
  const result = filterJobs(jobs, {
    matchFilter: null,
    newOnly: true,
    company: "acme",
    search: "",
  });

  assert.deepEqual(
    result.jobs.map((job) => job.job_id),
    ["1"]
  );
  assert.equal(result.activeCompany, "Acme");
  assert.deepEqual(result.otherFilterLabels, ["New only", "Company: Acme"]);
});

test("combines match filter with company and search filters", () => {
  const result = filterJobs(jobs, {
    matchFilter: false,
    newOnly: false,
    company: "globex",
    search: "design",
  });

  assert.deepEqual(
    result.jobs.map((job) => job.job_id),
    ["3"]
  );
  assert.deepEqual(result.otherFilterLabels, [
    "Company: Globex",
    "Search: design",
  ]);
});

test("ignores whitespace-only search text", () => {
  const result = filterJobs(jobs, {
    matchFilter: true,
    newOnly: false,
    company: "",
    search: "   ",
  });

  assert.deepEqual(
    result.jobs.map((job) => job.job_id),
    ["1", "4"]
  );
  assert.deepEqual(result.otherFilterLabels, []);
});
