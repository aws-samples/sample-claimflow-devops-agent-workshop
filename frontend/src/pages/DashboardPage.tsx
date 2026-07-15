import React, { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../contexts/AuthContext";
import api from "../services/api";
import { listClaims, Claim } from "../services/claims";
import {
  DocumentTextIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  PlusCircleIcon,
  ServerStackIcon,
  SignalIcon,
  UsersIcon,
  BanknotesIcon,
  LockClosedIcon,
  ArrowPathIcon,
} from "@heroicons/react/24/outline";

// Format amount in Indian numbering system
const formatINR = (amount: number): string => {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
};

// Health-check threshold: any healthy response above this many ms shows the
// service-health tile as amber "Slow". Set high enough to tolerate legitimate
// cold-start latency on ECS Fargate tasks (API Gateway -> VPC Link -> NLB ->
// container startup can genuinely take 3-5s on first hit after idle) while
// still catching real degradation.
const SLOW_RESPONSE_MS = 3000;

// Server-authoritative per-status counts. Runs one lightweight query per
// non-terminal status bucket to read `total` from the paginated response.
// Cheaper than a full listClaims scan and always reflects the current DB
// truth regardless of pagination.
async function fetchStatsFromServer(): Promise<{
  total: number;
  pending: number;
  approved: number;
  rejected: number;
  settled: number;
  closed: number;
}> {
  // Frontend sends `page_size`, backend expects `size` — we intentionally send
  // both so we work whether the deployed backend has been updated to accept
  // page_size or still uses the original `size`.
  const totalOnly = { page: 1, size: 1, page_size: 1 } as const;
  const [total, drafts, submitted, underReview, pending, approved, rejected, settled, closed] = await Promise.all([
    listClaims({ page: 1, size: 1, page_size: 1 } as any),
    listClaims({ ...totalOnly, status: "draft" } as any),
    listClaims({ ...totalOnly, status: "submitted" } as any),
    listClaims({ ...totalOnly, status: "under_review" } as any),
    listClaims({ ...totalOnly, status: "pending" } as any),
    listClaims({ ...totalOnly, status: "approved" } as any),
    listClaims({ ...totalOnly, status: "rejected" } as any),
    listClaims({ ...totalOnly, status: "settlement" } as any),
    listClaims({ ...totalOnly, status: "closed" } as any),
  ]);
  return {
    total: total.total || 0,
    pending: (drafts.total || 0) + (submitted.total || 0) + (underReview.total || 0) + (pending.total || 0),
    approved: approved.total || 0,
    rejected: rejected.total || 0,
    settled: settled.total || 0,
    closed: closed.total || 0,
  };
}

// Format date as DD/MM/YYYY
const formatDate = (dateStr: string): string => {
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
  settlement: "bg-purple-100 text-purple-700",
  closed: "bg-indigo-100 text-indigo-700",
};

const DashboardPage: React.FC = () => {
  const { user } = useAuth();
  const { t } = useTranslation();
  const [claims, setClaims] = useState<Claim[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ total: 0, pending: 0, approved: 0, rejected: 0, settled: 0, closed: 0 });

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Recent claims list for the activity panel — small page is fine.
        const response = await listClaims({ page: 1, size: 10, page_size: 10 } as any);
        setClaims(response.items || []);

        // Server-authoritative per-status counts (independent of the page
        // slice above). See fetchStatsFromServer for the query shape.
        const s = await fetchStatsFromServer();
        setStats(s);
      } catch (err) {
        console.error("Failed to fetch claims:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full" />
      </div>
    );
  }

  // Policyholder Dashboard
  if (user?.role === "policyholder") {
    return (
      <div className="space-y-8">
        {/* Welcome */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{t("common.dashboard.policyholder.title")}</h1>
            <p className="text-gray-500 mt-1">{t("common.dashboard.policyholder.subtitle")}</p>
          </div>
          <Link
            to="/claims/new"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-indigo-600 to-indigo-700 text-white font-medium rounded-lg hover:from-indigo-700 hover:to-indigo-800 transition-all shadow-lg shadow-indigo-900/10"
          >
            <PlusCircleIcon className="w-5 h-5" />
            {t("common.dashboard.policyholder.file_new_claim")}
          </Link>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4">
          <StatCard icon={DocumentTextIcon} label={t("common.dashboard.stats.total_claims")} value={stats.total} color="indigo" />
          <StatCard icon={ClockIcon} label={t("common.dashboard.stats.pending")} value={stats.pending} color="yellow" />
          <StatCard icon={CheckCircleIcon} label={t("common.dashboard.stats.approved")} value={stats.approved} color="green" />
          <StatCard icon={ExclamationTriangleIcon} label={t("common.dashboard.stats.rejected")} value={stats.rejected} color="red" />
          <StatCard icon={BanknotesIcon} label={t("common.dashboard.stats.settled")} value={stats.settled} color="purple" />
          <StatCard icon={LockClosedIcon} label={t("common.dashboard.stats.closed")} value={stats.closed} color="slate" />
        </div>

        {/* Recent Claims */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100">
            <h2 className="text-lg font-semibold text-gray-900">{t("common.dashboard.recent_claims.title")}</h2>
          </div>
          {claims.length === 0 ? (
            <div className="p-12 text-center">
              <DocumentTextIcon className="w-12 h-12 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500">{t("common.dashboard.recent_claims.empty")}</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {claims.slice(0, 5).map((claim) => (
                <Link
                  key={claim.claim_id}
                  to={`/claims/${claim.claim_id}`}
                  className="flex items-center justify-between px-6 py-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 bg-indigo-50 rounded-lg flex items-center justify-center">
                      <DocumentTextIcon className="w-5 h-5 text-indigo-600" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900 capitalize">
                        {claim.claim_type} {t("common.dashboard.claim.type_suffix")}
                      </p>
                      <p className="text-xs text-gray-500">
                        {formatDate(claim.submitted_at || claim.created_at || "")}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-sm font-semibold text-gray-900">
                      {formatINR(claim.amount)}
                    </span>
                    <span className={`inline-flex px-2.5 py-1 rounded-full text-xs font-medium capitalize ${statusColors[claim.status] || "bg-gray-100 text-gray-700"}`}>
                      {claim.status.replace("_", " ")}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          )}
          {claims.length > 0 && (
            <div className="px-6 py-3 bg-gray-50 border-t border-gray-100">
              <Link to="/claims" className="text-sm font-medium text-indigo-600 hover:text-indigo-700">
                {t("common.dashboard.recent_claims.view_all")}
              </Link>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Adjudicator Dashboard
  if (user?.role === "adjudicator") {
    return (
      <div className="space-y-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t("common.dashboard.adjudicator.title")}</h1>
          <p className="text-gray-500 mt-1">{t("common.dashboard.adjudicator.subtitle")}</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4">
          <StatCard icon={ClockIcon} label={t("common.dashboard.stats.pending")} value={stats.pending} color="yellow" />
          <StatCard icon={DocumentTextIcon} label={t("common.dashboard.stats.total_claims")} value={stats.total} color="indigo" />
          <StatCard icon={CheckCircleIcon} label={t("common.dashboard.stats.approved")} value={stats.approved} color="green" />
          <StatCard icon={ExclamationTriangleIcon} label={t("common.dashboard.stats.rejected")} value={stats.rejected} color="red" />
          <StatCard icon={BanknotesIcon} label={t("common.dashboard.stats.settled")} value={stats.settled} color="purple" />
          <StatCard icon={LockClosedIcon} label={t("common.dashboard.stats.closed")} value={stats.closed} color="slate" />
        </div>

        {/* All Claims */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100">
            <h2 className="text-lg font-semibold text-gray-900">{t("common.dashboard.all_claims.title")}</h2>
          </div>
          {claims.length === 0 ? (
            <div className="p-12 text-center">
              <DocumentTextIcon className="w-12 h-12 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500">{t("common.dashboard.all_claims.empty")}</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {claims.map((claim) => (
                <Link
                  key={claim.claim_id}
                  to={`/claims/${claim.claim_id}`}
                  className="flex items-center justify-between px-6 py-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                      ["submitted", "under_review", "pending"].includes(claim.status)
                        ? "bg-yellow-50"
                        : claim.status === "approved"
                        ? "bg-green-50"
                        : claim.status === "rejected"
                        ? "bg-red-50"
                        : "bg-gray-50"
                    }`}>
                      {["submitted", "under_review", "pending"].includes(claim.status) ? (
                        <ClockIcon className="w-5 h-5 text-yellow-600" />
                      ) : claim.status === "approved" ? (
                        <CheckCircleIcon className="w-5 h-5 text-green-600" />
                      ) : claim.status === "rejected" ? (
                        <ExclamationTriangleIcon className="w-5 h-5 text-red-600" />
                      ) : (
                        <DocumentTextIcon className="w-5 h-5 text-gray-600" />
                      )}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900 capitalize">
                        {claim.claim_type} {t("common.dashboard.claim.type_suffix")}
                      </p>
                      <p className="text-xs text-gray-500">
                        {t("common.dashboard.claim.id_label")} {claim.claim_id.slice(0, 8)}... &middot; {formatDate(claim.submitted_at || claim.created_at || "")}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-sm font-semibold text-gray-900">
                      {formatINR(claim.amount)}
                    </span>
                    <span className={`inline-flex px-2.5 py-1 rounded-full text-xs font-medium capitalize ${statusColors[claim.status] || "bg-gray-100 text-gray-700"}`}>
                      {claim.status.replace("_", " ")}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          )}
          {claims.length > 0 && (
            <div className="px-6 py-3 bg-gray-50 border-t border-gray-100">
              <Link to="/claims" className="text-sm font-medium text-indigo-600 hover:text-indigo-700">
                {t("common.dashboard.recent_claims.view_all")}
              </Link>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Admin Dashboard
  return <AdminDashboard claims={claims} stats={stats} onClaimsUpdate={setClaims} onStatsUpdate={setStats} />;
};

// Service health status types
interface ServiceHealth {
  name: string;
  status: "healthy" | "unhealthy" | "not_connected" | "checking";
  responseTime: number | null;
  lastChecked: Date | null;
  endpoint: string | null;
}

// Admin Dashboard Component
const AdminDashboard: React.FC<{
  claims: Claim[];
  stats: { total: number; pending: number; approved: number; rejected: number; settled: number; closed: number };
  onClaimsUpdate: (claims: Claim[]) => void;
  onStatsUpdate: (stats: { total: number; pending: number; approved: number; rejected: number; settled: number; closed: number }) => void;
}> = ({ claims, stats, onClaimsUpdate, onStatsUpdate }) => {
  const { t } = useTranslation();
  const [services, setServices] = useState<ServiceHealth[]>([
    { name: t("common.dashboard.services.auth"), status: "checking", responseTime: null, lastChecked: null, endpoint: "/api/auth/validate" },
    { name: t("common.dashboard.services.claims"), status: "checking", responseTime: null, lastChecked: null, endpoint: "/api/claims" },
    { name: t("common.dashboard.services.fraud"), status: "checking", responseTime: null, lastChecked: null, endpoint: "/api/fraud/flagged" },
    { name: t("common.dashboard.services.documents"), status: "checking", responseTime: null, lastChecked: null, endpoint: "/api/documents" },
    { name: t("common.dashboard.services.notifications"), status: "checking", responseTime: null, lastChecked: null, endpoint: "/api/notifications/log" },
    { name: t("common.dashboard.services.rules"), status: "checking", responseTime: null, lastChecked: null, endpoint: "/api/rules" },
    { name: t("common.dashboard.services.analytics"), status: "checking", responseTime: null, lastChecked: null, endpoint: "/api/analytics/metrics" },
  ]);
  const [activeUsers, setActiveUsers] = useState<number | null>(null);
  const [lastCheckedTime, setLastCheckedTime] = useState<Date | null>(null);

  const checkHealth = useCallback(async (path: string): Promise<{ status: "healthy" | "unhealthy"; responseTime: number }> => {
    const start = Date.now();
    try {
      // 8-second per-request timeout: if the service does not answer within
      // the SLA window, we mark it unhealthy rather than "very slow" — a
      // CPU-pegged or overloaded backend that never returns is functionally
      // unavailable to a user waiting on their browser.
      await api.get(path, { timeout: 8000 });
      return { status: "healthy", responseTime: Date.now() - start };
    } catch (err: any) {
      const responseTime = Date.now() - start;
      const status = err?.response?.status;
      // If we got an HTTP response with a client-error code (401, 403, 404),
      // the service is up — it just refused this specific request. That's
      // still "healthy" from an infrastructure perspective.
      if (typeof status === "number" && status >= 400 && status < 500) {
        return { status: "healthy", responseTime };
      }
      // Any other outcome (5xx, network error, timeout, no response) means
      // the service is not answering — mark it unhealthy so the dashboard
      // reflects reality when a task has OOMed, the target group has no
      // healthy hosts, or the backend is too slow to respond within the SLA.
      return { status: "unhealthy", responseTime };
    }
  }, []);

  const runHealthChecks = useCallback(async () => {
    const now = new Date();

    // Snapshot the current service list without depending on `services` in the
    // closure (avoids a re-render loop while keeping the dep array honest).
    const currentServices = await new Promise<ServiceHealth[]>((resolve) => {
      setServices((prev) => {
        resolve(prev);
        return prev;
      });
    });

    // Check all services that have endpoints
    const updatedServices = await Promise.all(
      currentServices.map(async (svc) => {
        if (!svc.endpoint) return svc;
        const result = await checkHealth(svc.endpoint);
        return { ...svc, status: result.status, responseTime: result.responseTime, lastChecked: now };
      })
    );

    setServices(updatedServices);
    setLastCheckedTime(now);

    // Fetch active users count
    try {
      const usersResponse = await api.get<Array<unknown>>("/api/auth/users");
      setActiveUsers(Array.isArray(usersResponse.data) ? usersResponse.data.length : 0);
    } catch {
      setActiveUsers(null);
    }
  }, [checkHealth]);

  useEffect(() => {
    runHealthChecks();
    const interval = setInterval(runHealthChecks, 60000);
    return () => clearInterval(interval);
  }, [runHealthChecks]);

  // Calculate average response time from connected services
  const connectedServices = services.filter((s) => s.endpoint !== null);
  const healthyServices = connectedServices.filter((s) => s.status === "healthy");
  const avgResponseTime =
    healthyServices.length > 0
      ? Math.round(healthyServices.reduce((sum, s) => sum + (s.responseTime || 0), 0) / healthyServices.length)
      : null;

  const platformStatus =
    healthyServices.length === connectedServices.length
      ? t("common.dashboard.metrics.operational")
      : healthyServices.length > 0
      ? t("common.dashboard.metrics.degraded")
      : t("common.dashboard.metrics.down");

  const platformStatusColor =
    healthyServices.length === connectedServices.length
      ? "text-green-600"
      : healthyServices.length > 0
      ? "text-yellow-600"
      : "text-red-600";

  const secondsAgo = lastCheckedTime ? Math.round((Date.now() - lastCheckedTime.getTime()) / 1000) : null;

  const [simulating, setSimulating] = React.useState(false);
  const [simResult, setSimResult] = React.useState<string | null>(null);

  const handleSimulate = async () => {
    setSimulating(true);
    setSimResult(null);
    const total = 150;
    let succeeded = 0;
    let failed = 0;
    // Run in parallel batches so the browser does not open 150 sockets at once
    // and so the participant can see progress. Each batch reports its running
    // total via the simResult banner.
    const batchSize = 10;
    try {
      for (let i = 0; i < total; i += batchSize) {
        const batch = Array.from({ length: Math.min(batchSize, total - i) }, () =>
          api.post("/api/claims/simulate/lifecycle")
        );
        const results = await Promise.allSettled(batch);
        for (const r of results) {
          if (r.status === "fulfilled") succeeded += 1;
          else failed += 1;
        }
        setSimResult(
          t("common.dashboard.simulation.progress", {
            done: succeeded + failed,
            total,
            failed,
          })
        );
      }
      setSimResult(
        t("common.dashboard.simulation.success_bulk", {
          count: succeeded,
          total,
          failed,
        })
      );
      // Refresh the visible stats in place — no page reload (that would drop
      // the in-memory JWT and force the participant to sign in again).
      try {
        const response = await listClaims({ page: 1, size: 20, page_size: 20 } as any);
        onClaimsUpdate(response.items || []);
        const s = await fetchStatsFromServer();
        onStatsUpdate(s);
      } catch {
        // Ignore refresh error — the banner shows the run completed.
      }
    } catch (err: any) {
      setSimResult(
        t("common.dashboard.simulation.failed", {
          message: err?.response?.data?.detail || err?.message || t("common.dashboard.simulation.unknown_error"),
        })
      );
    } finally {
      setSimulating(false);
    }
  };

  const lastCheckedLabel = lastCheckedTime
    ? t("common.dashboard.admin.last_checked", {
        time:
          secondsAgo !== null && secondsAgo < 60
            ? t("common.dashboard.admin.seconds_ago", { count: secondsAgo })
            : lastCheckedTime.toLocaleTimeString(),
      })
    : "";

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t("common.dashboard.admin.title")}</h1>
          <p className="text-gray-500 mt-1">{t("common.dashboard.admin.subtitle")}</p>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={handleSimulate}
            disabled={simulating}
            className="px-4 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 text-white text-sm font-medium rounded-lg hover:from-purple-700 hover:to-indigo-700 transition-all shadow-lg shadow-purple-900/10 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {simulating ? t("common.dashboard.admin.simulating") : t("common.dashboard.admin.simulate")}
          </button>
          {lastCheckedTime && (
            <span className="text-xs text-gray-400">
              {lastCheckedLabel}
            </span>
          )}
        </div>
      </div>

      {/* Simulation Result */}
      {simResult && (
        <div className={`p-4 rounded-xl border text-sm font-medium ${simResult.startsWith("\u2705") ? "bg-green-50 border-green-200 text-green-700" : "bg-red-50 border-red-200 text-red-700"}`}>
          {simResult}
        </div>
      )}

      {/* Claims Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4">
        <StatCard icon={DocumentTextIcon} label={t("common.dashboard.stats.total_claims")} value={stats.total} color="indigo" />
        <StatCard icon={ClockIcon} label={t("common.dashboard.stats.pending")} value={stats.pending} color="yellow" />
        <StatCard icon={CheckCircleIcon} label={t("common.dashboard.stats.approved")} value={stats.approved} color="green" />
        <StatCard icon={ExclamationTriangleIcon} label={t("common.dashboard.stats.rejected")} value={stats.rejected} color="red" />
        <StatCard icon={BanknotesIcon} label={t("common.dashboard.stats.settled")} value={stats.settled} color="purple" />
          <StatCard icon={LockClosedIcon} label={t("common.dashboard.stats.closed")} value={stats.closed} color="slate" />
      </div>

      {/* Service Health Checks */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <ServerStackIcon className="w-5 h-5 text-gray-700" />
            <h3 className="text-lg font-semibold text-gray-900">{t("common.dashboard.service_health.title")}</h3>
          </div>
          <button
            onClick={runHealthChecks}
            disabled={services.some((s) => s.status === "checking")}
            title={t("common.dashboard.service_health.refresh")}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-600 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ArrowPathIcon className={`w-4 h-4 ${services.some((s) => s.status === "checking") ? "animate-spin" : ""}`} />
            {t("common.dashboard.service_health.refresh")}
          </button>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {services.map((svc) => (
            <div
              key={svc.name}
              className="border border-gray-100 rounded-lg p-4 flex flex-col gap-2"
            >
              <div className="flex items-center gap-2">
                <span
                  className={`w-2.5 h-2.5 rounded-full ${
                    svc.status === "healthy" && (svc.responseTime === null || svc.responseTime <= SLOW_RESPONSE_MS)
                      ? "bg-green-500"
                      : svc.status === "healthy" && svc.responseTime !== null && svc.responseTime > SLOW_RESPONSE_MS
                      ? "bg-yellow-500"
                      : svc.status === "unhealthy"
                      ? "bg-red-500"
                      : "bg-gray-400"
                  }`}
                />
                <span className="text-sm font-medium text-gray-900">{svc.name}</span>
              </div>
              <div className="text-xs text-gray-500">
                {svc.status === "healthy" && (svc.responseTime === null || svc.responseTime <= SLOW_RESPONSE_MS) && (
                  <span className="text-green-600 font-medium">{t("common.dashboard.service_health.healthy")}</span>
                )}
                {svc.status === "healthy" && svc.responseTime !== null && svc.responseTime > SLOW_RESPONSE_MS && (
                  <span className="text-yellow-600 font-medium">{t("common.dashboard.service_health.slow")}</span>
                )}
                {svc.status === "unhealthy" && (
                  <span className="text-red-600 font-medium">{t("common.dashboard.service_health.unhealthy")}</span>
                )}
                {svc.status === "not_connected" && (
                  <span className="text-gray-400">{t("common.dashboard.service_health.not_connected")}</span>
                )}
                {svc.status === "checking" && (
                  <span className="text-gray-400">{t("common.dashboard.service_health.checking")}</span>
                )}
              </div>
              {svc.responseTime !== null && (
                <div className="text-xs text-gray-500">
                  {t("common.dashboard.service_health.response_prefix")}{" "}
                  <span className="font-medium text-gray-700">
                    {t("common.dashboard.service_health.response_value", { ms: svc.responseTime })}
                  </span>
                </div>
              )}
              {svc.lastChecked && (
                <div className="text-xs text-gray-400">
                  {svc.lastChecked.toLocaleTimeString()}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* System Metrics & API Response Times */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* System Metrics */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-6">
          <div className="flex items-center gap-2 mb-4">
            <SignalIcon className="w-5 h-5 text-gray-700" />
            <h3 className="text-lg font-semibold text-gray-900">{t("common.dashboard.metrics.title")}</h3>
          </div>
          <div className="space-y-4">
            <MetricRow label={t("common.dashboard.metrics.platform_status")} value={platformStatus} valueColor={platformStatusColor} />
            <MetricRow
              label={t("common.dashboard.metrics.api_response_time")}
              value={avgResponseTime !== null ? `${avgResponseTime}ms` : t("common.dashboard.metrics.no_value")}
              valueColor="text-gray-900"
            />
            <MetricRow label={t("common.dashboard.metrics.uptime")} value={t("common.dashboard.metrics.uptime_value")} valueColor="text-gray-900" />
            <MetricRow
              label={t("common.dashboard.metrics.active_users")}
              value={activeUsers !== null ? String(activeUsers) : t("common.dashboard.metrics.no_value")}
              valueColor="text-gray-900"
            />
          </div>
        </div>

        {/* API Response Times Table */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-6">
          <div className="flex items-center gap-2 mb-4">
            <UsersIcon className="w-5 h-5 text-gray-700" />
            <h3 className="text-lg font-semibold text-gray-900">{t("common.dashboard.api_times.title")}</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b border-gray-100">
                  <th className="pb-2 font-medium">{t("common.dashboard.api_times.endpoint")}</th>
                  <th className="pb-2 font-medium">{t("common.dashboard.api_times.method")}</th>
                  <th className="pb-2 font-medium">{t("common.dashboard.api_times.avg_ms")}</th>
                  <th className="pb-2 font-medium">{t("common.dashboard.api_times.status")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {connectedServices.map((svc) => (
                  <tr key={svc.name}>
                    <td className="py-2 text-gray-700">{svc.endpoint}</td>
                    <td className="py-2 text-gray-500">{t("common.dashboard.api_times.method_get")}</td>
                    <td className="py-2 text-gray-700 font-medium">
                      {svc.responseTime !== null ? svc.responseTime : t("common.dashboard.metrics.no_value")}
                    </td>
                    <td className="py-2">
                      <span
                        className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                          svc.status === "healthy"
                            ? "bg-green-100 text-green-700"
                            : svc.status === "unhealthy"
                            ? "bg-red-100 text-red-700"
                            : "bg-gray-100 text-gray-500"
                        }`}
                      >
                        {svc.status === "healthy"
                          ? t("common.dashboard.api_times.status_ok")
                          : svc.status === "unhealthy"
                          ? t("common.dashboard.api_times.status_error")
                          : t("common.dashboard.api_times.status_checking")}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Active Sessions & Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">{t("common.dashboard.sessions.title")}</h3>
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 bg-indigo-50 rounded-xl flex items-center justify-center">
              <UsersIcon className="w-7 h-7 text-indigo-600" />
            </div>
            <div>
              <p className="text-3xl font-bold text-gray-900">
                {activeUsers !== null ? activeUsers : t("common.dashboard.metrics.no_value")}
              </p>
              <p className="text-sm text-gray-500">{t("common.dashboard.sessions.registered_users")}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">{t("common.dashboard.activity.title")}</h3>
          {claims.length === 0 ? (
            <p className="text-gray-500 text-sm">{t("common.dashboard.activity.empty")}</p>
          ) : (
            <div className="space-y-3">
              {claims.slice(0, 5).map((claim) => (
                <div key={claim.claim_id} className="flex items-center justify-between text-sm">
                  <span className="text-gray-600 capitalize">
                    {claim.claim_type} {t("common.dashboard.activity.claim_suffix")}
                  </span>
                  <span
                    className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium capitalize ${
                      statusColors[claim.status] || "bg-gray-100 text-gray-700"
                    }`}
                  >
                    {claim.status.replace("_", " ")}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Stat Card Component
const StatCard: React.FC<{
  icon: React.FC<React.SVGProps<SVGSVGElement>>;
  label: string;
  value: number;
  color: string;
}> = ({ icon: Icon, label, value, color }) => {
  const colorMap: Record<string, { bg: string; icon: string }> = {
    indigo: { bg: "bg-indigo-50", icon: "text-indigo-600" },
    yellow: { bg: "bg-yellow-50", icon: "text-yellow-600" },
    green: { bg: "bg-green-50", icon: "text-green-600" },
    red: { bg: "bg-red-50", icon: "text-red-600" },
    purple: { bg: "bg-purple-50", icon: "text-purple-600" },
    slate: { bg: "bg-slate-100", icon: "text-slate-600" },
  };
  const colors = colorMap[color] || colorMap.indigo;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-5">
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 ${colors.bg} rounded-lg flex items-center justify-center`}>
          <Icon className={`w-5 h-5 ${colors.icon}`} />
        </div>
        <div>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
          <p className="text-xs text-gray-500">{label}</p>
        </div>
      </div>
    </div>
  );
};

// Metric Row Component
const MetricRow: React.FC<{ label: string; value: string; valueColor: string }> = ({
  label,
  value,
  valueColor,
}) => (
  <div className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
    <span className="text-sm text-gray-600">{label}</span>
    <span className={`text-sm font-medium ${valueColor}`}>{value}</span>
  </div>
);

export default DashboardPage;
