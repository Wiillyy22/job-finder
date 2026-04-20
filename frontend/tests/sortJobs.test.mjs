import assert from "node:assert/strict";
import test from "node:test";

import { sortJobs } from "../src/sortJobs.ts";

const jobs = [
  {
    job_id: "1",
    title: "Frontend Engineer",
    company: "Acme",
    department: "",
    location: "Stockholm",
    url: "",
    description: "",
    match: true,
    reason: "",
    is_new: false,
  },
  {
    job_id: "2",
    title: "Backend Engineer",
    company: "Beta",
    department: "",
    location: "Stockholm",
    url: "",
    description: "",
    match: false,
    reason: "",
    is_new: false,
  },
  {
    job_id: "3",
    title: "Platform Engineer",
    company: "Core",
    department: "",
    location: "Remote",
    url: "",
    description: "",
    match: true,
    reason: "",
    is_new: true,
  },
];

test("keeps explicit match sorting when both match values are present", () => {
  const result = sortJobs(jobs, "match", "desc");

  assert.equal(result.effectiveSortKey, "match");
  assert.equal(result.effectiveSortDir, "desc");
  assert.equal(result.matchSortDisabled, false);
  assert.deepEqual(
    result.jobs.map((job) => job.job_id),
    ["1", "3", "2"]
  );
});

test("falls back to company sort when all visible rows share one match value", () => {
  const matchingJobs = jobs.filter((job) => job.match);
  const result = sortJobs(matchingJobs, "match", "desc");

  assert.equal(result.effectiveSortKey, "company");
  assert.equal(result.effectiveSortDir, "asc");
  assert.equal(result.matchSortDisabled, true);
  assert.deepEqual(
    result.jobs.map((job) => job.job_id),
    ["1", "3"]
  );
});
