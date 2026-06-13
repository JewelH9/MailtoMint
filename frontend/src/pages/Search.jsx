import { useState, useEffect, useRef } from "react";
import {
  Search as SearchIcon,
  X,
  Filter,
  FileText,
  AlertTriangle,
} from "lucide-react";
import Layout from "../components/Layout";
import api from "../api/client";
import toast from "react-hot-toast";

const EXAMPLE_QUERIES = [
  "Amazon bills from March",
  "Travel expenses above 5000",
  "Food bills last month",
  "Flagged invoices",
  "Healthcare expenses",
  "Pending invoices",
];

const categoryColors = {
  travel: "bg-blue-50 text-blue-700",
  food: "bg-orange-50 text-orange-700",
  office: "bg-purple-50 text-purple-700",
  utilities: "bg-teal-50 text-teal-700",
  marketing: "bg-pink-50 text-pink-700",
  healthcare: "bg-green-50 text-green-700",
  subscription: "bg-indigo-50 text-indigo-700",
};

export default function Search() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState({
    category: "",
    min_amount: "",
    max_amount: "",
    status: "",
  });
  const inputRef = useRef(null);
  const debounceRef = useRef(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const doSearch = async (q, extraFilters = {}) => {
    if (!q.trim() && !Object.values(extraFilters).some(Boolean)) {
      setResults([]);
      setSearched(false);
      return;
    }

    setLoading(true);
    setSearched(true);

    try {
      const params = { q };
      if (extraFilters.category) params.category = extraFilters.category;
      if (extraFilters.min_amount) params.min_amount = extraFilters.min_amount;
      if (extraFilters.max_amount) params.max_amount = extraFilters.max_amount;
      if (extraFilters.status) params.status = extraFilters.status;

      const { data } = await api.get("/search", { params });
      setResults(data);
    } catch {
      toast.error("Search failed");
    } finally {
      setLoading(false);
    }
  };

  // Debounced search — waits 400ms after user stops typing
  const handleQueryChange = (e) => {
    const val = e.target.value;
    setQuery(val);

    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      doSearch(val, filters);
    }, 400);
  };

  const handleFilterChange = (key, value) => {
    const updated = { ...filters, [key]: value };
    setFilters(updated);
    doSearch(query, updated);
  };

  const handleExample = (example) => {
    setQuery(example);
    doSearch(example, filters);
  };

  const clearSearch = () => {
    setQuery("");
    setResults([]);
    setSearched(false);
    inputRef.current?.focus();
  };

  return (
    <Layout>
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-semibold text-gray-900">Smart Search</h1>
          <p className="text-gray-500 text-sm mt-1">
            Search invoices in plain English
          </p>
        </div>

        {/* Search input */}
        <div className="relative mb-4">
          <SearchIcon
            size={18}
            className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400"
          />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={handleQueryChange}
            placeholder='Try "Amazon bills from March" or "Travel above 5000"'
            className="w-full pl-11 pr-10 py-3.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent shadow-sm"
          />
          {query && (
            <button
              onClick={clearSearch}
              className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              <X size={16} />
            </button>
          )}
        </div>

        {/* Filter toggle + filters */}
        <div className="mb-6">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 mb-3"
          >
            <Filter size={14} />
            {showFilters ? "Hide filters" : "Show filters"}
          </button>

          {showFilters && (
            <div className="grid grid-cols-4 gap-3 p-4 bg-gray-50 rounded-xl border border-gray-100">
              <div>
                <label className="label text-xs">Category</label>
                <select
                  className="input text-sm"
                  value={filters.category}
                  onChange={(e) =>
                    handleFilterChange("category", e.target.value)
                  }
                >
                  <option value="">All</option>
                  {[
                    "travel",
                    "food",
                    "office",
                    "utilities",
                    "marketing",
                    "healthcare",
                    "subscription",
                  ].map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label text-xs">Min amount</label>
                <input
                  type="number"
                  className="input text-sm"
                  placeholder="₹0"
                  value={filters.min_amount}
                  onChange={(e) =>
                    handleFilterChange("min_amount", e.target.value)
                  }
                />
              </div>
              <div>
                <label className="label text-xs">Max amount</label>
                <input
                  type="number"
                  className="input text-sm"
                  placeholder="₹99999"
                  value={filters.max_amount}
                  onChange={(e) =>
                    handleFilterChange("max_amount", e.target.value)
                  }
                />
              </div>
              <div>
                <label className="label text-xs">Status</label>
                <select
                  className="input text-sm"
                  value={filters.status}
                  onChange={(e) => handleFilterChange("status", e.target.value)}
                >
                  <option value="">All</option>
                  <option value="pending">Pending</option>
                  <option value="processed">Processed</option>
                  <option value="flagged">Flagged</option>
                </select>
              </div>
            </div>
          )}
        </div>

        {/* Example queries — shown before first search */}
        {!searched && (
          <div>
            <p className="text-xs text-gray-400 mb-3 uppercase tracking-wide font-medium">
              Try these
            </p>
            <div className="flex flex-wrap gap-2">
              {EXAMPLE_QUERIES.map((ex) => (
                <button
                  key={ex}
                  onClick={() => handleExample(ex)}
                  className="px-3 py-1.5 bg-gray-100 hover:bg-brand-50 hover:text-brand-700 text-gray-600 rounded-full text-sm transition-colors"
                >
                  {ex}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="flex items-center justify-center py-12 text-gray-400">
            <SearchIcon size={18} className="animate-pulse mr-2" />
            Searching...
          </div>
        )}

        {/* Results */}
        {!loading && searched && (
          <div>
            <p className="text-xs text-gray-400 mb-3">
              {results.length} result{results.length !== 1 ? "s" : ""} found
            </p>

            {results.length === 0 ? (
              <div className="text-center py-12 text-gray-400">
                <SearchIcon size={32} className="mx-auto mb-3 opacity-30" />
                <p className="font-medium">No invoices found</p>
                <p className="text-sm mt-1">
                  Try different keywords or clear the filters
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {results.map((inv) => (
                  <div
                    key={inv.id}
                    className="card p-4 flex items-center gap-4 hover:shadow-md transition-shadow"
                  >
                    <div className="w-9 h-9 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0">
                      <FileText size={16} className="text-gray-400" />
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {inv.vendor_name || inv.file_name || "Unnamed"}
                        </p>
                        {inv.is_flagged && (
                          <AlertTriangle
                            size={13}
                            className="text-red-500 flex-shrink-0"
                          />
                        )}
                      </div>
                      <p className="text-xs text-gray-400 mt-0.5">
                        {inv.invoice_number && `#${inv.invoice_number} · `}
                        {inv.invoice_date || inv.created_at?.slice(0, 10)}
                      </p>
                    </div>

                    <div className="flex items-center gap-3 flex-shrink-0">
                      {inv.category && (
                        <span
                          className={`badge ${categoryColors[inv.category] || "bg-gray-100 text-gray-600"}`}
                        >
                          {inv.category}
                        </span>
                      )}
                      <span className="text-sm font-semibold text-gray-900">
                        {inv.total_amount
                          ? `₹${inv.total_amount.toLocaleString()}`
                          : "—"}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </Layout>
  );
}
