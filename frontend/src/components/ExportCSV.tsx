import type { JobResponse } from "../api/types";

export default function ExportCSV({ jobs }: { jobs: JobResponse[] }) {
  const exportCsv = () => {
    const headers = ["Company", "Title", "Location", "Match", "New", "Reason", "URL"];
    const rows = jobs.map((j) => [
      j.company,
      j.title,
      j.location,
      j.match ? "Yes" : "No",
      j.is_new ? "Yes" : "No",
      j.reason,
      j.url,
    ]);

    const escape = (s: string) => `"${s.replace(/"/g, '""')}"`;
    const csv = [headers, ...rows].map((row) => row.map(escape).join(",")).join("\n");

    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "jobs_export.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <button
      onClick={exportCsv}
      className="px-3 py-1.5 text-sm rounded-lg font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
      title="Export current view to CSV"
    >
      Export CSV
    </button>
  );
}
