import { useEffect, useRef } from "react";
import type { JobResponse } from "../api/types";

export default function JobDetailModal({
  job,
  onClose,
}: {
  job: JobResponse;
  onClose: () => void;
}) {
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);
  const titleId = `job-detail-title-${job.job_id}`;

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    document.body.style.overflow = "hidden";
    closeButtonRef.current?.focus();
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-6">
          {/* Header */}
          <div className="flex items-start justify-between mb-4">
            <div>
              <h2
                id={titleId}
                className="text-xl font-bold text-gray-900 dark:text-gray-100"
              >
                {job.title}
              </h2>
              <p className="text-gray-500 dark:text-gray-400 mt-1">
                {job.company}
                {job.location ? ` · ${job.location}` : ""}
                {job.department ? ` · ${job.department}` : ""}
              </p>
            </div>
            <button
              ref={closeButtonRef}
              type="button"
              aria-label="Close job details"
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 text-2xl leading-none"
            >
              ×
            </button>
          </div>

          {/* Badges */}
          <div className="flex gap-2 mb-4">
            <span
              className={`inline-flex px-2.5 py-1 text-xs font-medium rounded-full ${
                job.match
                  ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400"
                  : "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400"
              }`}
            >
              {job.match ? "Match" : "No match"}
            </span>
            {job.is_new && (
              <span className="inline-flex px-2.5 py-1 text-xs font-medium rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400">
                NEW
              </span>
            )}
          </div>

          {/* Reason */}
          <div className="mb-4">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1">
              Assessment
            </h3>
            <p className="text-gray-600 dark:text-gray-400">{job.reason}</p>
          </div>

          {/* Description */}
          {job.description && (
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1">
                Description
              </h3>
              <p className="text-gray-600 dark:text-gray-400 whitespace-pre-wrap">
                {job.description}
              </p>
            </div>
          )}

          {/* Apply button */}
          {job.url && (
            <a
              href={job.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg transition-colors"
            >
              Apply
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                />
              </svg>
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
