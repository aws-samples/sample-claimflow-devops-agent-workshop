import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { createClaim, submitClaim, uploadDocument, CreateClaimRequest } from "../services/claims";
import {
  CheckCircleIcon,
  DocumentTextIcon,
  PhotoIcon,
  MagnifyingGlassIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";

type Step = "type" | "details" | "documents" | "review";

interface UploadedFile {
  id: string;
  file: File;
}

// Format amount in Indian numbering system
const formatINR = (amount: number): string => {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
};

// Format file size for display
const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
};

const NewClaimPage: React.FC = () => {
  const navigate = useNavigate();
  const { t } = useTranslation();

  const steps: { key: Step; labelKey: string; icon: React.FC<React.SVGProps<SVGSVGElement>> }[] = [
    { key: "type", labelKey: "common.new_claim.steps.type", icon: DocumentTextIcon },
    { key: "details", labelKey: "common.new_claim.steps.details", icon: MagnifyingGlassIcon },
    { key: "documents", labelKey: "common.new_claim.steps.documents", icon: PhotoIcon },
    { key: "review", labelKey: "common.new_claim.steps.review", icon: CheckCircleIcon },
  ];

  const claimTypes = [
    { value: "health", labelKey: "common.new_claim.type.health_label", descriptionKey: "common.new_claim.type.health_description", emoji: "\ud83c\udfe5" },
    { value: "motor", labelKey: "common.new_claim.type.motor_label", descriptionKey: "common.new_claim.type.motor_description", emoji: "\ud83d\ude97" },
    { value: "property", labelKey: "common.new_claim.type.property_label", descriptionKey: "common.new_claim.type.property_description", emoji: "\ud83c\udfe0" },
    { value: "travel", labelKey: "common.new_claim.type.travel_label", descriptionKey: "common.new_claim.type.travel_description", emoji: "\u2708\ufe0f" },
  ];

  const [currentStep, setCurrentStep] = useState<Step>("type");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);

  const [formData, setFormData] = useState({
    claim_type: "",
    amount: "",
    description: "",
    policy_number: "",
    incident_date: "",
  });

  const currentStepIndex = steps.findIndex((s) => s.key === currentStep);

  const handleNext = () => {
    const nextIndex = currentStepIndex + 1;
    if (nextIndex < steps.length) {
      setCurrentStep(steps[nextIndex].key);
    }
  };

  const handleBack = () => {
    const prevIndex = currentStepIndex - 1;
    if (prevIndex >= 0) {
      setCurrentStep(steps[prevIndex].key);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;

    const newFiles: UploadedFile[] = Array.from(files).map((file) => ({
      id: `${file.name}-${Date.now()}-${Math.random().toString(36).slice(2)}`,
      file,
    }));

    setUploadedFiles((prev) => [...prev, ...newFiles]);
    // Reset input so the same file can be selected again
    e.target.value = "";
  };

  const handleRemoveFile = (id: string) => {
    setUploadedFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const handleSubmit = async () => {
    setError("");
    setLoading(true);

    try {
      const payload: CreateClaimRequest = {
        claim_type: formData.claim_type,
        amount: parseFloat(formData.amount) || 0,
        description: formData.description || "No description provided",
        policy_number: formData.policy_number || "POL-" + Date.now().toString(36).toUpperCase(),
      };
      if (formData.incident_date) {
        payload.incident_date = formData.incident_date;
      }

      const claim = await createClaim(payload);

      // Upload any selected files
      if (uploadedFiles.length > 0) {
        for (const item of uploadedFiles) {
          try {
            await uploadDocument(claim.claim_id, item.file);
          } catch (uploadErr) {
            console.error("Failed to upload file:", item.file.name, uploadErr);
          }
        }
      }

      await submitClaim(claim.claim_id);
      navigate("/claims");
    } catch (err: any) {
      let message = t("common.new_claim.errors.create_failed");
      const detail = err?.response?.data?.detail;

      if (Array.isArray(detail)) {
        // FastAPI validation errors — parse into readable messages
        message = detail.map((e: any) => {
          const field = e.loc?.[e.loc.length - 1] || "field";
          return `${field}: ${e.msg}`;
        }).join(". ");
      } else if (typeof detail === "string") {
        message = detail;
      } else if (err?.message) {
        message = err.message;
      }

      setError(message);
      setLoading(false);
    }
  };

  const isStepValid = (): boolean => {
    switch (currentStep) {
      case "type":
        return !!formData.claim_type;
      case "details":
        return !!formData.amount && !!formData.description && formData.description.length >= 10;
      case "documents":
        return true; // Documents are optional
      case "review":
        return true;
      default:
        return false;
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{t("common.new_claim.header.title")}</h1>
        <p className="text-gray-500 mt-1">{t("common.new_claim.header.subtitle")}</p>
      </div>

      {/* Step Indicator */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-6">
        <div className="flex items-center justify-between">
          {steps.map((step, index) => {
            const isActive = index === currentStepIndex;
            const isCompleted = index < currentStepIndex;
            const StepIcon = step.icon;

            return (
              <React.Fragment key={step.key}>
                <div className="flex flex-col items-center gap-2">
                  <div
                    className={`w-10 h-10 rounded-full flex items-center justify-center transition-all ${
                      isCompleted
                        ? "bg-green-100 text-green-600"
                        : isActive
                        ? "bg-indigo-100 text-indigo-600 ring-2 ring-indigo-200"
                        : "bg-gray-100 text-gray-400"
                    }`}
                  >
                    {isCompleted ? (
                      <CheckCircleIcon className="w-5 h-5" />
                    ) : (
                      <StepIcon className="w-5 h-5" />
                    )}
                  </div>
                  <span
                    className={`text-xs font-medium ${
                      isActive ? "text-indigo-600" : isCompleted ? "text-green-600" : "text-gray-400"
                    }`}
                  >
                    {t(step.labelKey)}
                  </span>
                </div>
                {index < steps.length - 1 && (
                  <div
                    className={`flex-1 h-0.5 mx-3 ${
                      index < currentStepIndex ? "bg-green-300" : "bg-gray-200"
                    }`}
                  />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Step Content */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-8">
        {/* Step 1: Type */}
        {currentStep === "type" && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">{t("common.new_claim.type.title")}</h2>
            <p className="text-sm text-gray-500">{t("common.new_claim.type.subtitle")}</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
              {claimTypes.map((type) => (
                <button
                  key={type.value}
                  type="button"
                  onClick={() => setFormData((prev) => ({ ...prev, claim_type: type.value }))}
                  className={`p-5 rounded-xl border-2 text-left transition-all ${
                    formData.claim_type === type.value
                      ? "border-indigo-500 bg-indigo-50 ring-2 ring-indigo-200"
                      : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
                  }`}
                >
                  <div className="text-2xl mb-2">{type.emoji}</div>
                  <h3 className="font-semibold text-gray-900">{t(type.labelKey)}</h3>
                  <p className="text-xs text-gray-500 mt-1">{t(type.descriptionKey)}</p>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 2: Details */}
        {currentStep === "details" && (
          <div className="space-y-5">
            <h2 className="text-lg font-semibold text-gray-900">{t("common.new_claim.details.title")}</h2>
            <p className="text-sm text-gray-500">{t("common.new_claim.details.subtitle")}</p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="amount" className="block text-sm font-medium text-gray-700 mb-1.5">
                  {t("common.new_claim.details.amount")}
                </label>
                <input
                  id="amount"
                  type="number"
                  value={formData.amount}
                  onChange={(e) => setFormData((prev) => ({ ...prev, amount: e.target.value }))}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                  placeholder={t("common.new_claim.details.amount_placeholder")}
                  required
                  min="1"
                />
              </div>
              <div>
                <label htmlFor="policy_number" className="block text-sm font-medium text-gray-700 mb-1.5">
                  {t("common.new_claim.details.policy_number")}
                </label>
                <input
                  id="policy_number"
                  type="text"
                  value={formData.policy_number}
                  onChange={(e) => setFormData((prev) => ({ ...prev, policy_number: e.target.value }))}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                  placeholder={t("common.new_claim.details.policy_number_placeholder")}
                />
              </div>
            </div>

            <div>
              <label htmlFor="incident_date" className="block text-sm font-medium text-gray-700 mb-1.5">
                {t("common.new_claim.details.incident_date")}
              </label>
              <input
                id="incident_date"
                type="date"
                value={formData.incident_date}
                onChange={(e) => setFormData((prev) => ({ ...prev, incident_date: e.target.value }))}
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-indigo-500 focus:border-indigo-500 outline-none"
              />
            </div>

            <div>
              <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1.5">
                {t("common.new_claim.details.description")}
              </label>
              <textarea
                id="description"
                value={formData.description}
                onChange={(e) => setFormData((prev) => ({ ...prev, description: e.target.value }))}
                rows={4}
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-indigo-500 focus:border-indigo-500 outline-none resize-none"
                placeholder={t("common.new_claim.details.description_placeholder")}
                required
              />
              {formData.description.length > 0 && formData.description.length < 10 && (
                <p className="mt-1 text-xs text-red-500">
                  {t("common.new_claim.details.description_min_length", { count: formData.description.length })}
                </p>
              )}
            </div>
          </div>
        )}

        {/* Step 3: Documents */}
        {currentStep === "documents" && (
          <div className="space-y-5">
            <h2 className="text-lg font-semibold text-gray-900">{t("common.new_claim.documents.title")}</h2>
            <p className="text-sm text-gray-500">{t("common.new_claim.documents.subtitle")}</p>

            {/* File Input */}
            <div>
              <label htmlFor="file-upload" className="block text-sm font-medium text-gray-700 mb-1.5">
                {t("common.new_claim.documents.select_files")}
              </label>
              <input
                id="file-upload"
                type="file"
                multiple
                onChange={handleFileSelect}
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-indigo-500 focus:border-indigo-500 outline-none file:mr-4 file:py-1 file:px-3 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
              />
            </div>

            {/* Selected Files List */}
            {uploadedFiles.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm font-medium text-gray-700">
                  {t("common.new_claim.documents.selected_files", { count: uploadedFiles.length })}
                </p>
                <ul className="divide-y divide-gray-100 border border-gray-200 rounded-lg overflow-hidden">
                  {uploadedFiles.map((item) => (
                    <li key={item.id} className="flex items-center justify-between px-4 py-3 bg-white hover:bg-gray-50">
                      <div className="flex items-center gap-3 min-w-0">
                        <DocumentTextIcon className="w-5 h-5 text-gray-400 flex-shrink-0" />
                        <div className="min-w-0">
                          <p className="text-sm text-gray-900 truncate">{item.file.name}</p>
                          <p className="text-xs text-gray-500">{formatFileSize(item.file.size)}</p>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleRemoveFile(item.id)}
                        className="ml-3 p-1 text-gray-400 hover:text-red-500 rounded transition-colors"
                        aria-label={t("common.new_claim.documents.remove_aria", { name: item.file.name })}
                      >
                        <XMarkIcon className="w-4 h-4" />
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Info message */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-sm text-blue-700">
                <strong>{t("common.new_claim.documents.note_label")}</strong>{" "}
                {t("common.new_claim.documents.note_text")}
              </p>
            </div>
          </div>
        )}

        {/* Step 4: Review */}
        {currentStep === "review" && (
          <div className="space-y-5">
            <h2 className="text-lg font-semibold text-gray-900">{t("common.new_claim.review.title")}</h2>
            <p className="text-sm text-gray-500">{t("common.new_claim.review.subtitle")}</p>

            <div className="bg-gray-50 rounded-xl p-6 space-y-4">
              <ReviewRow label={t("common.new_claim.review.claim_type")} value={formData.claim_type} capitalize />
              <ReviewRow label={t("common.new_claim.review.amount")} value={formData.amount ? formatINR(parseFloat(formData.amount)) : "--"} />
              <ReviewRow label={t("common.new_claim.review.policy_number")} value={formData.policy_number || t("common.new_claim.review.not_provided")} />
              <ReviewRow label={t("common.new_claim.review.incident_date")} value={formData.incident_date || t("common.new_claim.review.not_provided")} />
              <ReviewRow
                label={t("common.new_claim.review.documents")}
                value={uploadedFiles.length > 0 ? t("common.new_claim.review.file_count", { count: uploadedFiles.length }) : t("common.new_claim.review.no_documents")}
              />
              <div className="pt-2 border-t border-gray-200">
                <p className="text-sm font-medium text-gray-700 mb-1">{t("common.new_claim.review.description")}</p>
                <p className="text-sm text-gray-600">{formData.description || t("common.new_claim.review.no_description")}</p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Navigation Buttons */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={handleBack}
          disabled={currentStepIndex === 0}
          className="px-5 py-2.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {t("common.new_claim.buttons.back")}
        </button>

        {currentStep === "review" ? (
          <button
            type="button"
            onClick={handleSubmit}
            disabled={loading}
            className="px-6 py-2.5 bg-gradient-to-r from-indigo-600 to-indigo-700 text-white font-medium rounded-lg hover:from-indigo-700 hover:to-indigo-800 transition-all shadow-lg shadow-indigo-900/10 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <span className="inline-flex items-center gap-2">
                <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                {t("common.new_claim.buttons.submitting")}
              </span>
            ) : (
              t("common.new_claim.buttons.submit")
            )}
          </button>
        ) : (
          <button
            type="button"
            onClick={handleNext}
            disabled={!isStepValid()}
            className="px-6 py-2.5 bg-gradient-to-r from-indigo-600 to-indigo-700 text-white font-medium rounded-lg hover:from-indigo-700 hover:to-indigo-800 transition-all shadow-lg shadow-indigo-900/10 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {t("common.new_claim.buttons.continue")}
          </button>
        )}
      </div>
    </div>
  );
};

// Review Row Component
const ReviewRow: React.FC<{ label: string; value: string; capitalize?: boolean }> = ({
  label,
  value,
  capitalize,
}) => (
  <div className="flex items-center justify-between py-2">
    <span className="text-sm text-gray-500">{label}</span>
    <span className={`text-sm font-medium text-gray-900 ${capitalize ? "capitalize" : ""}`}>
      {value}
    </span>
  </div>
);

export default NewClaimPage;
