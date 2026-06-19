import React, { useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../contexts/AuthContext";
import {
  ShieldCheckIcon,
  ClipboardDocumentCheckIcon,
  CogIcon,
  ArrowLeftIcon,
} from "@heroicons/react/24/outline";

interface PersonaConfig {
  titleKey: string;
  subtitleKey: string;
  descriptionKey: string;
  icon: React.FC<React.SVGProps<SVGSVGElement>>;
  gradient: string;
  accentColor: string;
  inputFocus: string;
  buttonGradient: string;
  showRegister: boolean;
}

const personaConfigs: Record<string, PersonaConfig> = {
  policyholder: {
    titleKey: "common.login.personas.policyholder_title",
    subtitleKey: "common.login.personas.policyholder_subtitle",
    descriptionKey: "common.login.personas.policyholder_description",
    icon: ShieldCheckIcon,
    gradient: "from-blue-600 via-blue-700 to-indigo-800",
    accentColor: "text-blue-600",
    inputFocus: "focus:ring-blue-500 focus:border-blue-500",
    buttonGradient: "from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800",
    showRegister: true,
  },
  adjudicator: {
    titleKey: "common.login.personas.adjudicator_title",
    subtitleKey: "common.login.personas.adjudicator_subtitle",
    descriptionKey: "common.login.personas.adjudicator_description",
    icon: ClipboardDocumentCheckIcon,
    gradient: "from-emerald-600 via-emerald-700 to-teal-800",
    accentColor: "text-emerald-600",
    inputFocus: "focus:ring-emerald-500 focus:border-emerald-500",
    buttonGradient: "from-emerald-600 to-emerald-700 hover:from-emerald-700 hover:to-emerald-800",
    showRegister: false,
  },
  admin: {
    titleKey: "common.login.personas.admin_title",
    subtitleKey: "common.login.personas.admin_subtitle",
    descriptionKey: "common.login.personas.admin_description",
    icon: CogIcon,
    gradient: "from-purple-600 via-purple-700 to-indigo-800",
    accentColor: "text-purple-600",
    inputFocus: "focus:ring-purple-500 focus:border-purple-500",
    buttonGradient: "from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800",
    showRegister: false,
  },
};

const LoginPage: React.FC = () => {
  const { persona } = useParams<{ persona: string }>();
  const navigate = useNavigate();
  const { login } = useAuth();
  const { t } = useTranslation();

  const [userId, setUserId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const config = personaConfigs[persona || "policyholder"] || personaConfigs.policyholder;
  const IconComponent = config.icon;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await login({ user_id: userId, password });
      navigate("/dashboard");
    } catch (err: any) {
      const message =
        err?.response?.data?.detail || err?.response?.data?.message || "Login failed. Please check your credentials.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`min-h-screen bg-gradient-to-br ${config.gradient} flex`}>
      {/* Left panel - Branding */}
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-between p-12 relative overflow-hidden">
        {/* Decorative elements */}
        <div className="absolute top-0 left-0 w-full h-full">
          <div className="absolute top-20 left-10 w-64 h-64 bg-white/5 rounded-full blur-3xl" />
          <div className="absolute bottom-20 right-10 w-80 h-80 bg-white/5 rounded-full blur-3xl" />
        </div>

        <div className="relative z-10">
          <Link
            to="/"
            className="inline-flex items-center gap-2 text-white/70 hover:text-white transition-colors text-sm"
          >
            <ArrowLeftIcon className="w-4 h-4" />
            {t("common.login.navigation.back_home")}
          </Link>
        </div>

        <div className="relative z-10 space-y-6">
          <div className="w-16 h-16 bg-white/10 backdrop-blur-sm rounded-2xl flex items-center justify-center border border-white/20">
            <IconComponent className="w-8 h-8 text-white" />
          </div>
          <h2 className="text-4xl font-bold text-white">{t(config.titleKey)}</h2>
          <p className="text-xl text-white/70 max-w-md">{t(config.descriptionKey)}</p>
        </div>

        <div className="relative z-10">
          <p className="text-white/40 text-sm">
            {t("common.login.footer.copyright", { year: new Date().getFullYear() })}
          </p>
        </div>
      </div>

      {/* Right panel - Login Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          {/* Mobile back link */}
          <div className="lg:hidden mb-8">
            <Link
              to="/"
              className="inline-flex items-center gap-2 text-white/70 hover:text-white transition-colors text-sm"
            >
              <ArrowLeftIcon className="w-4 h-4" />
              {t("common.login.navigation.back_home")}
            </Link>
          </div>

          {/* Card */}
          <div className="bg-white rounded-2xl shadow-2xl p-8">
            {/* Header */}
            <div className="text-center mb-8">
              <div className={`inline-flex items-center justify-center w-12 h-12 rounded-xl bg-gray-100 mb-4`}>
                <IconComponent className={`w-6 h-6 ${config.accentColor}`} />
              </div>
              <h1 className="text-2xl font-bold text-gray-900">{t(config.titleKey)}</h1>
              <p className="text-gray-500 mt-1 text-sm">{t(config.subtitleKey)}</p>
            </div>

            {/* Error */}
            {error && (
              <div className="mb-6 p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label htmlFor="user_id" className="block text-sm font-medium text-gray-700 mb-1.5">
                  {t("common.login.form.user_id")}
                </label>
                <input
                  id="user_id"
                  type="text"
                  value={userId}
                  onChange={(e) => setUserId(e.target.value)}
                  className={`w-full px-4 py-3 border border-gray-300 rounded-lg text-sm transition-all ${config.inputFocus} outline-none`}
                  placeholder={t("common.login.form.user_id_placeholder")}
                  required
                  autoComplete="username"
                />
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1.5">
                  {t("common.login.form.password")}
                </label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className={`w-full px-4 py-3 border border-gray-300 rounded-lg text-sm transition-all ${config.inputFocus} outline-none`}
                  placeholder={t("common.login.form.password_placeholder")}
                  required
                  autoComplete="current-password"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className={`w-full py-3 px-4 bg-gradient-to-r ${config.buttonGradient} text-white font-medium rounded-lg transition-all duration-200 shadow-lg shadow-gray-900/10 disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                {loading ? (
                  <span className="inline-flex items-center gap-2">
                    <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    {t("common.login.form.signing_in")}
                  </span>
                ) : (
                  t("common.login.form.sign_in")
                )}
              </button>
            </form>

            {/* Register link - only for policyholder */}
            {config.showRegister && (
              <div className="mt-6 text-center">
                <p className="text-sm text-gray-500">
                  {t("common.login.register.prompt")}{" "}
                  <Link to="/register" className={`font-medium ${config.accentColor} hover:underline`}>
                    {t("common.login.register.link")}
                  </Link>
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
