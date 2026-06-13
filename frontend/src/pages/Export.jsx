import { useState } from "react";
import { Download, FileText, FileSpreadsheet, File } from "lucide-react";
import Layout from "../components/Layout";
import api from "../api/client";
import toast from "react-hot-toast";

const exportFormats = [
  {
    id: "csv",
    label: "CSV",
    description: "Plain comma-separated file. Works in any spreadsheet app.",
    icon: FileText,
    color: "bg-blue-50 text-blue-600 border-blue-100",
    mime: "text/csv",
    ext: "csv",
  },
  {
    id: "excel",
    label: "Excel",
    description: "Formatted .xlsx with color coding and summary row.",
    icon: FileSpreadsheet,
    color: "bg-green-50 text-green-600 border-green-100",
    mime: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ext: "xlsx",
  },
  {
    id: "pdf",
    label: "PDF Report",
    description: "Polished report with summary stats and invoice table.",
    icon: File,
    color: "bg-red-50 text-red-500 border-red-100",
    mime: "application/pdf",
    ext: "pdf",
  },
];

export default function Export() {
  const [filters, setFilters] = useState({
    category: "",
    status: "",
    date_from: "",
    date_to: "",
  });
  const [loading, setLoading] = useState({});

  const handleExport = async (format) => {
    setLoading((prev) => ({ ...prev, [format.id]: true }));

    try {
      const params = {};
      if (filters.category) params.category = filters.category;
      if (filters.status) params.status = filters.status;
      if (filters.date_from) params.date_from = filters.date_from;
      if (filters.date_to) params.date_to = filters.date_to;

      const response = await api.get(`/export/${format.id}`, {
        params,
        responseType: "blob", // tells axios to treat response as binary
      });

      // Create a temporary download link and click it
      const url = window.URL.createObjectURL(
        new Blob([response.data], { type: format.mime }),
      );
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute(
        "download",
        `mailtomint_export_${new Date().toISOString().slice(0, 10)}.${format.ext}`,
      );
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      toast.success(`${format.label} downloaded!`);
    } catch {
      toast.error(`Failed to export ${format.label}`);
    } finally {
      setLoading((prev) => ({ ...prev, [format.id]: false }));
    }
  };

  return (
    <Layout>
      <div className="max-w-2xl mx-auto">
        <div className="mb-8">
          <h1 className="text-2xl font-semibold text-gray-900">Export</h1>
          <p className="text-gray-500 text-sm mt-1">
            Download your invoices in any format
          </p>
        </div>

        {/* Filters */}
        <div className="card p-5 mb-6">
          <h2 className="text-sm font-medium text-gray-700 mb-4">
            Filter export
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Category</label>
              <select
                className="input"
                value={filters.category}
                onChange={(e) =>
                  setFilters({ ...filters, category: e.target.value })
                }
              >
                <option value="">All categories</option>
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
              <label className="label">Status</label>
              <select
                className="input"
                value={filters.status}
                onChange={(e) =>
                  setFilters({ ...filters, status: e.target.value })
                }
              >
                <option value="">All statuses</option>
                <option value="pending">Pending</option>
                <option value="processed">Processed</option>
              </select>
            </div>
            <div>
              <label className="label">From date</label>
              <input
                type="date"
                className="input"
                value={filters.date_from}
                onChange={(e) =>
                  setFilters({ ...filters, date_from: e.target.value })
                }
              />
            </div>
            <div>
              <label className="label">To date</label>
              <input
                type="date"
                className="input"
                value={filters.date_to}
                onChange={(e) =>
                  setFilters({ ...filters, date_to: e.target.value })
                }
              />
            </div>
          </div>
        </div>

        {/* Export format cards */}
        <div className="space-y-3">
          {exportFormats.map((format) => (
            <div key={format.id} className="card p-5 flex items-center gap-4">
              <div
                className={`w-11 h-11 rounded-xl flex items-center justify-center border ${format.color} flex-shrink-0`}
              >
                <format.icon size={20} />
              </div>
              <div className="flex-1">
                <p className="font-medium text-gray-900">{format.label}</p>
                <p className="text-sm text-gray-500 mt-0.5">
                  {format.description}
                </p>
              </div>
              <button
                onClick={() => handleExport(format)}
                disabled={loading[format.id]}
                className="btn-primary flex items-center gap-2 text-sm flex-shrink-0"
              >
                <Download size={14} />
                {loading[format.id] ? "Generating..." : "Download"}
              </button>
            </div>
          ))}
        </div>

        <p className="text-xs text-gray-400 text-center mt-6">
          Exported files include all invoices matching the filters above.
          Flagged invoices are highlighted in red.
        </p>
      </div>
    </Layout>
  );
}
