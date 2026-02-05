import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { ragApi, dealershipApi } from '../services/api';
import toast from 'react-hot-toast';
import { Database, Upload, Trash2, Check, Loader2, RefreshCw, FileText, Building2 } from 'lucide-react';
import type { RagStatus, Dealership } from '../types';
import clsx from 'clsx';

const TOPICS = [
  { id: 'books', name: 'Books', description: 'Training books and manuals' },
  { id: 'objection_handling', name: 'Objection Handling', description: 'Common objections and responses' },
  { id: 'playbooks', name: 'Playbooks', description: 'Sales playbooks and strategies' },
  { id: 'videos', name: 'Videos', description: 'Video transcripts and summaries' },
  { id: 'compliance', name: 'Compliance', description: 'Compliance and regulatory materials' },
  { id: 'product_knowledge', name: 'Product Knowledge', description: 'Product specs and features' },
];

export default function RagManagement() {
  const { user } = useAuth();
  const [status, setStatus] = useState<RagStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isInitializing, setIsInitializing] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [uploadingTopic, setUploadingTopic] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);
  
  // Super admin dealership selection
  const [dealerships, setDealerships] = useState<Dealership[]>([]);
  const [selectedDealershipId, setSelectedDealershipId] = useState<number | null>(null);
  
  const isSuperAdmin = user?.role === 'super_admin';
  const dealershipId = isSuperAdmin ? selectedDealershipId : user?.dealership_id;

  // Load dealerships for super admin
  useEffect(() => {
    if (isSuperAdmin) {
      dealershipApi.list().then((data) => {
        setDealerships(data);
        if (data.length > 0 && !selectedDealershipId) {
          setSelectedDealershipId(data[0].id);
        }
      });
    }
  }, [isSuperAdmin]);

  const fetchStatus = async () => {
    if (!dealershipId) return;
    try {
      setIsLoading(true);
      const data = await ragApi.getStatus(dealershipId);
      setStatus(data);
    } catch (error) {
      console.error('Failed to fetch RAG status:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (dealershipId) {
      fetchStatus();
    }
  }, [dealershipId]);

  const handleInitialize = async () => {
    if (!dealershipId) return;
    setIsInitializing(true);
    try {
      await ragApi.initialize(dealershipId);
      toast.success('RAG initialized successfully!');
      await fetchStatus();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { error?: { message?: string } } } };
      toast.error(err.response?.data?.error?.message || 'Failed to initialize RAG');
    } finally {
      setIsInitializing(false);
    }
  };

  const handleReset = async () => {
    if (!dealershipId) return;
    if (!confirm('Are you sure you want to reset RAG? This will delete all uploaded documents.')) {
      return;
    }
    setIsResetting(true);
    try {
      await ragApi.reset(dealershipId);
      toast.success('RAG reset successfully!');
      await fetchStatus();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { error?: { message?: string } } } };
      toast.error(err.response?.data?.error?.message || 'Failed to reset RAG');
    } finally {
      setIsResetting(false);
    }
  };

  const handleUploadClick = (topicId: string) => {
    setSelectedTopic(topicId);
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0 || !selectedTopic || !dealershipId) return;

    setUploadingTopic(selectedTopic);
    try {
      await ragApi.uploadDocuments(dealershipId, selectedTopic, Array.from(files));
      toast.success(`Successfully uploaded ${files.length} file(s)!`);
      await fetchStatus();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { error?: { message?: string } } } };
      toast.error(err.response?.data?.error?.message || 'Failed to upload documents');
    } finally {
      setUploadingTopic(null);
      setSelectedTopic(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  if (!isSuperAdmin && !user?.dealership_id) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <p className="text-yellow-800">
          You are not associated with a dealership. Please contact your administrator.
        </p>
      </div>
    );
  }

  if (isSuperAdmin && dealerships.length === 0) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <p className="text-yellow-800">
          No dealerships found. Please create a dealership first.
        </p>
      </div>
    );
  }

  if (isLoading && dealershipId) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    );
  }

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6 sm:mb-8">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900">RAG Management</h1>
          <p className="mt-1 text-sm sm:text-base text-gray-600">
            Manage your dealership's knowledge base for AI training.
          </p>
        </div>
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 sm:gap-4">
          {/* Dealership Selector for Super Admin */}
          {isSuperAdmin && dealerships.length > 0 && (
            <div className="flex items-center gap-2">
              <Building2 className="w-5 h-5 text-gray-400 hidden sm:block" />
              <select
                value={selectedDealershipId || ''}
                onChange={(e) => setSelectedDealershipId(Number(e.target.value))}
                className="w-full sm:w-auto px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-sm"
              >
                {dealerships.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </div>
          )}
          <button
            onClick={fetchStatus}
            className="flex items-center justify-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </button>
        </div>
      </div>

      {/* Status Card */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 sm:p-6 mb-6 sm:mb-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center">
            <div
              className={clsx(
                'w-10 h-10 sm:w-12 sm:h-12 rounded-lg flex items-center justify-center flex-shrink-0',
                status?.initialized ? 'bg-green-100' : 'bg-gray-100'
              )}
            >
              {status?.initialized ? (
                <Check className="w-5 h-5 sm:w-6 sm:h-6 text-green-600" />
              ) : (
                <Database className="w-5 h-5 sm:w-6 sm:h-6 text-gray-400" />
              )}
            </div>
            <div className="ml-3 sm:ml-4">
              <h3 className="text-base sm:text-lg font-semibold text-gray-900">
                {status?.initialized ? 'RAG Initialized' : 'RAG Not Initialized'}
              </h3>
              <p className="text-xs sm:text-sm text-gray-600">
                {status?.initialized
                  ? `${status.total_documents || 0} documents (${status.total_chunks || 0} chunks)`
                  : 'Initialize RAG to start uploading training materials'}
              </p>
            </div>
          </div>
          <div className="flex space-x-3">
            {status?.initialized ? (
              <button
                onClick={handleReset}
                disabled={isResetting}
                className="flex-1 sm:flex-none flex items-center justify-center px-4 py-2 text-sm font-medium text-red-600 bg-red-50 border border-red-200 rounded-lg hover:bg-red-100 disabled:opacity-50"
              >
                {isResetting ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Trash2 className="w-4 h-4 mr-2" />
                )}
                Reset
              </button>
            ) : (
              <button
                onClick={handleInitialize}
                disabled={isInitializing}
                className="flex-1 sm:flex-none flex items-center justify-center px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-50"
              >
                {isInitializing ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Database className="w-4 h-4 mr-2" />
                )}
                Initialize RAG
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Topics Grid */}
      {status?.initialized && (
        <div>
          <h2 className="text-base sm:text-lg font-semibold text-gray-900 mb-4">Knowledge Base Topics</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
            {TOPICS.map((topic) => {
              const docCount = status.documents_by_topic?.[topic.id] || 0;
              const isUploading = uploadingTopic === topic.id;

              return (
                <div
                  key={topic.id}
                  className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 sm:p-6"
                >
                  <div className="flex items-center justify-between mb-3 sm:mb-4">
                    <div className="w-9 h-9 sm:w-10 sm:h-10 bg-primary-100 rounded-lg flex items-center justify-center">
                      <FileText className="w-4 h-4 sm:w-5 sm:h-5 text-primary-600" />
                    </div>
                    <span className="text-xs sm:text-sm font-medium text-gray-500">
                      {docCount} doc{docCount !== 1 ? 's' : ''}
                    </span>
                  </div>
                  <h3 className="font-semibold text-gray-900 text-sm sm:text-base">{topic.name}</h3>
                  <p className="mt-1 text-xs sm:text-sm text-gray-600">{topic.description}</p>
                  <button
                    onClick={() => handleUploadClick(topic.id)}
                    disabled={isUploading}
                    className="mt-3 sm:mt-4 w-full flex items-center justify-center px-3 sm:px-4 py-2 text-xs sm:text-sm font-medium text-primary-600 bg-primary-50 border border-primary-200 rounded-lg hover:bg-primary-100 disabled:opacity-50"
                  >
                    {isUploading ? (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <Upload className="w-4 h-4 mr-2" />
                    )}
                    Upload Documents
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.docx,.txt"
        onChange={handleFileChange}
        className="hidden"
      />
    </div>
  );
}
