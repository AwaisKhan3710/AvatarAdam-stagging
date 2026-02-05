import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { userApi, dealershipApi } from '../services/api';
import type { User, UserCreate, UserUpdate, Dealership } from '../types';
import { Users, Plus, Pencil, Trash2, X, AlertCircle, UserCheck, UserX, Shield, Building2 } from 'lucide-react';

interface UserFormData {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  role: 'super_admin' | 'dealership_admin' | 'user';
  dealership_id: number | null;
}

const emptyForm: UserFormData = {
  email: '',
  password: '',
  first_name: '',
  last_name: '',
  role: 'user',
  dealership_id: null,
};

const roleLabels: Record<string, string> = {
  super_admin: 'Super Admin',
  dealership_admin: 'Dealership Admin',
  user: 'User',
};

const roleColors: Record<string, string> = {
  super_admin: 'bg-purple-100 text-purple-800',
  dealership_admin: 'bg-blue-100 text-blue-800',
  user: 'bg-gray-100 text-gray-800',
};

export default function UserManagement() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [dealerships, setDealerships] = useState<Dealership[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formData, setFormData] = useState<UserFormData>(emptyForm);
  const [submitting, setSubmitting] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null);
  const [filterRole, setFilterRole] = useState<string>('');
  const [filterActive, setFilterActive] = useState<string>('');

  const isSuperAdmin = currentUser?.role === 'super_admin';

  useEffect(() => {
    if (isSuperAdmin) {
      loadUsers();
      loadDealerships();
    }
  }, [isSuperAdmin]);

  const loadUsers = async () => {
    try {
      setLoading(true);
      setError(null);
      const params: Record<string, unknown> = {};
      if (filterRole) params.role = filterRole;
      if (filterActive !== '') params.is_active = filterActive === 'true';
      const data = await userApi.list(params);
      setUsers(data);
    } catch (err) {
      setError('Failed to load users');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadDealerships = async () => {
    try {
      const data = await dealershipApi.list();
      setDealerships(data);
    } catch (err) {
      console.error('Failed to load dealerships:', err);
    }
  };

  useEffect(() => {
    if (isSuperAdmin) {
      loadUsers();
    }
  }, [filterRole, filterActive]);

  const openCreateModal = () => {
    setFormData(emptyForm);
    setEditingId(null);
    setShowModal(true);
  };

  const openEditModal = (user: User) => {
    setFormData({
      email: user.email,
      password: '', // Don't show password
      first_name: user.first_name,
      last_name: user.last_name,
      role: user.role,
      dealership_id: user.dealership_id,
    });
    setEditingId(user.id);
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setEditingId(null);
    setFormData(emptyForm);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const email = formData.email.trim();
    const firstName = formData.first_name.trim();
    const lastName = formData.last_name.trim();
    const password = formData.password;

    // Validation for create mode
    if (!editingId) {
      if (!email) {
        setError('Email is required');
        return;
      }
      if (!firstName) {
        setError('First name is required');
        return;
      }
      if (firstName.length > 100) {
        setError('First name must be 100 characters or less');
        return;
      }
      if (!lastName) {
        setError('Last name is required');
        return;
      }
      if (lastName.length > 100) {
        setError('Last name must be 100 characters or less');
        return;
      }
      if (!password) {
        setError('Password is required');
        return;
      }
      if (password.length < 8) {
        setError('Password must be at least 8 characters');
        return;
      }
      if (password.length > 100) {
        setError('Password must be 100 characters or less');
        return;
      }
    }

    // Validation for edit mode (only validate if field is provided)
    if (editingId) {
      if (firstName && firstName.length > 100) {
        setError('First name must be 100 characters or less');
        return;
      }
      if (lastName && lastName.length > 100) {
        setError('Last name must be 100 characters or less');
        return;
      }
    }

    try {
      setSubmitting(true);

      if (editingId) {
        const updatePayload: UserUpdate = {};
        if (email) updatePayload.email = email;
        if (firstName) updatePayload.first_name = firstName;
        if (lastName) updatePayload.last_name = lastName;
        if (formData.role) updatePayload.role = formData.role;
        await userApi.update(editingId, updatePayload);
      } else {
        const createPayload: UserCreate = {
          email,
          password,
          first_name: firstName,
          last_name: lastName,
          role: formData.role,
          dealership_id: formData.dealership_id,
        };
        await userApi.create(createPayload);
      }

      await loadUsers();
      closeModal();
    } catch (err: unknown) {
      // Handle axios error response
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { error?: { message?: string } } } };
        const message = axiosErr.response?.data?.error?.message;
        if (message) {
          setError(message);
          return;
        }
      }
      const errorMessage = err instanceof Error ? err.message : 'Failed to save user';
      setError(errorMessage);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      setSubmitting(true);
      await userApi.delete(id);
      setDeleteConfirm(null);
      await loadUsers();
    } catch (err) {
      setError('Failed to delete user');
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  };

  const toggleActive = async (user: User) => {
    try {
      await userApi.toggleActive(user.id);
      await loadUsers();
    } catch (err) {
      setError('Failed to update user status');
      console.error(err);
    }
  };

  const getDealershipName = (dealershipId: number | null) => {
    if (!dealershipId) return '-';
    const dealership = dealerships.find(d => d.id === dealershipId);
    return dealership?.name || `ID: ${dealershipId}`;
  };

  if (!isSuperAdmin) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px]">
        <AlertCircle className="w-16 h-16 text-red-500 mb-4" />
        <h2 className="text-xl font-semibold text-gray-900 mb-2">Access Denied</h2>
        <p className="text-gray-600">Only Super Admins can manage users.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 mb-6">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900">User Management</h1>
          <p className="mt-1 text-sm sm:text-base text-gray-600">Manage all users in the system</p>
        </div>
        <button
          onClick={openCreateModal}
          className="inline-flex items-center justify-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
        >
          <Plus className="w-5 h-5 mr-2" />
          Add User
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
        <div className="flex flex-wrap gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
            <select
              value={filterRole}
              onChange={(e) => setFilterRole(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="">All Roles</option>
              <option value="super_admin">Super Admin</option>
              <option value="dealership_admin">Dealership Admin</option>
              <option value="user">User</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <select
              value={filterActive}
              onChange={(e) => setFilterActive(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="">All Status</option>
              <option value="true">Active</option>
              <option value="false">Inactive</option>
            </select>
          </div>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center text-red-700">
          <AlertCircle className="w-5 h-5 mr-2 flex-shrink-0" />
          {error}
          <button onClick={() => setError(null)} className="ml-auto">
            <X className="w-5 h-5" />
          </button>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      ) : users.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg shadow-sm border border-gray-200">
          <Users className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No users found</h3>
          <p className="text-gray-600 mb-4">Get started by adding your first user.</p>
          <button
            onClick={openCreateModal}
            className="inline-flex items-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            <Plus className="w-5 h-5 mr-2" />
            Add User
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    User
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Role
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Dealership
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Created
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {users.map((user) => (
                  <tr key={user.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="flex-shrink-0 h-10 w-10 rounded-full bg-primary-100 flex items-center justify-center">
                          <span className="text-primary-600 font-medium">
                            {user.first_name[0]}{user.last_name[0]}
                          </span>
                        </div>
                        <div className="ml-4">
                          <div className="text-sm font-medium text-gray-900">
                            {user.first_name} {user.last_name}
                            {user.id === currentUser?.id && (
                              <span className="ml-2 text-xs text-gray-500">(You)</span>
                            )}
                          </div>
                          <div className="text-sm text-gray-500">{user.email}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${roleColors[user.role]}`}>
                        {user.role === 'super_admin' && <Shield className="w-3 h-3 mr-1" />}
                        {user.role === 'dealership_admin' && <Building2 className="w-3 h-3 mr-1" />}
                        {roleLabels[user.role]}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {getDealershipName(user.dealership_id)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <button
                        onClick={() => toggleActive(user)}
                        disabled={user.id === currentUser?.id}
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          user.is_active
                            ? 'bg-green-100 text-green-800 hover:bg-green-200'
                            : 'bg-red-100 text-red-800 hover:bg-red-200'
                        } ${user.id === currentUser?.id ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                      >
                        {user.is_active ? (
                          <>
                            <UserCheck className="w-3 h-3 mr-1" />
                            Active
                          </>
                        ) : (
                          <>
                            <UserX className="w-3 h-3 mr-1" />
                            Inactive
                          </>
                        )}
                      </button>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(user.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => openEditModal(user)}
                          className="p-2 text-gray-600 hover:text-primary-600 hover:bg-gray-100 rounded-lg"
                          title="Edit"
                        >
                          <Pencil className="w-4 h-4" />
                        </button>
                        {deleteConfirm === user.id ? (
                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => handleDelete(user.id)}
                              disabled={submitting || user.id === currentUser?.id}
                              className="p-2 text-white bg-red-600 hover:bg-red-700 rounded-lg disabled:opacity-50"
                              title="Confirm Delete"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => setDeleteConfirm(null)}
                              className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg"
                              title="Cancel"
                            >
                              <X className="w-4 h-4" />
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() => setDeleteConfirm(user.id)}
                            disabled={user.id === currentUser?.id}
                            className="p-2 text-gray-600 hover:text-red-600 hover:bg-gray-100 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
                            title={user.id === currentUser?.id ? "Cannot delete yourself" : "Delete"}
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Create/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">
                {editingId ? 'Edit User' : 'Create User'}
              </h2>
              <button
                onClick={closeModal}
                className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="p-4 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    First Name {!editingId && '*'}
                  </label>
                  <input
                    type="text"
                    value={formData.first_name}
                    onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    required={!editingId}
                    minLength={1}
                    maxLength={100}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Last Name {!editingId && '*'}
                  </label>
                  <input
                    type="text"
                    value={formData.last_name}
                    onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    required={!editingId}
                    minLength={1}
                    maxLength={100}
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email {!editingId && '*'}
                </label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  required={!editingId}
                  maxLength={255}
                />
              </div>
              {!editingId && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Password *
                  </label>
                  <input
                    type="password"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    required
                    minLength={8}
                    maxLength={100}
                  />
                  <p className="mt-1 text-xs text-gray-500">8-100 characters</p>
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Role *
                </label>
                <select
                  value={formData.role}
                  onChange={(e) => setFormData({ ...formData, role: e.target.value as UserFormData['role'] })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                >
                  <option value="user">User</option>
                  <option value="dealership_admin">Dealership Admin</option>
                  <option value="super_admin">Super Admin</option>
                </select>
              </div>
              {(formData.role === 'dealership_admin' || formData.role === 'user') && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Dealership
                  </label>
                  <select
                    value={formData.dealership_id || ''}
                    onChange={(e) => setFormData({ ...formData, dealership_id: e.target.value ? Number(e.target.value) : null })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  >
                    <option value="">No Dealership</option>
                    {dealerships.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
                <button
                  type="button"
                  onClick={closeModal}
                  className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                >
                  {submitting ? 'Saving...' : editingId ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
