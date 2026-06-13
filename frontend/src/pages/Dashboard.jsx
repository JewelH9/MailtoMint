import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import {
  FileText,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  Zap,
  RefreshCw,
} from "lucide-react";
import Layout from "../components/Layout";
import useAuthStore from "../store/authStore";
import api from "../api/client";

const CATEGORY_COLORS = {
  travel: "#3b82f6",
  food: "#f97316",
  office: "#8b5cf6",
  utilities: "#14b8a6",
  marketing: "#ec4899",
  healthcare: "#22c55e",
  subscription: "#6366f1",
  other: "#94a3b8",
  uncategorized: "#cbd5e1",
};

function StatCard({ label, value, sub, icon: Icon, color }) {
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-500">{label}</p>
          <p className="text-2xl font-semibold text-gray-900 mt-1">{value}</p>
          {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
        </div>
        <div
          className={`w-9 h-9 rounded-lg flex items-center justify-center ${color}`}
        >
          <Icon size={17} />
        </div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { user } = useAuthStore();
  const [summary, setSummary] = useState(null);
  const [monthly, setMonthly] = useState([]);
  const [categories, setCategories] = useState([]);
  const [vendors, setVendors] = useState([]);
  const [insights, setInsights] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAll();
  }, []);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [summaryRes, monthlyRes, catRes, vendorRes] = await Promise.all([
        api.get("/analytics/summary"),
        api.get("/analytics/monthly"),
        api.get("/analytics/categories"),
        api.get("/analytics/vendors"),
      ]);
      setSummary(summaryRes.data);
      setMonthly(monthlyRes.data);
      setCategories(catRes.data);
      setVendors(vendorRes.data);
    } catch {
      // silently fail — charts just stay empty
    } finally {
      setLoading(false);
    }

    // Load insights separately — can be slow
    try {
      const { data } = await api.get("/analytics/insights");
      setInsights(data.insights);
    } catch {
      setInsights("");
    }
  };

  const formatCurrency = (val) =>
    val >= 1000 ? `₹${(val / 1000).toFixed(1)}k` : `₹${val}`;

  return (
    <Layout>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">
            Good morning, {user?.full_name?.split(" ")[0]} 👋
          </h1>
          <p className="text-gray-500 text-sm mt-1">
            Here's your financial overview
          </p>
        </div>
        <button
          onClick={fetchAll}
          className="btn-secondary flex items-center gap-2 text-sm"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <StatCard
          label="Total Invoices"
          value={summary?.total_invoices ?? "—"}
          sub={`${summary?.processed_count ?? 0} processed`}
          icon={FileText}
          color="bg-blue-50 text-blue-600"
        />
        <StatCard
          label="Total Spend"
          value={summary ? formatCurrency(summary.total_spend) : "—"}
          sub="all time"
          icon={TrendingUp}
          color="bg-green-50 text-green-600"
        />
        <StatCard
          label="This Month"
          value={summary ? formatCurrency(summary.this_month_spend) : "—"}
          sub="current month"
          icon={Zap}
          color="bg-purple-50 text-purple-600"
        />
        <StatCard
          label="Flagged"
          value={summary?.flagged_count ?? "—"}
          sub="need review"
          icon={AlertTriangle}
          color="bg-red-50 text-red-500"
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        {/* Monthly trend */}
        <div className="card p-5 col-span-2">
          <h2 className="text-sm font-medium text-gray-700 mb-4">
            Monthly spending
          </h2>
          {monthly.length === 0 ? (
            <div className="flex items-center justify-center h-40 text-gray-300 text-sm">
              No data yet
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={monthly} barSize={28}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis
                  dataKey="month"
                  tick={{ fontSize: 12, fill: "#94a3b8" }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tickFormatter={formatCurrency}
                  tick={{ fontSize: 12, fill: "#94a3b8" }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  formatter={(val) => [`₹${val.toLocaleString()}`, "Spend"]}
                  contentStyle={{
                    fontSize: 13,
                    borderRadius: 8,
                    border: "1px solid #e2e8f0",
                    boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
                  }}
                />
                <Bar dataKey="amount" fill="#16a34a" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Category pie */}
        <div className="card p-5">
          <h2 className="text-sm font-medium text-gray-700 mb-4">
            By category
          </h2>
          {categories.length === 0 ? (
            <div className="flex items-center justify-center h-40 text-gray-300 text-sm">
              No data yet
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={categories}
                  dataKey="amount"
                  nameKey="category"
                  cx="50%"
                  cy="50%"
                  outerRadius={70}
                  innerRadius={35}
                >
                  {categories.map((entry) => (
                    <Cell
                      key={entry.category}
                      fill={CATEGORY_COLORS[entry.category] || "#94a3b8"}
                    />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(val) => [`₹${val.toLocaleString()}`, ""]}
                  contentStyle={{ fontSize: 13, borderRadius: 8 }}
                />
                <Legend
                  iconType="circle"
                  iconSize={8}
                  wrapperStyle={{ fontSize: 12 }}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Vendors + AI insights row */}
      <div className="grid grid-cols-3 gap-4">
        {/* Top vendors */}
        <div className="card p-5 col-span-2">
          <h2 className="text-sm font-medium text-gray-700 mb-4">
            Top vendors
          </h2>
          {vendors.length === 0 ? (
            <div className="flex items-center justify-center h-24 text-gray-300 text-sm">
              No vendors yet
            </div>
          ) : (
            <div className="space-y-3">
              {vendors.slice(0, 5).map((v, i) => {
                const maxAmount = vendors[0].amount;
                const pct = maxAmount > 0 ? (v.amount / maxAmount) * 100 : 0;
                return (
                  <div key={v.vendor}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-700 font-medium truncate max-w-[200px]">
                        {v.vendor}
                      </span>
                      <span className="text-gray-500 ml-2 flex-shrink-0">
                        ₹{v.amount.toLocaleString()}
                        <span className="text-gray-300 ml-1">
                          · {v.count} inv
                        </span>
                      </span>
                    </div>
                    <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-brand-500 rounded-full transition-all duration-500"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* AI insights */}
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-6 h-6 rounded-md bg-brand-600 flex items-center justify-center">
              <Zap size={12} className="text-white" />
            </div>
            <h2 className="text-sm font-medium text-gray-700">AI Insights</h2>
          </div>
          {insights ? (
            <div className="space-y-3">
              {insights
                .split("\n")
                .filter(Boolean)
                .map((line, i) => (
                  <p key={i} className="text-sm text-gray-600 leading-relaxed">
                    {line}
                  </p>
                ))}
            </div>
          ) : (
            <div className="text-sm text-gray-400">
              Process some invoices to unlock AI insights.
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
