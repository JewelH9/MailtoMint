import { useEffect, useState } from "react";
import { AlertTriangle, ShieldCheck, Copy, RefreshCw } from "lucide-react";
import Layout from "../components/Layout";
import api from "../api/client";
import toast from "react-hot-toast";

const riskColor = (score) => {
  if (score >= 0.7) return "text-red-600 bg-red-50";
  if (score >= 0.4) return "text-yellow-600 bg-yellow-50";
  return "text-green-600 bg-green-50";
};

const riskLabel = (score) => {
  if (score >= 0.7) return "High risk";
  if (score >= 0.4) return "Medium risk";
  return "Low risk";
};

export default function Fraud() {
  const [summary, setSummary] = useState(null);
  const [flagged, setFlagged] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [summaryRes, flaggedRes] = await Promise.all([
        api.get("/fraud/summary"),
        api.get("/fraud/flags"),
      ]);
      setSummary(summaryRes.data);
      setFlagged(flaggedRes.data);
    } catch {
      toast.error("Failed to load fraud data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleRecheck = async (id) => {
    try {
      await api.post(`/fraud/recheck/${id}`);
      toast.success("Re-check complete");
      fetchData();
    } catch {
      toast.error("Re-check failed");
    }
  };

  return (
    <Layout>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">
            Fraud Detection
          </h1>
          <p className="text-gray-500 text-sm mt-1">
            AI-powered anomaly and duplicate detection
          </p>
        </div>
        <button
          onClick={fetchData}
          className="btn-secondary flex items-center gap-2 text-sm"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {[
          {
            label: "Flagged invoices",
            value: summary?.flagged_count ?? "—",
            sub: `${summary?.flag_rate_pct ?? 0}% of total`,
            color: "bg-red-50 text-red-500",
            icon: AlertTriangle,
          },
          {
            label: "Duplicates found",
            value: summary?.duplicate_count ?? "—",
            sub: "exact or fuzzy matches",
            color: "bg-orange-50 text-orange-500",
            icon: Copy,
          },
          {
            label: "High risk",
            value: summary?.high_risk_count ?? "—",
            sub: "score ≥ 0.7",
            color: "bg-yellow-50 text-yellow-600",
            icon: AlertTriangle,
          },
          {
            label: "Avg fraud score",
            value: summary ? summary.average_fraud_score.toFixed(2) : "—",
            sub: "0 = clean, 1 = fraud",
            color: "bg-green-50 text-green-600",
            icon: ShieldCheck,
          },
        ].map(({ label, value, sub, color, icon: Icon }) => (
          <div key={label} className="card p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-gray-500">{label}</p>
                <p className="text-2xl font-semibold text-gray-900 mt-1">
                  {value}
                </p>
                <p className="text-xs text-gray-400 mt-0.5">{sub}</p>
              </div>
              <div
                className={`w-9 h-9 rounded-lg flex items-center justify-center ${color}`}
              >
                <Icon size={17} />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Flagged invoices table */}
      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100">
          <h2 className="text-sm font-medium text-gray-700">
            Flagged invoices
          </h2>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16 text-gray-400">
            <RefreshCw size={18} className="animate-spin mr-2" />
            Analyzing...
          </div>
        ) : flagged.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-gray-400">
            <ShieldCheck size={36} className="mb-3 opacity-40" />
            <p className="font-medium">No suspicious invoices found</p>
            <p className="text-sm mt-1">All invoices look clean</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">
                  Invoice
                </th>
                <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">
                  Vendor
                </th>
                <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">
                  Amount
                </th>
                <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">
                  Risk
                </th>
                <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">
                  Score
                </th>
                <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">
                  Flags
                </th>
                <th className="px-5 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {flagged.map((inv) => (
                <tr key={inv.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3.5 text-gray-700">
                    {inv.file_name || "Unnamed"}
                  </td>
                  <td className="px-5 py-3.5 text-gray-600">
                    {inv.vendor_name || "—"}
                  </td>
                  <td className="px-5 py-3.5 font-medium text-gray-900">
                    {inv.total_amount
                      ? `₹${inv.total_amount.toLocaleString()}`
                      : "—"}
                  </td>
                  <td className="px-5 py-3.5">
                    <span className={`badge ${riskColor(inv.fraud_score)}`}>
                      {riskLabel(inv.fraud_score)}
                    </span>
                  </td>
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            inv.fraud_score >= 0.7
                              ? "bg-red-500"
                              : inv.fraud_score >= 0.4
                                ? "bg-yellow-500"
                                : "bg-green-500"
                          }`}
                          style={{ width: `${inv.fraud_score * 100}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-500">
                        {inv.fraud_score.toFixed(2)}
                      </span>
                    </div>
                  </td>
                  <td className="px-5 py-3.5">
                    {inv.is_duplicate && (
                      <span className="badge bg-orange-50 text-orange-600 mr-1">
                        duplicate
                      </span>
                    )}
                  </td>
                  <td className="px-5 py-3.5">
                    <button
                      onClick={() => handleRecheck(inv.id)}
                      className="text-xs text-brand-600 hover:underline"
                    >
                      Re-check
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </Layout>
  );
}
