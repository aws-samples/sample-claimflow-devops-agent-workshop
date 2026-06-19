import React, { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  getClaim,
  submitClaim,
  approveClaim,
  rejectClaim,
  settleClaim,
  closeClaim,
  getClaimDocuments,
  Claim,
  Document as ClaimDocument,
} from "../services/claims";
import { useAuth } from "../contexts/AuthContext";
import {
  ArrowLeftIcon,
  DocumentTextIcon,
  CheckCircleIcon,
  XCircleIcon,
  PaperAirplaneIcon,
  BanknotesIcon,
  LockClosedIcon,
} from "@heroicons/react/24/outline";
import api from "../services/api";

// Format amount in Indian numbering system
const formatINR = (amount: number): string => {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
};

// Format date as DD/MM/YYYY
const formatDate = (dateStr: string): string => {
  if (!dateStr) return "--";
  const date = new Date(dateStr);
  const day = String(date.getDate()).padStart(2, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const year = date.getFullYear();
  return `${day}/${month}/${year}`;
};

interface ClaimHistoryEntry {
  claim_id: string;
  timestamp: string;
  previous_status: string;
  new_status: string;
  changed_by: string;
  notes?: string;
}

const statusColors: Record<string, { text: string; bg: string; border: string; dot: string }> = {
  draft: { text: "text-gray-700", bg: "bg-gray-100", border: "border-gray-300", dot: "bg-gray-400" },
  submitted: { text: "text-blue-700", bg: "bg-blue-100", border: "border-blue-300", dot: "bg-blue-500" },
  under_review: { text: "text-amber-700", bg: "bg-amber-100", border: "border-amber-300", dot: "bg-amber-500" },
  approved: { text: "text-green-700", bg: "bg-green-100", border: "border-green-300", dot: "bg-green-500" },
  rejected: { text: "text-red-700", bg: "bg-red-100", border: "border-red-300", dot: "bg-red-500" },
  settlement: { text: "text-purple-700", bg: "bg-purple-100", border: "border-purple-300", dot: "bg-purple-500" },
  closed: { text: "text-indigo-700", bg: "bg-indigo-100", border: "border-indigo-300", dot: "bg-indigo-500" },
};

const ClaimDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const { t } = useTranslation();
  const [claim, setClaim] = useState<Claim | null>(null);
  const [history, setHistory] = useState<ClaimHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState("");
  const [actionError, setActionError] = useState("");

  // Modal states
  const [showApproveModal, setShowApproveModal] = useState(false);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [settlementAmount, setSettlementAmount] = useState("");
  const [approveNotes, setApproveNotes] = useState("");
  const [rejectReason, setRejectReason] = useState("");

  // Status timeline steps (translated)
  const TIMELINE_STEPS = [
    { key: "draft", label: t("common.claim_detail.timeline.draft") },
    { key: "submitted", label: t("common.claim_detail.timeline.submitted") },
    { key: "under_review", label: t("common.claim_detail.timeline.under_review") },
    { key: "approved", label: t("common.claim_detail.timeline.approved") },
    { key: "settlement", label: t("common.claim_detail.timeline.settlement") },
    { key: "closed", label: t("common.claim_detail.timeline.closed") },
  ];

  const TIMELINE_STEPS_REJECTED = [
    { key: "draft", label: t("common.claim_detail.timeline.draft") },
    { key: "submitted", label: t("common.claim_detail.timeline.submitted") },
    { key: "under_review", label: t("common.claim_detail.timeline.under_review") },
    { key: "rejected", label: t("common.claim_detail.timeline.rejected") },
    { key: "closed", label: t("common.claim_detail.timeline.closed") },
  ];

  const fetchClaim = useCallback(async () => {
    if (!id) return;
    try {
      const data = await getClaim(id);
      setClaim(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || t("common.claim_detail.errors.load_failed"));
    } finally {
      setLoading(false);
    }
  }, [id, t]);

  const fetchHistory = useCallback(async () => {
    if (!id) return;
    try {
      const response = await api.get<ClaimHistoryEntry[]>(`/api/claims/${id}/history`);
      setHistory(response.data);
    } catch {
      // History may not be available for all claims
      setHistory([]);
    }
  }, [id]);

  useEffect(() => {
    fetchClaim();
    fetchHistory();
  }, [fetchClaim, fetchHistory]);

  const handleAction = async (action: () => Promise<void>) => {
    setActionLoading(true);
    setActionError("");
    try {
      await action();
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      let message = t("common.claim_detail.errors.action_failed");
      if (Array.isArray(detail)) {
        message = detail.map((e: any) => e.msg || e).join(". ");
      } else if (typeof detail === "string") {
        message = detail;
      } else if (err?.message) {
        message = err.message;
      }
      setActionError(message);
      setActionLoading(false);
      return;
    }
    // Refresh data after successful action
    try {
      await fetchClaim();
      await fetchHistory();
    } catch {
      // Ignore refresh errors
    }
    setActionLoading(false);
  };

  const handleSubmit = () => handleAction(async () => {
    await submitClaim(id!);
  });

  const handleApprove = () => handleAction(async () => {
    const amount = parseFloat(settlementAmount);
    if (isNaN(amount) || amount <= 0) {
      throw new Error(t("common.claim_detail.errors.invalid_settlement"));
    }
    await approveClaim(id!, amount, approveNotes || undefined);
    setShowApproveModal(false);
    setSettlementAmount("");
    setApproveNotes("");
  });

  const handleReject = () => handleAction(async () => {
    if (!rejectReason.trim() || rejectReason.trim().length < 10) {
      throw new Error(t("common.claim_detail.errors.rejection_too_short"));
    }
    await rejectClaim(id!, rejectReason);
    setShowRejectModal(false);
    setRejectReason("");
  });

  const handleSettle = () => handleAction(async () => {
    await settleClaim(id!);
  });

  const handleClose = () => handleAction(async () => {
    await closeClaim(id!);
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full" />
      </div>
    );
  }

  if (error || !claim) {
    return (
      <div className="space-y-4">
        <Link to="/claims" className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700">
          <ArrowLeftIcon className="w-4 h-4" />
          {t("common.claim_detail.navigation.back_to_claims")}
        </Link>
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <p className="text-red-700">{error || t("common.claim_detail.errors.not_found")}</p>
        </div>
      </div>
    );
  }

  const statusStyle = statusColors[claim.status] || statusColors.draft;
  const isAdjudicatorOrAdmin = user?.role === "adjudicator" || user?.role === "admin";
  const isPolicyholder = user?.role === "policyholder";

  // Determine which timeline to show
  const timelineSteps = claim.status === "rejected" ? TIMELINE_STEPS_REJECTED : TIMELINE_STEPS;
  const currentStepIndex = timelineSteps.findIndex((s) => s.key === claim.status);

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Back link */}
      <Link
        to="/claims"
        className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-indigo-600 transition-colors"
      >
        <ArrowLeftIcon className="w-4 h-4" />
        {t("common.claim_detail.navigation.back_to_claims")}
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 capitalize">
            {claim.claim_type} {t("common.claim_detail.header.claim_suffix")}
          </h1>
          <p className="text-sm text-gray-500 mt-1">{t("common.claim_detail.header.id_label")} {claim.claim_id}</p>
        </div>
        <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full border ${statusStyle.bg} ${statusStyle.border}`}>
          <span className={`w-2 h-2 rounded-full ${statusStyle.dot}`} />
          <span className={`text-sm font-medium capitalize ${statusStyle.text}`}>
            {claim.status.replace(/_/g, " ")}
          </span>
        </div>
      </div>

      {/* Action Error */}
      {actionError && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <p className="text-sm text-red-700">{actionError}</p>
        </div>
      )}

      {/* Status Timeline */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 bg-gray-50">
          <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wider">
            {t("common.claim_detail.timeline.title")}
          </h2>
        </div>
        <div className="p-6">
          <div className="flex items-center justify-between">
            {timelineSteps.map((step, index) => {
              const isCompleted = index <= currentStepIndex;
              const isCurrent = index === currentStepIndex;
              const stepColor = isCompleted
                ? statusColors[step.key] || statusColors.draft
                : { text: "text-gray-400", bg: "bg-gray-50", border: "border-gray-200", dot: "bg-gray-300" };

              return (
                <React.Fragment key={step.key}>
                  <div className="flex flex-col items-center gap-2">
                    <div
                      className={`w-8 h-8 rounded-full flex items-center justify-center border-2 transition-all ${
                        isCurrent
                          ? `${stepColor.dot} border-transparent ring-4 ring-opacity-20 ${step.key === "rejected" ? "ring-red-300" : "ring-indigo-300"}`
                          : isCompleted
                          ? `${stepColor.dot} border-transparent`
                          : "bg-white border-gray-300"
                      }`}
                    >
                      {isCompleted && (
                        <CheckCircleIcon className="w-4 h-4 text-white" />
                      )}
                    </div>
                    <span
                      className={`text-xs font-medium ${
                        isCurrent ? stepColor.text : isCompleted ? "text-gray-700" : "text-gray-400"
                      }`}
                    >
                      {step.label}
                    </span>
                  </div>
                  {index < timelineSteps.length - 1 && (
                    <div
                      className={`flex-1 h-0.5 mx-2 ${
                        index < currentStepIndex ? "bg-indigo-400" : "bg-gray-200"
                      }`}
                    />
                  )}
                </React.Fragment>
              );
            })}
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      {renderActionButtons()}

      {/* Main Details Card */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 bg-gray-50">
          <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wider">
            {t("common.claim_detail.details.title")}
          </h2>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <DetailItem label={t("common.claim_detail.details.claim_type")} value={claim.claim_type} capitalize />
            <DetailItem label={t("common.claim_detail.details.amount")} value={formatINR(claim.amount)} highlight />
            <DetailItem label={t("common.claim_detail.details.policy_number")} value={claim.policy_number || t("common.claim_detail.details.not_provided")} />
            <DetailItem label={t("common.claim_detail.details.status")} value={claim.status.replace(/_/g, " ")} capitalize />
            <DetailItem
              label={t("common.claim_detail.details.incident_date")}
              value={claim.incident_date ? formatDate(claim.incident_date) : t("common.claim_detail.details.not_provided")}
            />
            <DetailItem
              label={t("common.claim_detail.details.created_on")}
              value={formatDate(claim.created_at || "")}
            />
            <DetailItem
              label={t("common.claim_detail.details.submitted_on")}
              value={claim.submitted_at ? formatDate(claim.submitted_at) : t("common.claim_detail.details.not_submitted")}
            />
            {claim.resolved_at && (
              <DetailItem label={t("common.claim_detail.details.resolved_on")} value={formatDate(claim.resolved_at)} />
            )}
            {claim.user_id && !isPolicyholder && (
              <DetailItem label={t("common.claim_detail.details.claimant")} value={claim.user_id} />
            )}
            {claim.fraud_score !== undefined && claim.fraud_score !== null && !isPolicyholder && (
              <DetailItem
                label={t("common.claim_detail.details.fraud_score")}
                value={`${(claim.fraud_score * 100).toFixed(1)}%`}
                highlight={claim.fraud_score > 0.7}
              />
            )}
          </div>
        </div>
      </div>

      {/* Description Card */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 bg-gray-50">
          <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wider">
            {t("common.claim_detail.description.title")}
          </h2>
        </div>
        <div className="p-6">
          <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
            {claim.description || t("common.claim_detail.description.empty")}
          </p>
        </div>
      </div>

      {/* Documents Card */}
      <DocumentsSection claimId={claim.claim_id} />

      {/* Claim History Timeline */}
      {history.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100 bg-gray-50">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wider">
              {t("common.claim_detail.history.title")}
            </h2>
          </div>
          <div className="p-6">
            <div className="space-y-4">
              {history.map((entry, index) => (
                <div key={index} className="flex gap-4">
                  <div className="flex flex-col items-center">
                    <div className="w-3 h-3 rounded-full bg-indigo-400 mt-1" />
                    {index < history.length - 1 && (
                      <div className="w-0.5 flex-1 bg-gray-200 mt-1" />
                    )}
                  </div>
                  <div className="pb-4">
                    <p className="text-sm font-medium text-gray-900 capitalize">
                      {entry.new_status.replace(/_/g, " ")}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {formatDate(entry.timestamp)}
                      {entry.changed_by && t("common.claim_detail.history.by_user", { user: entry.changed_by })}
                    </p>
                    {entry.notes && (
                      <p className="text-xs text-gray-600 mt-1 italic">
                        {entry.notes}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Approve Modal */}
      {showApproveModal && (
        <Modal onClose={() => setShowApproveModal(false)} title={t("common.claim_detail.approve_modal.title")}>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("common.claim_detail.approve_modal.settlement_amount")} <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                value={settlementAmount}
                onChange={(e) => setSettlementAmount(e.target.value)}
                placeholder={t("common.claim_detail.approve_modal.settlement_placeholder")}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("common.claim_detail.approve_modal.notes")}
              </label>
              <textarea
                value={approveNotes}
                onChange={(e) => setApproveNotes(e.target.value)}
                placeholder={t("common.claim_detail.approve_modal.notes_placeholder")}
                rows={3}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none resize-none"
              />
            </div>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowApproveModal(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
              >
                {t("common.claim_detail.approve_modal.cancel")}
              </button>
              <button
                onClick={handleApprove}
                disabled={actionLoading || !settlementAmount}
                className="px-4 py-2 text-sm font-medium text-white bg-gradient-to-r from-green-500 to-green-600 rounded-lg hover:from-green-600 hover:to-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                {actionLoading ? t("common.claim_detail.actions.approving") : t("common.claim_detail.actions.confirm_approve")}
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Reject Modal */}
      {showRejectModal && (
        <Modal onClose={() => setShowRejectModal(false)} title={t("common.claim_detail.reject_modal.title")}>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("common.claim_detail.reject_modal.reason")} <span className="text-red-500">*</span>
              </label>
              <textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder={t("common.claim_detail.reject_modal.reason_placeholder")}
                rows={4}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none resize-none"
              />
            </div>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowRejectModal(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
              >
                {t("common.claim_detail.reject_modal.cancel")}
              </button>
              <button
                onClick={handleReject}
                disabled={actionLoading || !rejectReason.trim()}
                className="px-4 py-2 text-sm font-medium text-white bg-gradient-to-r from-red-500 to-red-600 rounded-lg hover:from-red-600 hover:to-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                {actionLoading ? t("common.claim_detail.actions.rejecting") : t("common.claim_detail.actions.confirm_reject")}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );

  function renderActionButtons() {
    const buttons: React.ReactNode[] = [];

    // Policyholder + draft: Submit
    if (isPolicyholder && claim!.status === "draft") {
      buttons.push(
        <button
          key="submit"
          onClick={handleSubmit}
          disabled={actionLoading}
          className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-indigo-500 to-indigo-600 rounded-lg hover:from-indigo-600 hover:to-indigo-700 shadow-sm disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          <PaperAirplaneIcon className="w-4 h-4" />
          {actionLoading ? t("common.claim_detail.actions.submitting") : t("common.claim_detail.actions.submit")}
        </button>
      );
    }

    // Adjudicator/Admin + under_review: Approve & Reject
    if (isAdjudicatorOrAdmin && claim!.status === "under_review") {
      buttons.push(
        <button
          key="approve"
          onClick={() => setShowApproveModal(true)}
          disabled={actionLoading}
          className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-green-500 to-green-600 rounded-lg hover:from-green-600 hover:to-green-700 shadow-sm disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          <CheckCircleIcon className="w-4 h-4" />
          {t("common.claim_detail.actions.approve")}
        </button>
      );
      buttons.push(
        <button
          key="reject"
          onClick={() => setShowRejectModal(true)}
          disabled={actionLoading}
          className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-red-500 to-red-600 rounded-lg hover:from-red-600 hover:to-red-700 shadow-sm disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          <XCircleIcon className="w-4 h-4" />
          {t("common.claim_detail.actions.reject")}
        </button>
      );
    }

    // Adjudicator/Admin + approved: Initiate Settlement
    if (isAdjudicatorOrAdmin && claim!.status === "approved") {
      buttons.push(
        <button
          key="settle"
          onClick={handleSettle}
          disabled={actionLoading}
          className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-purple-500 to-purple-600 rounded-lg hover:from-purple-600 hover:to-purple-700 shadow-sm disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          <BanknotesIcon className="w-4 h-4" />
          {actionLoading ? t("common.claim_detail.actions.processing") : t("common.claim_detail.actions.settle")}
        </button>
      );
    }

    // Adjudicator/Admin + settlement or rejected: Close Claim
    if (isAdjudicatorOrAdmin && (claim!.status === "settlement" || claim!.status === "rejected")) {
      buttons.push(
        <button
          key="close"
          onClick={handleClose}
          disabled={actionLoading}
          className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-indigo-500 to-indigo-600 rounded-lg hover:from-indigo-600 hover:to-indigo-700 shadow-sm disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          <LockClosedIcon className="w-4 h-4" />
          {actionLoading ? t("common.claim_detail.actions.closing") : t("common.claim_detail.actions.close")}
        </button>
      );
    }

    if (buttons.length === 0) return null;

    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-4">
        <div className="flex items-center gap-3 flex-wrap">{buttons}</div>
      </div>
    );
  }
};

// Documents Section Component
const DocumentsSection: React.FC<{ claimId: string }> = ({ claimId }) => {
  const { t } = useTranslation();
  const [documents, setDocuments] = React.useState<ClaimDocument[]>([]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    const fetchDocs = async () => {
      try {
        const docs = await getClaimDocuments(claimId);
        setDocuments(Array.isArray(docs) ? docs : []);
      } catch {
        setDocuments([]);
      } finally {
        setLoading(false);
      }
    };
    fetchDocs();
  }, [claimId]);

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-6">
        <p className="text-sm text-gray-500">{t("common.claim_detail.documents.loading")}</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-100 bg-gray-50">
        <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wider">
          {t("common.claim_detail.documents.title", { count: documents.length })}
        </h2>
      </div>
      <div className="p-6">
        {documents.length === 0 ? (
          <p className="text-sm text-gray-500">{t("common.claim_detail.documents.empty")}</p>
        ) : (
          <div className="space-y-3">
            {documents.map((doc) => (
              <div key={doc.document_id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-3">
                  <DocumentTextIcon className="w-5 h-5 text-indigo-500" />
                  <div>
                    <p className="text-sm font-medium text-gray-900">{doc.file_name}</p>
                    <p className="text-xs text-gray-500">
                      {doc.document_type.replace(/_/g, " ")} • {(doc.file_size / 1024).toFixed(1)} KB • {formatDate(doc.created_at)}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// Detail Item Component
const DetailItem: React.FC<{
  label: string;
  value: string;
  capitalize?: boolean;
  highlight?: boolean;
}> = ({ label, value, capitalize, highlight }) => (
  <div>
    <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
      {label}
    </p>
    <p
      className={`text-sm font-medium ${
        highlight ? "text-indigo-700" : "text-gray-900"
      } ${capitalize ? "capitalize" : ""}`}
    >
      {value}
    </p>
  </div>
);

// Modal Component
const Modal: React.FC<{
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}> = ({ onClose, title, children }) => (
  <div className="fixed inset-0 z-50 flex items-center justify-center">
    <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
    <div className="relative bg-white rounded-xl shadow-xl border border-gray-200 w-full max-w-md mx-4 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
      {children}
    </div>
  </div>
);

export default ClaimDetailPage;
