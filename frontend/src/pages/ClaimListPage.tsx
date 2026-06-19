import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { listClaims, Claim } from "../services/claims";
import { useAuth } from "../contexts/AuthContext";
import {
  DocumentTextIcon,
  FunnelIcon,
  PlusCircleIcon,
} from "@heroicons/react/24/outline";

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
  return date.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
};

const statusColors: Record<string, string> = {
  draft: "bg-gray-100 text-gray-700",
  submitted: "bg-blue-100 text-blue-700",
  under_review: "bg-yellow-100 text-yellow-700",
  approved: "bg-green-100 text-green-700",
  rejected: "bg-red-100 text-red-700",
  pending: "bg-orange-100 text-orange-700",
};

const claimTypeColors: Record<string, string> = {
  health: "bg-pink-50 text-pink-700",
  motor: "bg-blue-50 text-blue-700",
  property: "bg-amber-50 text-amber-700",
  travel: "bg-teal-50 text-teal-700",
};

const ClaimListPage: React.FC = () => {
  const { user } = useAuth();
  const { t } = useTranslation();
  const [claims, setClaims] = useState<Claim[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [filterType, setFilterType] = useState("");

  useEffect(() => {
    const fetchClaims = async () => {
      setLoading(true);
      try {
        const params: any = { page: 1, page_size: 50 };
        if (filterStatus) params.status = filterStatus;
        if (filterType) params.claim_type = filterType;
        const response = await listClaims(params);
        setClaims(response.items || []);
      } catch (err) {
        setError(t("common.claim_list.errors.load_failed"));
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchClaims();
  }, [filterStatus, filterType, t]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t("common.claim_list.header.title")}</h1>
          <p className="text-gray-500 mt-1">
            {user?.role === "policyholder"
              ? t("common.claim_list.header.subtitle_policyholder")
              : t("common.claim_list.header.subtitle_other")}
          </p>
        </div>
        {user?.role === "policyholder" && (
          <Link
            to="/claims/new"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-indigo-600 to-indigo-700 text-white font-medium rounded-lg hover:from-indigo-700 hover:to-indigo-800 transition-all shadow-lg shadow-indigo-900/10"
          >
            <PlusCircleIcon className="w-5 h-5" />
            {t("common.claim_list.header.new_claim")}
          </Link>
        )}
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-4">
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <FunnelIcon className="w-4 h-4" />
            <span>{t("common.claim_list.filters.label")}</span>
          </div>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-indigo-500 focus:border-indigo-500 outline-none"
            aria-label={t("common.claim_list.filters.by_status_aria")}
          >
            <option value="">{t("common.claim_list.filters.all_statuses")}</option>
            <option value="draft">{t("common.claim_list.filters.draft")}</option>
            <option value="submitted">{t("common.claim_list.filters.submitted")}</option>
            <option value="under_review">{t("common.claim_list.filters.under_review")}</option>
            <option value="approved">{t("common.claim_list.filters.approved")}</option>
            <option value="rejected">{t("common.claim_list.filters.rejected")}</option>
          </select>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-indigo-500 focus:border-indigo-500 outline-none"
            aria-label={t("common.claim_list.filters.by_type_aria")}
          >
            <option value="">{t("common.claim_list.filters.all_types")}</option>
            <option value="health">{t("common.claim_list.filters.health")}</option>
            <option value="motor">{t("common.claim_list.filters.motor")}</option>
            <option value="property">{t("common.claim_list.filters.property")}</option>
            <option value="travel">{t("common.claim_list.filters.travel")}</option>
          </select>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Loading */}
      {loading ? (
        <div className="flex items-center justify-center h-48">
          <div className="animate-spin w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full" />
        </div>
      ) : claims.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-12 text-center">
          <DocumentTextIcon className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">{t("common.claim_list.empty.no_claims")}</p>
        </div>
      ) : (
        /* Claims Table */
        <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100">
                  <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    {t("common.claim_list.table.claim_id")}
                  </th>
                  <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    {t("common.claim_list.table.type")}
                  </th>
                  <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    {t("common.claim_list.table.amount")}
                  </th>
                  <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    {t("common.claim_list.table.status")}
                  </th>
                  <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    {t("common.claim_list.table.date")}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {claims.map((claim) => (
                  <tr key={claim.claim_id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4">
                      <Link
                        to={`/claims/${claim.claim_id}`}
                        className="text-sm font-medium text-indigo-600 hover:text-indigo-700 hover:underline"
                      >
                        {claim.claim_id.slice(0, 8)}...
                      </Link>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex px-2.5 py-1 rounded-full text-xs font-medium capitalize ${claimTypeColors[claim.claim_type] || "bg-gray-50 text-gray-700"}`}>
                        {claim.claim_type}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm font-semibold text-gray-900">
                      {formatINR(claim.amount)}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex px-2.5 py-1 rounded-full text-xs font-medium capitalize ${statusColors[claim.status] || "bg-gray-100 text-gray-700"}`}>
                        {claim.status.replace("_", " ")}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {formatDate(claim.submitted_at || claim.created_at || "")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default ClaimListPage;
