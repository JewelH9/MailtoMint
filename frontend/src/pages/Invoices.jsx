import { useState, useEffect } from "react";
import { FileText, Plus, Trash2, RefreshCw } from "lucide-react";
import Layout from "../components/Layout";
import UploadZone from "../components/UploadZone";
import api from "../api/client";
import toast from "react-hot-toast";

const statusColors = {
  pending: "bg-yellow-50 text-yellow-700",
  processed: "bg-green-50 text-green-700",
  flagged: "bg-red-50 text-red-700",
};

const categoryColors = {
  travel: "bg-blue-50 text-blue-700",
  food: "bg-orange-50 text-orange-700",
  office: "bg-purple-50 text-purple-700",
  utilities: "bg-teal-50 text-teal-700",
  marketing: "bg-pink-50 text-pink-700",
  healthcare: "bg-green-50 text-green-700",
  subscription: "bg-indigo-50 text-indigo-700",
};

export default function Invoices() {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showUpload, setShowUpload] = useState(false);

  const fetchInvoices = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/invoices");
      setInvoices(data);
    } catch {
      toast.error("Failed to load invoices");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInvoices();
  }, []);

  const handleUploadSuccess = (newInvoice) => {
    setInvoices((prev) => [newInvoice, ...prev]);
    setShowUpload(false);

    // Auto-refresh after 8 seconds to show OCR results
    setTimeout(() => {
      fetchInvoices();
    }, 8000);

    toast("Processing invoice with AI...", { icon: "🤖" });
  };

  const handleDelete = async (id) => {
    if (!confirm("Delete this invoice?")) return;
    try {
      await api.delete(`/invoices/${id}`);
      setInvoices((prev) => prev.filter((inv) => inv.id !== id));
      toast.success("Invoice deleted");
    } catch {
      toast.error("Failed to delete");
    }
  };

  return (
    <Layout>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Invoices</h1>
          <p className="text-gray-500 text-sm mt-1">
            {invoices.length} total invoices
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={fetchInvoices}
            className="btn-secondary flex items-center gap-2"
          >
            <RefreshCw size={15} />
            Refresh
          </button>
          <button
            onClick={() => setShowUpload(!showUpload)}
            className="btn-primary flex items-center gap-2"
          >
            <Plus size={15} />
            Upload Invoice
          </button>
        </div>
      </div>

      {/* Upload zone — toggles on button click */}
      {showUpload && (
        <div className="card p-5 mb-6">
          <h2 className="text-sm font-medium text-gray-700 mb-3">
            Upload a new invoice
          </h2>
          <UploadZone onUploadSuccess={handleUploadSuccess} />
        </div>
      )}

      {/* Invoice table */}
      <div className="card overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16 text-gray-400">
            <RefreshCw size={18} className="animate-spin mr-2" />
            Loading invoices...
          </div>
        ) : invoices.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-gray-400">
            <FileText size={36} className="mb-3 opacity-40" />
            <p className="font-medium">No invoices yet</p>
            <p className="text-sm mt-1">
              Upload your first invoice to get started
            </p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">
                  File
                </th>
                <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">
                  Vendor
                </th>
                <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">
                  Amount
                </th>
                <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">
                  Category
                </th>
                <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">
                  Status
                </th>
                <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">
                  Date
                </th>
                <th className="px-5 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {invoices.map((inv) => (
                <tr key={inv.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-2">
                      <FileText
                        size={15}
                        className="text-gray-400 flex-shrink-0"
                      />
                      <span className="text-gray-700 truncate max-w-[140px]">
                        {inv.file_name || "Unnamed"}
                      </span>
                    </div>
                  </td>
                  <td className="px-5 py-3.5 text-gray-600">
                    {inv.vendor_name || (
                      <span className="text-gray-300">—</span>
                    )}
                  </td>
                  <td className="px-5 py-3.5 font-medium text-gray-900">
                    {inv.total_amount ? (
                      `₹${inv.total_amount.toLocaleString()}`
                    ) : (
                      <span className="text-gray-300 font-normal">—</span>
                    )}
                  </td>
                  <td className="px-5 py-3.5">
                    {inv.category ? (
                      <span
                        className={`badge ${categoryColors[inv.category] || "bg-gray-100 text-gray-600"}`}
                      >
                        {inv.category}
                      </span>
                    ) : (
                      <span className="text-gray-300">—</span>
                    )}
                  </td>
                  <td className="px-5 py-3.5">
                    <span
                      className={`badge ${statusColors[inv.status] || "bg-gray-100 text-gray-600"}`}
                    >
                      {inv.status}
                    </span>
                  </td>
                  <td className="px-5 py-3.5 text-gray-500">
                    {inv.invoice_date ||
                      new Date(inv.created_at).toLocaleDateString("en-IN")}
                  </td>
                  <td className="px-5 py-3.5">
                    <button
                      onClick={() => handleDelete(inv.id)}
                      className="text-gray-300 hover:text-red-500 transition-colors"
                    >
                      <Trash2 size={15} />
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
