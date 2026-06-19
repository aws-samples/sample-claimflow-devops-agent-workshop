import React from "react";
import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  HomeIcon,
  DocumentTextIcon,
  PlusCircleIcon,
  UsersIcon,
  ChartBarIcon,
  ArrowRightOnRectangleIcon,
  UserCircleIcon,
} from "@heroicons/react/24/outline";
import { useAuth } from "../contexts/AuthContext";

const Layout: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { t } = useTranslation();

  const handleLogout = async () => {
    await logout();
    navigate("/");
  };

  const navItems = [
    { to: "/dashboard", label: t("common.layout.nav.dashboard"), icon: HomeIcon, roles: ["policyholder", "adjudicator", "admin"] },
    { to: "/claims", label: t("common.layout.nav.claims"), icon: DocumentTextIcon, roles: ["policyholder", "adjudicator", "admin"] },
    { to: "/claims/new", label: t("common.layout.nav.new_claim"), icon: PlusCircleIcon, roles: ["policyholder"] },
    { to: "/admin/users", label: t("common.layout.nav.users"), icon: UsersIcon, roles: ["admin"] },
    { to: "/admin/analytics", label: t("common.layout.nav.analytics"), icon: ChartBarIcon, roles: ["admin", "adjudicator"] },
    { to: "/profile", label: t("common.layout.nav.profile"), icon: UserCircleIcon, roles: ["policyholder", "adjudicator", "admin"] },
  ];

  const visibleItems = navItems.filter(
    (item) => user && item.roles.includes(user.role)
  );

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-64 bg-gradient-to-b from-white to-blue-50 border-r border-gray-200 flex flex-col shadow-sm">
        {/* Brand */}
        <div className="h-16 flex items-center px-6 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">{t("common.layout.brand.logo_abbreviation")}</span>
            </div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
              {t("common.layout.brand.name")}
            </h1>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 py-6 space-y-1">
          {visibleItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? "bg-indigo-50 text-indigo-700 shadow-sm"
                    : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                }`
              }
            >
              <item.icon className="w-5 h-5" />
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* User section (no logout button here) */}
        <div className="p-4 border-t border-gray-100">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center">
              <UserCircleIcon className="w-5 h-5 text-indigo-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">
                {user?.user_id}
              </p>
              <p className="text-xs text-gray-500 capitalize">
                {user?.role}
              </p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
        {/* Header */}
        <header className="h-16 bg-white/80 backdrop-blur-sm border-b border-gray-200/60 flex items-center px-8 sticky top-0 z-10">
          <div className="flex items-center justify-between w-full">
            <h2 className="text-lg font-semibold text-gray-800">
              {t("common.layout.header.title")}
            </h2>
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-500">
                {t("common.layout.header.welcome_prefix")}{" "}
                <span className="font-medium text-gray-700">{user?.user_id}</span>
              </span>
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-700 capitalize">
                {user?.role}
              </span>
              <NavLink
                to="/profile"
                className="p-2 text-gray-400 hover:text-indigo-600 rounded-lg hover:bg-indigo-50 transition-colors"
                title={t("common.layout.header.profile_title")}
              >
                <UserCircleIcon className="w-5 h-5" />
              </NavLink>
              <button
                onClick={handleLogout}
                className="p-2 text-gray-400 hover:text-red-600 rounded-lg hover:bg-red-50 transition-colors"
                aria-label={t("common.layout.header.logout_label")}
                title={t("common.layout.header.logout_label")}
              >
                <ArrowRightOnRectangleIcon className="w-5 h-5" />
              </button>
            </div>
          </div>
        </header>

        {/* Page content */}
        <div className="p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export default Layout;
