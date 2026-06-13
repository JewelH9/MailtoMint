import { useState, useEffect } from "react";
import {
  User,
  Mail,
  Lock,
  Trash2,
  Copy,
  Check,
  ShieldCheck,
  Calendar,
  FileText,
  TrendingUp,
  AlertTriangle,
} from "lucide-react";
import Layout from "../components/Layout";
import api from "../api/client";
import useAuthStore from "../store/authStore";
import toast from "react-hot-toast";

export default function Settings() {
  const { user, updateUser, logout } = useAuthStore();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  // Form states
  const [nameForm, setNameForm] = useState({ full_name: "" });
  const [passForm, setPassForm] = useState({
    current_password: "",
    new_password: "",
    confirm: "",
  });
  const [nameLoading, setNameLoading] = useState(false);
  const [passLoading, setPassLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteInput, setDeleteInput] = useState("");

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/settings/profile");
      setProfile(data);
      setNameForm({ full_name: data.full_name });
    } catch {
      toast.error("Failed to load profile");
    } finally {
      setLoading(false);
    }
  };

  const handleNameUpdate = async (e) => {
    e.preventDefault();
    setNameLoading(true);
    try {
      const { data } = await api.patch("/settings/profile", nameForm);
      updateUser({ full_name: data.full_name });
      toast.success("Name updated");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Update failed");
    } finally {
      setNameLoading(false);
    }
  };

  const handlePasswordChange = async (e) => {
    e.preventDefault();
    if (passForm.new_password !== passForm.confirm) {
      toast.error("New passwords do not match");
      return;
    }
    setPassLoading(true);
    try {
      await api.post("/settings/change-password", {
        current_password: passForm.current_password,
        new_password: passForm.new_password,
      });
      toast.success("Password changed successfully");
      setPassForm({ current_password: "", new_password: "", confirm: "" });
    } catch (err) {
      toast.error(err.response?.data?.detail || "Password change failed");
    } finally {
      setPassLoading(false);
    }
  };

  const handleCopyAlias = () => {
    navigator.clipboard.writeText(profile?.unique_email_alias || "");
    setCopied(true);
    toast.success("Email alias copied!");
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDeleteAccount = async () => {
    if (deleteInput !== user?.email) {
      toast.error("Email does not match");
      return;
    }
    try {
      await api.delete("/settings/account");
      toast.success("Account deleted");
      logout();
    } catch {
      toast.error("Failed to delete account");
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center py-24 text-gray-400">
          Loading...
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-2xl mx-auto">
        <div className="mb-8">
          <h1 className="text-2xl font-semibold text-gray-900">Settings</h1>
          <p className="text-gray-500 text-sm mt-1">Manage your account</p>
        </div>

        {/* Account stats */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          {[
            {
              label: "Total invoices",
              value: profile?.stats?.total_invoices ?? 0,
              icon: FileText,
              color: "bg-blue-50 text-blue-600",
            },
            {
              label: "Total spend",
              value: `₹${(profile?.stats?.total_spend || 0).toLocaleString()}`,
              icon: TrendingUp,
              color: "bg-green-50 text-green-600",
            },
            {
              label: "Member since",
              value: profile?.created_at
                ? new Date(profile.created_at).toLocaleDateString("en-IN", {
                    month: "short",
                    year: "numeric",
                  })
                : "—",
              icon: Calendar,
              color: "bg-purple-50 text-purple-600",
            },
          ].map(({ label, value, icon: Icon, color }) => (
            <div key={label} className="card p-4">
              <div className="flex items-center gap-3">
                <div
                  className={`w-8 h-8 rounded-lg flex items-center justify-center ${color}`}
                >
                  <Icon size={15} />
                </div>
                <div>
                  <p className="text-xs text-gray-500">{label}</p>
                  <p className="text-sm font-semibold text-gray-900">{value}</p>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Profile section */}
        <div className="card p-6 mb-4">
          <div className="flex items-center gap-2 mb-5">
            <User size={16} className="text-gray-500" />
            <h2 className="text-sm font-medium text-gray-700">Profile</h2>
          </div>

          {/* Avatar + email (read only) */}
          <div className="flex items-center gap-4 mb-5 pb-5 border-b border-gray-100">
            <div className="w-14 h-14 rounded-full bg-brand-100 flex items-center justify-center text-brand-700 text-xl font-semibold">
              {profile?.full_name?.[0]?.toUpperCase() || "U"}
            </div>
            <div>
              <p className="font-medium text-gray-900">{profile?.full_name}</p>
              <p className="text-sm text-gray-500">{profile?.email}</p>
              <span className="badge bg-brand-50 text-brand-700 mt-1">
                {profile?.role}
              </span>
            </div>
          </div>

          {/* Edit name form */}
          <form onSubmit={handleNameUpdate} className="flex gap-3">
            <div className="flex-1">
              <label className="label">Display name</label>
              <input
                className="input"
                value={nameForm.full_name}
                onChange={(e) => setNameForm({ full_name: e.target.value })}
                placeholder="Your full name"
                required
              />
            </div>
            <div className="flex items-end">
              <button
                type="submit"
                disabled={nameLoading}
                className="btn-primary px-5"
              >
                {nameLoading ? "Saving..." : "Save"}
              </button>
            </div>
          </form>
        </div>

        {/* Email alias section */}
        <div className="card p-6 mb-4">
          <div className="flex items-center gap-2 mb-2">
            <Mail size={16} className="text-gray-500" />
            <h2 className="text-sm font-medium text-gray-700">
              MailToMint inbox
            </h2>
            <span className="badge bg-brand-50 text-brand-700 ml-auto">
              Auto-processing
            </span>
          </div>

          <p className="text-xs text-gray-500 mb-4">
            Forward or CC any invoice email to your unique address below.
            Attachments are automatically extracted, OCR'd, and added to your
            dashboard within 5 minutes — no manual upload needed.
          </p>

          {/* Alias display */}
          <div className="flex items-center gap-3 p-3 bg-brand-50 rounded-lg border border-brand-100 mb-4">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-brand-800 truncate">
                {profile?.unique_email_alias || "—"}
              </p>
            </div>
            <button
              onClick={handleCopyAlias}
              className="flex items-center gap-1.5 text-xs text-brand-700 hover:text-brand-900 font-medium flex-shrink-0"
            >
              {copied ? <Check size={13} /> : <Copy size={13} />}
              {copied ? "Copied!" : "Copy"}
            </button>
          </div>

          {/* How to use steps */}
          <div className="space-y-2 mb-4">
            {[
              "Vendor emails you an invoice PDF",
              `You forward it to ${profile?.unique_email_alias || "your alias"}`,
              "MailToMint detects the attachment automatically",
              "Invoice appears in your dashboard within 5 minutes",
            ].map((step, i) => (
              <div
                key={i}
                className="flex items-start gap-3 text-xs text-gray-500"
              >
                <span className="w-5 h-5 rounded-full bg-brand-100 text-brand-700 flex items-center justify-center font-medium flex-shrink-0 mt-0.5">
                  {i + 1}
                </span>
                {step}
              </div>
            ))}
          </div>

          {/* Manual trigger button */}
          <button
            onClick={async () => {
              try {
                const { data } = await api.post("/settings/check-email");
                toast.success(data.message);
              } catch {
                toast.error("Check failed — verify IMAP settings");
              }
            }}
            className="btn-secondary text-sm flex items-center gap-2"
          >
            <Mail size={14} />
            Check inbox now
          </button>
        </div>

        {/* Change password section */}
        <div className="card p-6 mb-4">
          <div className="flex items-center gap-2 mb-5">
            <Lock size={16} className="text-gray-500" />
            <h2 className="text-sm font-medium text-gray-700">
              Change password
            </h2>
          </div>

          <form onSubmit={handlePasswordChange} className="space-y-4">
            <div>
              <label className="label">Current password</label>
              <input
                type="password"
                className="input"
                placeholder="••••••••"
                value={passForm.current_password}
                onChange={(e) =>
                  setPassForm({ ...passForm, current_password: e.target.value })
                }
                required
              />
            </div>
            <div>
              <label className="label">New password</label>
              <input
                type="password"
                className="input"
                placeholder="Min 8 chars, 1 uppercase, 1 number"
                value={passForm.new_password}
                onChange={(e) =>
                  setPassForm({ ...passForm, new_password: e.target.value })
                }
                required
              />
            </div>
            <div>
              <label className="label">Confirm new password</label>
              <input
                type="password"
                className="input"
                placeholder="••••••••"
                value={passForm.confirm}
                onChange={(e) =>
                  setPassForm({ ...passForm, confirm: e.target.value })
                }
                required
              />
            </div>
            <button
              type="submit"
              disabled={passLoading}
              className="btn-primary"
            >
              {passLoading ? "Changing..." : "Change password"}
            </button>
          </form>
        </div>

        {/* Danger zone */}
        <div className="card p-6 border-red-100">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle size={16} className="text-red-500" />
            <h2 className="text-sm font-medium text-red-600">Danger zone</h2>
          </div>
          <p className="text-xs text-gray-500 mb-4">
            Deleting your account permanently removes all invoices, data, and
            files. This cannot be undone.
          </p>

          {!showDeleteConfirm ? (
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="flex items-center gap-2 text-sm text-red-600 hover:text-red-700 font-medium border border-red-200 hover:border-red-300 px-4 py-2 rounded-lg transition-colors"
            >
              <Trash2 size={14} />
              Delete my account
            </button>
          ) : (
            <div className="space-y-3 p-4 bg-red-50 rounded-lg border border-red-100">
              <p className="text-sm text-red-700 font-medium">
                Type your email to confirm:{" "}
                <span className="font-mono">{user?.email}</span>
              </p>
              <input
                className="input border-red-200 focus:ring-red-400"
                placeholder="Enter your email"
                value={deleteInput}
                onChange={(e) => setDeleteInput(e.target.value)}
              />
              <div className="flex gap-2">
                <button
                  onClick={handleDeleteAccount}
                  className="bg-red-600 hover:bg-red-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
                >
                  Permanently delete
                </button>
                <button
                  onClick={() => {
                    setShowDeleteConfirm(false);
                    setDeleteInput("");
                  }}
                  className="btn-secondary text-sm"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
