import axios, { AxiosError, InternalAxiosRequestConfig, AxiosResponse } from 'axios';
import type {
  TokenResponse,
  LoginRequest,
  SignupRequest,
  User,
  UserCreate,
  UserUpdate,
  Dealership,
  RagStatus,
  ChatMessage,
  ChatResponse,
  VoiceChatRequest,
  VoiceChatResponse,
  InaccuracyReportRequest,
  InaccuracyReportResponse,
  SendToTeamRequest,
  SendToTeamResponse,
} from '../types';

/**
 * API client configuration
 * 
 * Uses VITE_API_URL environment variable for the backend URL.
 * In development, Vite proxy handles /api requests.
 * In production, set VITE_API_URL to your backend server URL.
 * 
 * Examples:
 * - Development: VITE_API_URL is not set, uses proxy via /api/v1
 * - Production: VITE_API_URL=https://api.yourdomain.com/api/v1
 */
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Export for WebSocket URL construction
export const getApiBaseUrl = () => API_BASE_URL;
export const getWsBaseUrl = () => {
  if (API_BASE_URL.startsWith('http')) {
    // Production: convert http(s) to ws(s)
    return API_BASE_URL.replace(/^http/, 'ws');
  }
  // Development: use current host
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/api/v1`;
};

// Flag to prevent multiple refresh requests
let isRefreshing = false;
// Queue of failed requests to retry after token refresh
let failedQueue: Array<{
  resolve: (value: unknown) => void;
  reject: (reason?: unknown) => void;
}> = [];

const processQueue = (error: Error | null, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

// Request interceptor - attach auth token to all requests
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor - handle token refresh on 401 errors
api.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // If error is 401 and we haven't already tried to refresh
    if (error.response?.status === 401 && !originalRequest._retry) {
      // Don't try to refresh if the failed request was the refresh endpoint itself
      if (originalRequest.url?.includes('/auth/refresh')) {
        // Refresh failed, clear tokens and redirect to login
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(error);
      }

      // Don't try to refresh for login/signup requests
      if (originalRequest.url?.includes('/auth/login') || originalRequest.url?.includes('/auth/signup')) {
        return Promise.reject(error);
      }

      if (isRefreshing) {
        // If already refreshing, queue this request
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return api(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = localStorage.getItem('refresh_token');

      if (!refreshToken) {
        // No refresh token, redirect to login
        localStorage.removeItem('access_token');
        window.location.href = '/login';
        return Promise.reject(error);
      }

      try {
        // Call refresh endpoint
        const response = await axios.post<TokenResponse>(
          `${API_BASE_URL}/auth/refresh`,
          { refresh_token: refreshToken },
          { headers: { 'Content-Type': 'application/json' } }
        );

        const { access_token, refresh_token: newRefreshToken } = response.data;

        // Store new tokens
        localStorage.setItem('access_token', access_token);
        localStorage.setItem('refresh_token', newRefreshToken);

        // Update authorization header
        originalRequest.headers.Authorization = `Bearer ${access_token}`;

        // Process queued requests
        processQueue(null, access_token);

        // Retry the original request
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh failed, clear tokens and redirect to login
        processQueue(refreshError as Error, null);
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  login: async (data: LoginRequest): Promise<TokenResponse> => {
    const response = await api.post('/auth/login', data);
    return response.data;
  },

  signup: async (data: SignupRequest): Promise<TokenResponse> => {
    const response = await api.post('/auth/signup', data);
    return response.data;
  },

  getMe: async (): Promise<User> => {
    const response = await api.get('/auth/me');
    return response.data;
  },

  refreshToken: async (refreshToken: string): Promise<TokenResponse> => {
    const response = await api.post('/auth/refresh', { refresh_token: refreshToken });
    return response.data;
  },

  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },
};

// Dealership API
export const dealershipApi = {
  list: async (): Promise<Dealership[]> => {
    const response = await api.get('/dealerships/');
    return response.data;
  },

  get: async (id: number): Promise<Dealership> => {
    const response = await api.get(`/dealerships/${id}`);
    return response.data;
  },

  create: async (data: Partial<Dealership>): Promise<Dealership> => {
    const response = await api.post('/dealerships/', data);
    return response.data;
  },

  update: async (id: number, data: Partial<Dealership>): Promise<Dealership> => {
    const response = await api.patch(`/dealerships/${id}`, data);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/dealerships/${id}`);
  },
};

