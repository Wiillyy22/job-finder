interface FilterBarProps {
  matchFilter: boolean | null;
  setMatchFilter: (v: boolean | null) => void;
  newOnly: boolean;
  setNewOnly: (v: boolean) => void;
  company: string;
  setCompany: (v: string) => void;
  search: string;
  setSearch: (v: string) => void;
  companies: string[];
}

export default function FilterBar({
  matchFilter,
  setMatchFilter,
  newOnly,
  setNewOnly,
  company,
  setCompany,
  search,
  setSearch,
  companies,
}: FilterBarProps) {
  const btn = (active: boolean) =>
    `px-3 py-1.5 text-sm rounded-lg font-medium transition-colors ${
      active
        ? "bg-indigo-600 text-white"
        : "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
    }`;

  return (
    <div className="flex flex-wrap items-center gap-3">
      {/* Match filter toggles */}
      <div className="flex gap-1">
        <button
          type="button"
          aria-pressed={matchFilter === null}
          className={btn(matchFilter === null)}
          onClick={() => setMatchFilter(null)}
        >
          All
        </button>
        <button
          type="button"
          aria-pressed={matchFilter === true}
          className={btn(matchFilter === true)}
          onClick={() => setMatchFilter(true)}
        >
          Matching
        </button>
        <button
          type="button"
          aria-pressed={matchFilter === false}
          className={btn(matchFilter === false)}
          onClick={() => setMatchFilter(false)}
        >
          Non-matching
        </button>
      </div>

      {/* New only toggle */}
      <button
        type="button"
        aria-pressed={newOnly}
        className={btn(newOnly)}
        onClick={() => setNewOnly(!newOnly)}
      >
        New only
      </button>

      {/* Company dropdown */}
      <select
        value={company}
        onChange={(e) => setCompany(e.target.value)}
        className="px-3 py-1.5 text-sm rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200"
      >
        <option value="">All companies</option>
        {companies.map((c) => (
          <option key={c} value={c}>
            {c}
          </option>
        ))}
      </select>

      {/* Search */}
      <input
        type="text"
        placeholder="Search jobs..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="px-3 py-1.5 text-sm rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 placeholder-gray-400 w-48"
      />
    </div>
  );
}
