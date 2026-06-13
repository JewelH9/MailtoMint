import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
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
import Layout from "../components/Layout";
import api from "../api/client";

const COLORS = [
  "#16a34a",
  "#3b82f6",
  "#f97316",
  "#8b5cf6",
  "#ec4899",
  "#14b8a6",
  "#6366f1",
  "#94a3b8",
];

export default function Analytics() {
  const [monthly, setMonthly] = useState([]);
  const [categories, setCategories] = useState([]);
  const [vendors, setVendors] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get("/analytics/monthly"),
      api.get("/analytics/categories"),
      api.get("/analytics/vendors"),
    ])
      .then(([m, c, v]) => {
        setMonthly(m.data);
        setCategories(c.data);
        setVendors(v.data);
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <Layout>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Analytics</h1>
        <p className="text-gray-500 text-sm mt-1">
          Detailed breakdown of your spending
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        {/* Spending trend */}
        <div className="card p-5">
          <h2 className="text-sm font-medium text-gray-700 mb-4">
            Spending trend
          </h2>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={monthly}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis
                dataKey="month"
                tick={{ fontSize: 12, fill: "#94a3b8" }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 12, fill: "#94a3b8" }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
              />
              <Tooltip
                formatter={(v) => [`₹${v.toLocaleString()}`, "Spend"]}
                contentStyle={{
                  fontSize: 13,
                  borderRadius: 8,
                  border: "1px solid #e2e8f0",
                }}
              />
              <Line
                type="monotone"
                dataKey="amount"
                stroke="#16a34a"
                strokeWidth={2}
                dot={{ r: 4, fill: "#16a34a" }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Category donut */}
        <div className="card p-5">
          <h2 className="text-sm font-medium text-gray-700 mb-4">
            Spend by category
          </h2>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={categories}
                dataKey="amount"
                nameKey="category"
                cx="50%"
                cy="50%"
                outerRadius={80}
                innerRadius={45}
              >
                {categories.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                formatter={(v) => [`₹${v.toLocaleString()}`, ""]}
                contentStyle={{ fontSize: 13, borderRadius: 8 }}
              />
              <Legend
                iconType="circle"
                iconSize={8}
                wrapperStyle={{ fontSize: 12 }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Vendor bar chart */}
      <div className="card p-5">
        <h2 className="text-sm font-medium text-gray-700 mb-4">
          Spend by vendor
        </h2>
        {vendors.length === 0 ? (
          <div className="flex items-center justify-center h-32 text-gray-300 text-sm">
            No vendor data yet
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={vendors} layout="vertical" barSize={18}>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="#f1f5f9"
                horizontal={false}
              />
              <XAxis
                type="number"
                tick={{ fontSize: 12, fill: "#94a3b8" }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
              />
              <YAxis
                type="category"
                dataKey="vendor"
                width={160}
                tick={{ fontSize: 12, fill: "#64748b" }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                formatter={(v) => [`₹${v.toLocaleString()}`, "Spend"]}
                contentStyle={{
                  fontSize: 13,
                  borderRadius: 8,
                  border: "1px solid #e2e8f0",
                }}
              />
              <Bar dataKey="amount" fill="#16a34a" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </Layout>
  );
}