// RAG API
export const ragApi = {
  initialize: async (dealershipId: number): Promise<{ message: string }> => {
    const response = await api.post(`/rag/${dealershipId}/initialize`);
    return response.data;
  },

  getStatus: async (dealershipId: number): Promise<RagStatus> => {
    const response = await api.get(`/rag/${dealershipId}/status`);
    return response.data;
  },

  uploadDocuments: async (
    dealershipId: number,
    topic: string,
    files: File[]
  ): Promise<{ message: string }> => {
    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));
    const response = await api.post(`/rag/${dealershipId}/upload/${topic}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  query: async (
    dealershipId: number,
    query: string,
    topics?: string[]
  ): Promise<{ query: string; results: unknown[]; count: number }> => {
    const response = await api.post(`/rag/${dealershipId}/query`, null, {
      params: { query, topics },
    });
    return response.data;
  },

  reset: async (dealershipId: number): Promise<{ message: string }> => {
    const response = await api.delete(`/rag/${dealershipId}/reset`);
    return response.data;
  },
};

// Chat API
export const chatApi = {
  send: async (data: ChatMessage, signal?: AbortSignal): Promise<ChatResponse> => {
    const response = await api.post('/chat/', data, { signal });
    return response.data;
  },

  getHistory: async (sessionId?: string): Promise<ChatResponse[]> => {
    const response = await api.get('/chat/history', {
      params: { session_id: sessionId },
    });
    return response.data;
  },

  /**
   * Pre-warm RAG context for a voice call session.
   * Call this when starting a voice call to reduce latency on first queries.
   */
  prewarmSession: async (sessionId: string, dealershipId?: number): Promise<{
    session_id: string;
    dealership_id: number;
    chunks_prewarmed: number;
    queries_run: number;
    elapsed_ms: number;
  }> => {
    const response = await api.post('/chat/prewarm', {
      session_id: sessionId,
      dealership_id: dealershipId,
    });
    return response.data;
  },

  /**
   * Clear RAG session context when a voice call ends.
   */
  clearSessionContext: async (sessionId: string): Promise<{ message: string }> => {
    const response = await api.post(`/chat/session/${sessionId}/clear`);
    return response.data;
  },
};

// Voice API
export const voiceApi = {
  chat: async (data: VoiceChatRequest): Promise<VoiceChatResponse> => {
    const response = await api.post('/voice/chat', data);
    return response.data;
  },

  chatFast: async (data: VoiceChatRequest): Promise<VoiceChatResponse> => {
    const response = await api.post('/voice/chat/fast', data);
    return response.data;
  },

  textToSpeech: async (text: string, voice?: string): Promise<{ audio_base64: string; text: string }> => {
    const response = await api.post('/voice/tts', { text, voice });
    return response.data;
  },

  speechToText: async (
    audioBase64: string,
    mimeType = 'audio/wav'
  ): Promise<{ transcript: string; confidence: number }> => {
    const response = await api.post('/voice/stt', {
      audio_base64: audioBase64,
      mime_type: mimeType,
    });
    return response.data;
  },

  clearSession: async (sessionId: string): Promise<{ message: string }> => {
    const response = await api.delete(`/voice/session/${sessionId}`);
    return response.data;
  },
};

// User Management API (Super Admin only)
export const userApi = {
  list: async (params?: {
    skip?: number;
    limit?: number;
    role?: string;
    is_active?: boolean;
    dealership_id?: number;
  }): Promise<User[]> => {
    const response = await api.get('/users/', { params });
    return response.data;
  },

  getCount: async (params?: {
    role?: string;
    is_active?: boolean;
    dealership_id?: number;
  }): Promise<{ count: number }> => {
    const response = await api.get('/users/count', { params });
    return response.data;
  },

  get: async (id: number): Promise<User> => {
    const response = await api.get(`/users/${id}`);
    return response.data;
  },

  create: async (data: UserCreate): Promise<User> => {
    const response = await api.post('/users/', data);
    return response.data;
  },

  update: async (id: number, data: UserUpdate): Promise<User> => {
    const response = await api.patch(`/users/${id}`, data);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/users/${id}`);
  },

  toggleActive: async (id: number): Promise<User> => {
    const response = await api.patch(`/users/${id}/toggle-active`);
    return response.data;
  },
};

// Report API
export const reportApi = {
  submitInaccuracy: async (data: InaccuracyReportRequest): Promise<InaccuracyReportResponse> => {
    const response = await api.post('/report/inaccuracy', data);
    return response.data;
  },

  sendToTeam: async (data: SendToTeamRequest): Promise<SendToTeamResponse> => {
    const response = await api.post('/report/send-to-team', data);
    return response.data;
  },
};

// Avatar API (HeyGen LiveAvatar)
export interface AvatarSessionResponse {
  session_id: string;
  session_token: string;
}

export const avatarApi = {
  createSession: async (voiceId?: string): Promise<AvatarSessionResponse> => {
    const response = await api.post('/avatar/session', { voice_id: voiceId });
    return response.data;
  },

  listVoices: async (): Promise<{ voices: unknown[] }> => {
    const response = await api.get('/avatar/voices');
    return response.data;
  },
};

export default api;
