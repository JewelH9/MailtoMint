import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, File, X, CheckCircle, AlertCircle } from "lucide-react";
import api from "../api/client";
import toast from "react-hot-toast";

export default function UploadZone({ onUploadSuccess }) {
  const [uploading, setUploading] = useState(false);
  const [uploadedFile, setUploadedFile] = useState(null);

  const onDrop = useCallback(
    async (acceptedFiles, rejectedFiles) => {
      if (rejectedFiles.length > 0) {
        toast.error("Only PDF, JPG, PNG files under 10MB are allowed");
        return;
      }

      const file = acceptedFiles[0];
      if (!file) return;

      setUploadedFile({ name: file.name, status: "uploading" });
      setUploading(true);

      const formData = new FormData();
      formData.append("file", file);

      try {
        const { data } = await api.post("/invoices/upload", formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });

        setUploadedFile({ name: file.name, status: "success" });
        toast.success("Invoice uploaded successfully!");
        onUploadSuccess?.(data);
      } catch (err) {
        setUploadedFile({ name: file.name, status: "error" });
        toast.error(err.response?.data?.detail || "Upload failed");
      } finally {
        setUploading(false);
      }
    },
    [onUploadSuccess],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "image/jpeg": [".jpg", ".jpeg"],
      "image/png": [".png"],
    },
    maxSize: 10 * 1024 * 1024,
    multiple: false,
  });

  const reset = () => setUploadedFile(null);

  return (
    <div>
      {!uploadedFile ? (
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors ${
            isDragActive
              ? "border-brand-500 bg-brand-50"
              : "border-gray-200 hover:border-brand-400 hover:bg-gray-50"
          }`}
        >
          <input {...getInputProps()} />
          <div className="flex flex-col items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-brand-50 flex items-center justify-center">
              <Upload size={22} className="text-brand-600" />
            </div>
            <div>
              <p className="font-medium text-gray-900">
                {isDragActive ? "Drop it here" : "Drag & drop your invoice"}
              </p>
              <p className="text-sm text-gray-500 mt-1">
                or{" "}
                <span className="text-brand-600 font-medium">browse files</span>
              </p>
            </div>
            <p className="text-xs text-gray-400">PDF, JPG, PNG up to 10MB</p>
          </div>
        </div>
      ) : (
        <div className="border rounded-xl p-5 flex items-center gap-4">
          <div className="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0">
            <File size={18} className="text-gray-500" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-900 truncate">
              {uploadedFile.name}
            </p>
            <p
              className={`text-xs mt-0.5 ${
                uploadedFile.status === "uploading"
                  ? "text-gray-500"
                  : uploadedFile.status === "success"
                    ? "text-green-600"
                    : "text-red-500"
              }`}
            >
              {uploadedFile.status === "uploading" && "Uploading..."}
              {uploadedFile.status === "success" && "Uploaded successfully"}
              {uploadedFile.status === "error" && "Upload failed"}
            </p>
          </div>
          {uploadedFile.status === "success" && (
            <CheckCircle size={18} className="text-green-500 flex-shrink-0" />
          )}
          {uploadedFile.status === "error" && (
            <AlertCircle size={18} className="text-red-500 flex-shrink-0" />
          )}
          {uploadedFile.status !== "uploading" && (
            <button
              onClick={reset}
              className="text-gray-400 hover:text-gray-600"
            >
              <X size={16} />
            </button>
          )}
        </div>
      )}
    </div>
  );
}
