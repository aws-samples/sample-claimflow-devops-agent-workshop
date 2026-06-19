import React from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  ShieldCheckIcon,
  ClipboardDocumentCheckIcon,
  CogIcon,
} from "@heroicons/react/24/outline";

const LandingPage: React.FC = () => {
  const { t } = useTranslation();

  const personas = [
    {
      title: t("common.landing.personas.policyholder_title"),
      description: t("common.landing.personas.policyholder_description"),
      icon: ShieldCheckIcon,
      color: "blue",
      link: "/login/policyholder",
      gradient: "from-blue-500 to-blue-600",
      hoverGradient: "from-blue-600 to-blue-700",
      iconBg: "bg-blue-100",
      iconColor: "text-blue-600",
      ring: "ring-blue-200",
    },
    {
      title: t("common.landing.personas.adjudicator_title"),
      description: t("common.landing.personas.adjudicator_description"),
      icon: ClipboardDocumentCheckIcon,
      color: "green",
      link: "/login/adjudicator",
      gradient: "from-emerald-500 to-emerald-600",
      hoverGradient: "from-emerald-600 to-emerald-700",
      iconBg: "bg-emerald-100",
      iconColor: "text-emerald-600",
      ring: "ring-emerald-200",
    },
    {
      title: t("common.landing.personas.admin_title"),
      description: t("common.landing.personas.admin_description"),
      icon: CogIcon,
      color: "purple",
      link: "/login/admin",
      gradient: "from-purple-500 to-purple-600",
      hoverGradient: "from-purple-600 to-purple-700",
      iconBg: "bg-purple-100",
      iconColor: "text-purple-600",
      ring: "ring-purple-200",
    },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-900 via-purple-900 to-indigo-800 relative overflow-hidden">
      {/* Floating decorative circles */}
      <div className="absolute top-20 left-10 w-72 h-72 bg-purple-500/20 rounded-full blur-3xl animate-pulse" />
      <div className="absolute bottom-20 right-10 w-96 h-96 bg-indigo-500/20 rounded-full blur-3xl animate-pulse" />
      <div className="absolute top-1/2 left-1/3 w-64 h-64 bg-blue-500/10 rounded-full blur-3xl" />
      <div className="absolute top-10 right-1/4 w-48 h-48 bg-pink-500/10 rounded-full blur-2xl" />

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen px-4 py-16">
        {/* Hero Section */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-white/10 backdrop-blur-sm rounded-full border border-white/20 mb-6">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
            <span className="text-white/80 text-sm font-medium">{t("common.landing.hero.platform_active")}</span>
          </div>
          <h1 className="text-5xl md:text-6xl font-bold text-white mb-4 tracking-tight">
            {t("common.landing.hero.brand")}
          </h1>
          <p className="text-2xl md:text-3xl font-light text-indigo-200 mb-3">
            {t("common.landing.hero.tagline")}
          </p>
          <p className="text-lg text-indigo-300/80 max-w-md mx-auto">
            {t("common.landing.hero.subtitle")}
          </p>
        </div>

        {/* Persona Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl w-full mb-16">
          {personas.map((persona) => (
            <Link
              key={persona.title}
              to={persona.link}
              className="group relative bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl p-8 text-center transition-all duration-300 hover:bg-white/15 hover:border-white/30 hover:scale-105 hover:shadow-2xl hover:shadow-purple-500/10"
            >
              {/* Icon */}
              <div className={`inline-flex items-center justify-center w-16 h-16 rounded-xl ${persona.iconBg} mb-5 group-hover:scale-110 transition-transform duration-300`}>
                <persona.icon className={`w-8 h-8 ${persona.iconColor}`} />
              </div>

              {/* Title */}
              <h3 className="text-xl font-semibold text-white mb-2">
                {persona.title}
              </h3>

              {/* Description */}
              <p className="text-sm text-indigo-200/70 leading-relaxed">
                {persona.description}
              </p>

              {/* Arrow indicator */}
              <div className="mt-5 inline-flex items-center gap-1 text-sm font-medium text-indigo-300 group-hover:text-white transition-colors">
                <span>{t("common.landing.personas.sign_in")}</span>
                <svg className="w-4 h-4 group-hover:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </Link>
          ))}
        </div>

        {/* Footer */}
        <div className="text-center">
          <p className="text-indigo-300/60 text-sm">
            {t("common.landing.footer.powered_by")}{" "}
            <span className="font-medium text-indigo-200/80">{t("common.landing.footer.aws")}</span>
          </p>
        </div>
      </div>
    </div>
  );
};

export default LandingPage;
