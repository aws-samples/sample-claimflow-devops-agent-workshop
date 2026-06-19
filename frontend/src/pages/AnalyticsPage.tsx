import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  ChartBarIcon,
  ArrowTrendingUpIcon,
  ClockIcon,
  ShieldCheckIcon,
} from "@heroicons/react/24/outline";

// Simple bar chart component (no external library needed)
const BarChart: React.FC<{ data: { label: string; value: number; color: string }[] }> = ({ data }) => {
  const max = Math.max(...data.map((d) => d.value), 1);
  return (
    <div className="space-y-3">
      {data.map((item) => (
        <div key={item.label} className="flex items-center gap-3">
          <span className="text-xs text-gray-500 w-20 text-right">{item.label}</span>
          <div className="flex-1 bg-gray-100 rounded-full h-6 overflow-hidden">
            <div
              className={`h-full rounded-full ${item.color} transition-all duration-700 flex items-center justify-end pr-2`}
              style={{ width: `${(item.value / max) * 100}%` }}
            >
              <span className="text-xs font-medium text-white">{item.value}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

// Donut chart component
const DonutChart: React.FC<{
  segments: { label: string; value: number; color: string }[];
  totalLabel: string;
}> = ({ segments, totalLabel }) => {
  const total = segments.reduce((sum, s) => sum + s.value, 0) || 1;
  let cumulativePercent = 0;

  const getCoordinatesForPercent = (percent: number) => {
    const x = Math.cos(2 * Math.PI * percent);
    const y = Math.sin(2 * Math.PI * percent);
    return [x, y];
  };

  return (
    <div className="flex items-center gap-6">
      <svg viewBox="-1.2 -1.2 2.4 2.4" className="w-32 h-32 -rotate-90">
        {segments.map((segment) => {
          const percent = segment.value / total;
          const [startX, startY] = getCoordinatesForPercent(cumulativePercent);
          cumulativePercent += percent;
          const [endX, endY] = getCoordinatesForPercent(cumulativePercent);
          const largeArcFlag = percent > 0.5 ? 1 : 0;

          return (
            <path
              key={segment.label}
              d={`M ${startX} ${startY} A 1 1 0 ${largeArcFlag} 1 ${endX} ${endY} L 0 0`}
              fill={segment.color}
              stroke="white"
              strokeWidth="0.04"
            />
          );
        })}
        <circle cx="0" cy="0" r="0.6" fill="white" />
        <text x="0" y="0.05" textAnchor="middle" className="text-[0.25px] font-bold fill-gray-900 rotate-90" style={{ fontSize: '0.25px' }}>
          {total}
        </text>
        <text x="0" y="0.2" textAnchor="middle" className="text-[0.12px] fill-gray-500 rotate-90" style={{ fontSize: '0.12px' }}>
          {totalLabel}
        </text>
      </svg>
      <div className="space-y-2">
        {segments.map((s) => (
          <div key={s.label} className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: s.color }} />
            <span className="text-sm text-gray-600">{s.label}: {s.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

const AnalyticsPage: React.FC = () => {
  const { t } = useTranslation();
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
  const [realData, setRealData] = useState<{
    total: number;
    byType: { label: string; value: number; color: string }[];
    byStatus: { label: string; value: number; color: string }[];
    totalAmount: number;
  }>({ total: 0, byType: [], byStatus: [], totalAmount: 0 });

  React.useEffect(() => {
    const fetchRealData = async () => {
      try {
        const { listClaims } = await import("../services/claims");
        const response = await listClaims({ page: 1, page_size: 100 });
        const claims = response.items || [];

        // Filter by date if filters are set
        let filtered = claims;
        if (startDate) {
          filtered = filtered.filter((c) => (c.created_at || "") >= startDate);
        }
        if (endDate) {
          filtered = filtered.filter((c) => (c.created_at || "") <= endDate + "T23:59:59");
        }

        // Compute by type
        const typeCount: Record<string, number> = {};
        const statusCount: Record<string, number> = {};
        let totalAmount = 0;

        filtered.forEach((c) => {
          typeCount[c.claim_type] = (typeCount[c.claim_type] || 0) + 1;
          statusCount[c.status] = (statusCount[c.status] || 0) + 1;
          totalAmount += c.amount || 0;
        });

        const typeColors: Record<string, string> = {
          health: "bg-blue-500", motor: "bg-emerald-500", property: "bg-amber-500", travel: "bg-purple-500"
        };
        const statusColorMap: Record<string, string> = {
          draft: "#6b7280", submitted: "#3b82f6", under_review: "#f59e0b", approved: "#10b981", rejected: "#ef4444"
        };

        setRealData({
          total: filtered.length,
          byType: Object.entries(typeCount).map(([k, v]) => ({ label: k, value: v, color: typeColors[k] || "bg-gray-500" })),
          byStatus: Object.entries(statusCount).map(([k, v]) => ({ label: k.replace("_", " "), value: v, color: statusColorMap[k] || "#6b7280" })),
          totalAmount,
        });
      } catch (err) {
        console.error("Failed to fetch analytics data:", err);
      }
    };
    fetchRealData();
  }, [startDate, endDate]);

  // Mock analytics data (industry benchmarks)
  const claimsByType = realData.byType.length > 0 ? realData.byType : [
    { label: t("common.analytics.claim_types.health"), value: 45, color: "bg-blue-500" },
    { label: t("common.analytics.claim_types.motor"), value: 32, color: "bg-emerald-500" },
    { label: t("common.analytics.claim_types.property"), value: 18, color: "bg-amber-500" },
    { label: t("common.analytics.claim_types.travel"), value: 12, color: "bg-purple-500" },
  ];

  const claimsByMonth = [
    { label: t("common.analytics.months.jan"), value: 12 },
    { label: t("common.analytics.months.feb"), value: 19 },
    { label: t("common.analytics.months.mar"), value: 15 },
    { label: t("common.analytics.months.apr"), value: 22 },
    { label: t("common.analytics.months.may"), value: realData.total || 28 },
  ];

  const statusDistribution = realData.byStatus.length > 0 ? realData.byStatus : [
    { label: t("common.analytics.donut.approved"), value: 52, color: "#10b981" },
    { label: t("common.analytics.donut.pending"), value: 23, color: "#f59e0b" },
    { label: t("common.analytics.donut.rejected"), value: 12, color: "#ef4444" },
    { label: t("common.analytics.donut.draft"), value: 20, color: "#6b7280" },
  ];

  const metrics = [
    { label: t("common.analytics.metrics.avg_processing_time"), value: t("common.analytics.metrics.avg_processing_value"), icon: ClockIcon, change: "-12%", positive: true },
    { label: t("common.analytics.metrics.fraud_detection"), value: t("common.analytics.metrics.fraud_detection_value"), icon: ShieldCheckIcon, change: "+2.3%", positive: true },
    { label: t("common.analytics.metrics.auto_approval"), value: t("common.analytics.metrics.auto_approval_value"), icon: ArrowTrendingUpIcon, change: "+5%", positive: true },
    { label: t("common.analytics.metrics.total_claims"), value: String(realData.total || 107), icon: ChartBarIcon, change: "+18%", positive: true },
  ];

  const maxMonthValue = Math.max(...claimsByMonth.map((m) => m.value), 1);

  const rangeLabel = startDate && endDate
    ? t("common.analytics.filters.range_from_to", { start: startDate, end: endDate })
    : startDate
    ? t("common.analytics.filters.range_from", { start: startDate })
    : endDate
    ? t("common.analytics.filters.range_until", { end: endDate })
    : t("common.analytics.filters.range_all");

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{t("common.analytics.header.title")}</h1>
        <p className="text-gray-500 mt-1">{t("common.analytics.header.subtitle")}</p>
      </div>

      {/* Date Filters */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-4">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <label htmlFor="start-date" className="text-sm font-medium text-gray-700">{t("common.analytics.filters.start_date")}</label>
            <input
              id="start-date"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-indigo-500 focus:border-indigo-500 outline-none"
            />
          </div>
          <div className="flex items-center gap-2">
            <label htmlFor="end-date" className="text-sm font-medium text-gray-700">{t("common.analytics.filters.end_date")}</label>
            <input
              id="end-date"
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-indigo-500 focus:border-indigo-500 outline-none"
            />
          </div>
          {(startDate || endDate) && (
            <button
              onClick={() => { setStartDate(""); setEndDate(""); }}
              className="text-xs text-indigo-600 hover:text-indigo-700 font-medium"
            >
              {t("common.analytics.filters.clear")}
            </button>
          )}
          <span className="text-xs text-gray-500 bg-gray-100 px-3 py-1.5 rounded-full">
            {rangeLabel}
          </span>
        </div>
      </div>

      {/* Real Data Summary */}
      {realData.total > 0 && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4">
          <p className="text-sm text-indigo-700">
            <strong>{t("common.analytics.live_data.label")}</strong>{" "}
            {t("common.analytics.live_data.showing")} <strong>{realData.total}</strong> {t("common.analytics.live_data.claims")}
            {realData.totalAmount > 0 && (
              <>
                {" "}
                {t("common.analytics.live_data.with_total")}{" "}
                <strong>{`\u20b9${new Intl.NumberFormat("en-IN").format(realData.totalAmount)}`}</strong>
              </>
            )}
            {(startDate || endDate) ? ` ${t("common.analytics.live_data.filtered_suffix")}` : ""}
          </p>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {metrics.map((metric) => (
          <div key={metric.label} className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-5">
            <div className="flex items-center justify-between mb-3">
              <metric.icon className="w-5 h-5 text-indigo-500" />
              <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${metric.positive ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                {metric.change}
              </span>
            </div>
            <p className="text-2xl font-bold text-gray-900">{metric.value}</p>
            <p className="text-xs text-gray-500 mt-1">{metric.label}</p>
          </div>
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Claims by Type */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-6">{t("common.analytics.charts.by_type")}</h3>
          <BarChart data={claimsByType} />
        </div>

        {/* Status Distribution */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-6">{t("common.analytics.charts.status_distribution")}</h3>
          <DonutChart segments={statusDistribution} totalLabel={t("common.analytics.charts.total_label")} />
        </div>
      </div>

      {/* Monthly Trend - Vertical Bar Chart */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-6">{t("common.analytics.charts.monthly_trend")}</h3>
        <div className="flex items-end gap-4" style={{ height: "200px" }}>
          {claimsByMonth.map((month) => {
            const heightPercent = (month.value / maxMonthValue) * 100;
            return (
              <div key={month.label} className="flex-1 flex flex-col items-center h-full">
                {/* Value label */}
                <span className="text-xs font-medium text-gray-700 mb-1">{month.value}</span>
                {/* Bar container - grows from bottom */}
                <div className="flex-1 w-full flex items-end">
                  <div
                    className="w-full rounded-t-lg bg-gradient-to-t from-indigo-600 to-indigo-400 transition-all duration-700"
                    style={{ height: `${heightPercent}%` }}
                  />
                </div>
                {/* Month label */}
                <span className="text-xs text-gray-500 mt-2">{month.label}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Performance Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100">
          <h3 className="text-lg font-semibold text-gray-900">{t("common.analytics.table.title")}</h3>
        </div>
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t("common.analytics.table.type")}</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t("common.analytics.table.total")}</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t("common.analytics.table.avg_amount")}</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t("common.analytics.table.approval_rate")}</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t("common.analytics.table.avg_time")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            <tr><td className="px-6 py-4 text-sm">{`\ud83c\udfe5 ${t("common.analytics.claim_types.health")}`}</td><td className="px-6 py-4 text-sm font-medium">45</td><td className="px-6 py-4 text-sm">₹1,25,000</td><td className="px-6 py-4 text-sm text-green-600 font-medium">78%</td><td className="px-6 py-4 text-sm">3.2 hrs</td></tr>
            <tr><td className="px-6 py-4 text-sm">{`\ud83d\ude97 ${t("common.analytics.claim_types.motor")}`}</td><td className="px-6 py-4 text-sm font-medium">32</td><td className="px-6 py-4 text-sm">₹85,000</td><td className="px-6 py-4 text-sm text-green-600 font-medium">72%</td><td className="px-6 py-4 text-sm">5.1 hrs</td></tr>
            <tr><td className="px-6 py-4 text-sm">{`\ud83c\udfe0 ${t("common.analytics.claim_types.property")}`}</td><td className="px-6 py-4 text-sm font-medium">18</td><td className="px-6 py-4 text-sm">₹3,50,000</td><td className="px-6 py-4 text-sm text-yellow-600 font-medium">61%</td><td className="px-6 py-4 text-sm">8.4 hrs</td></tr>
            <tr><td className="px-6 py-4 text-sm">{`\u2708\ufe0f ${t("common.analytics.claim_types.travel")}`}</td><td className="px-6 py-4 text-sm font-medium">12</td><td className="px-6 py-4 text-sm">₹45,000</td><td className="px-6 py-4 text-sm text-green-600 font-medium">85%</td><td className="px-6 py-4 text-sm">2.1 hrs</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default AnalyticsPage;
