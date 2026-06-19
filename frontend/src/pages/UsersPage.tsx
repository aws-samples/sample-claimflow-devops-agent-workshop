import React, { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
  UserCircleIcon,
  ShieldCheckIcon,
  ClipboardDocumentCheckIcon,
  CogIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import api from "../services/api";

interface User {
  user_id: string;
  full_name: string;
  email: string;
  role: string;
  status: string;
  created_at: string;
  last_login: string | null;
}

interface AddUserForm {
  user_id: string;
  email: string;
  full_name: string;
  password: string;
  role: string;
}

// Mock users data (fallback if API is unavailable)
const mockUsers: User[] = [
  { user_id: "testuser2", full_name: "Priya Sharma", email: "priya@example.com", role: "policyholder", status: "active", created_at: "2026-05-25", last_login: "2026-05-25" },
  { user_id: "adjudicator1", full_name: "Rajesh Kumar", email: "rajesh@claimflow.in", role: "adjudicator", status: "active", created_at: "2026-05-25", last_login: "2026-05-25" },
  { user_id: "admin1", full_name: "Anita Desai", email: "anita@claimflow.in", role: "admin", status: "active", created_at: "2026-05-25", last_login: "2026-05-25" },
  { user_id: "user_demo1", full_name: "Amit Patel", email: "amit@example.com", role: "policyholder", status: "active", created_at: "2026-05-20", last_login: "2026-05-24" },
  { user_id: "user_demo2", full_name: "Sneha Reddy", email: "sneha@example.com", role: "policyholder", status: "inactive", created_at: "2026-05-15", last_login: "2026-05-18" },
];

const roleIcons: Record<string, React.FC<React.SVGProps<SVGSVGElement>>> = {
  policyholder: ShieldCheckIcon,
  adjudicator: ClipboardDocumentCheckIcon,
  admin: CogIcon,
};

const roleColors: Record<string, string> = {
  policyholder: "bg-blue-100 text-blue-700",
  adjudicator: "bg-emerald-100 text-emerald-700",
  admin: "bg-purple-100 text-purple-700",
};

const statusColors: Record<string, string> = {
  active: "bg-green-100 text-green-700",
  inactive: "bg-gray-100 text-gray-500",
};

const UsersPage: React.FC = () => {
  const { t } = useTranslation();
  const [filter, setFilter] = useState<string>("all");
  const [users, setUsers] = useState<User[]>(mockUsers);
  const [loading, setLoading] = useState<boolean>(true);

  // Modal states
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [editRole, setEditRole] = useState("");
  const [addForm, setAddForm] = useState<AddUserForm>({
    user_id: "",
    email: "",
    full_name: "",
    password: "",
    role: "policyholder",
  });
  const [formError, setFormError] = useState<string | null>(null);
  const [formLoading, setFormLoading] = useState(false);

  const fetchUsers = async () => {
    try {
      const response = await api.get("/api/auth/users");
      if (response.data && Array.isArray(response.data) && response.data.length > 0) {
        setUsers(response.data);
      } else {
        setUsers(mockUsers);
      }
    } catch {
      setUsers(mockUsers);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const filteredUsers = filter === "all" ? users : users.filter((u) => u.role === filter);

  const stats = {
    total: users.length,
    policyholders: users.filter((u) => u.role === "policyholder").length,
    adjudicators: users.filter((u) => u.role === "adjudicator").length,
    admins: users.filter((u) => u.role === "admin").length,
  };

  // Add User handler
  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!addForm.user_id || !addForm.email || !addForm.full_name || !addForm.password) {
      setFormError(t("common.users.errors.all_required"));
      return;
    }

    setFormLoading(true);
    try {
      await api.post("/api/auth/register", {
        user_id: addForm.user_id,
        email: addForm.email,
        full_name: addForm.full_name,
        password: addForm.password,
        role: addForm.role,
      });
      setShowAddModal(false);
      setAddForm({ user_id: "", email: "", full_name: "", password: "", role: "policyholder" });
      await fetchUsers();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setFormError(error.response?.data?.detail || t("common.users.errors.create_failed"));
    } finally {
      setFormLoading(false);
    }
  };

  // Edit Role handler
  const handleEditRole = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingUser || !editRole) return;

    setFormError(null);
    setFormLoading(true);
    try {
      await api.put(`/api/auth/users/${editingUser.user_id}/role`, { role: editRole });
      setShowEditModal(false);
      setEditingUser(null);
      setEditRole("");
      await fetchUsers();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setFormError(error.response?.data?.detail || t("common.users.errors.update_role_failed"));
    } finally {
      setFormLoading(false);
    }
  };

  // Deactivate handler
  const handleDeactivate = async (userId: string) => {
    if (!window.confirm(t("common.users.errors.deactivate_confirm", { userId }))) return;

    try {
      await api.put(`/api/auth/users/${userId}/deactivate`);
      await fetchUsers();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      // Surfacing via console keeps this sample simple; a production app would
      // show this in an inline error banner.
      console.error(error.response?.data?.detail || t("common.users.errors.deactivate_failed"));
    }
  };

  const openEditModal = (user: User) => {
    setEditingUser(user);
    setEditRole(user.role);
    setFormError(null);
    setShowEditModal(true);
  };

  const filterLabels: Record<string, string> = {
    all: t("common.users.filter.all"),
    policyholder: t("common.users.add_modal.role_policyholder") + "s",
    adjudicator: t("common.users.add_modal.role_adjudicator") + "s",
    admin: t("common.users.add_modal.role_admin") + "s",
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t("common.users.header.title")}</h1>
          <p className="text-gray-500 mt-1">{t("common.users.header.subtitle")}</p>
        </div>
        <button
          onClick={() => { setFormError(null); setShowAddModal(true); }}
          className="px-4 py-2.5 bg-gradient-to-r from-indigo-600 to-indigo-700 text-white text-sm font-medium rounded-lg hover:from-indigo-700 hover:to-indigo-800 transition-all shadow-lg shadow-indigo-900/10"
        >
          {t("common.users.header.add_user")}
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-4 text-center">
          <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
          <p className="text-xs text-gray-500">{t("common.users.stats.total")}</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-4 text-center">
          <p className="text-2xl font-bold text-blue-600">{stats.policyholders}</p>
          <p className="text-xs text-gray-500">{t("common.users.stats.policyholders")}</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-4 text-center">
          <p className="text-2xl font-bold text-emerald-600">{stats.adjudicators}</p>
          <p className="text-xs text-gray-500">{t("common.users.stats.adjudicators")}</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-4 text-center">
          <p className="text-2xl font-bold text-purple-600">{stats.admins}</p>
          <p className="text-xs text-gray-500">{t("common.users.stats.admins")}</p>
        </div>
      </div>

      {/* Filter */}
      <div className="flex gap-2">
        {["all", "policyholder", "adjudicator", "admin"].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors capitalize ${
              filter === f
                ? "bg-indigo-100 text-indigo-700"
                : "bg-white text-gray-600 border border-gray-200 hover:bg-gray-50"
            }`}
          >
            {filterLabels[f]}
          </button>
        ))}
      </div>

      {/* Users Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-500">{t("common.users.table.loading")}</div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t("common.users.table.user")}</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t("common.users.table.role")}</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t("common.users.table.status")}</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t("common.users.table.last_login")}</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t("common.users.table.actions")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredUsers.map((user) => {
                const RoleIcon = roleIcons[user.role] || UserCircleIcon;
                return (
                  <tr key={user.user_id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-indigo-100 rounded-full flex items-center justify-center">
                          <UserCircleIcon className="w-6 h-6 text-indigo-600" />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-900">{user.full_name}</p>
                          <p className="text-xs text-gray-500">{user.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium capitalize ${roleColors[user.role]}`}>
                        <RoleIcon className="w-3.5 h-3.5" />
                        {user.role}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex px-2.5 py-1 rounded-full text-xs font-medium capitalize ${statusColors[user.status] || "bg-gray-100 text-gray-500"}`}>
                        {user.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {user.last_login || t("common.users.table.never_logged_in")}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => openEditModal(user)}
                          className="text-sm text-indigo-600 hover:text-indigo-700 font-medium"
                        >
                          {t("common.users.table.edit")}
                        </button>
                        {user.status === "active" && (
                          <button
                            onClick={() => handleDeactivate(user.user_id)}
                            className="text-sm text-red-600 hover:text-red-700 font-medium"
                          >
                            {t("common.users.table.deactivate")}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Add User Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
              <h3 className="text-lg font-semibold text-gray-900">{t("common.users.add_modal.title")}</h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="p-1 text-gray-400 hover:text-gray-600 rounded"
              >
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleAddUser} className="p-6 space-y-4">
              {formError && (
                <div className="px-4 py-3 rounded-lg text-sm font-medium bg-red-50 text-red-700 border border-red-200">
                  {formError}
                </div>
              )}
              <div>
                <label htmlFor="add-user-id" className="block text-sm font-medium text-gray-700 mb-1">{t("common.users.add_modal.user_id")}</label>
                <input
                  id="add-user-id"
                  type="text"
                  value={addForm.user_id}
                  onChange={(e) => setAddForm({ ...addForm, user_id: e.target.value })}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder={t("common.users.add_modal.user_id_placeholder")}
                />
              </div>
              <div>
                <label htmlFor="add-email" className="block text-sm font-medium text-gray-700 mb-1">{t("common.users.add_modal.email")}</label>
                <input
                  id="add-email"
                  type="email"
                  value={addForm.email}
                  onChange={(e) => setAddForm({ ...addForm, email: e.target.value })}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder={t("common.users.add_modal.email_placeholder")}
                />
              </div>
              <div>
                <label htmlFor="add-fullname" className="block text-sm font-medium text-gray-700 mb-1">{t("common.users.add_modal.full_name")}</label>
                <input
                  id="add-fullname"
                  type="text"
                  value={addForm.full_name}
                  onChange={(e) => setAddForm({ ...addForm, full_name: e.target.value })}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder={t("common.users.add_modal.full_name_placeholder")}
                />
              </div>
              <div>
                <label htmlFor="add-password" className="block text-sm font-medium text-gray-700 mb-1">{t("common.users.add_modal.password")}</label>
                <input
                  id="add-password"
                  type="password"
                  value={addForm.password}
                  onChange={(e) => setAddForm({ ...addForm, password: e.target.value })}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder={t("common.users.add_modal.password_placeholder")}
                />
              </div>
              <div>
                <label htmlFor="add-role" className="block text-sm font-medium text-gray-700 mb-1">{t("common.users.add_modal.role")}</label>
                <select
                  id="add-role"
                  value={addForm.role}
                  onChange={(e) => setAddForm({ ...addForm, role: e.target.value })}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                >
                  <option value="policyholder">{t("common.users.add_modal.role_policyholder")}</option>
                  <option value="adjudicator">{t("common.users.add_modal.role_adjudicator")}</option>
                  <option value="admin">{t("common.users.add_modal.role_admin")}</option>
                </select>
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                >
                  {t("common.users.add_modal.cancel")}
                </button>
                <button
                  type="submit"
                  disabled={formLoading}
                  className="px-4 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-indigo-600 to-indigo-700 rounded-lg hover:from-indigo-700 hover:to-indigo-800 transition-all disabled:opacity-50"
                >
                  {formLoading ? t("common.users.add_modal.creating") : t("common.users.add_modal.create")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Role Modal */}
      {showEditModal && editingUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
              <h3 className="text-lg font-semibold text-gray-900">{t("common.users.edit_modal.title")}</h3>
              <button
                onClick={() => setShowEditModal(false)}
                className="p-1 text-gray-400 hover:text-gray-600 rounded"
              >
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleEditRole} className="p-6 space-y-4">
              {formError && (
                <div className="px-4 py-3 rounded-lg text-sm font-medium bg-red-50 text-red-700 border border-red-200">
                  {formError}
                </div>
              )}
              <div>
                <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">{t("common.users.edit_modal.user")}</label>
                <p className="text-sm font-medium text-gray-900">{editingUser.full_name} ({editingUser.user_id})</p>
              </div>
              <div>
                <label htmlFor="edit-role" className="block text-sm font-medium text-gray-700 mb-1">{t("common.users.edit_modal.role")}</label>
                <select
                  id="edit-role"
                  value={editRole}
                  onChange={(e) => setEditRole(e.target.value)}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                >
                  <option value="policyholder">{t("common.users.edit_modal.role_policyholder")}</option>
                  <option value="adjudicator">{t("common.users.edit_modal.role_adjudicator")}</option>
                  <option value="admin">{t("common.users.edit_modal.role_admin")}</option>
                </select>
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowEditModal(false)}
                  className="px-4 py-2.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                >
                  {t("common.users.edit_modal.cancel")}
                </button>
                <button
                  type="submit"
                  disabled={formLoading}
                  className="px-4 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-indigo-600 to-indigo-700 rounded-lg hover:from-indigo-700 hover:to-indigo-800 transition-all disabled:opacity-50"
                >
                  {formLoading ? t("common.users.edit_modal.saving") : t("common.users.edit_modal.save")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default UsersPage;
