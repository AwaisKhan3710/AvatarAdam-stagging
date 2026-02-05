export interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  role: 'super_admin' | 'dealership_admin' | 'user';
  is_active: boolean;
  is_verified: boolean;
  dealership_id: number | null;
  last_login: string | null;
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface SignupRequest {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  role?: string;
  dealership_id?: number;
}

export interface UserCreate {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  role: 'super_admin' | 'dealership_admin' | 'user';
  dealership_id?: number | null;
}

export interface UserUpdate {
  email?: string;
  first_name?: string;
  last_name?: string;
  is_active?: boolean;
  role?: 'super_admin' | 'dealership_admin' | 'user';
}

export interface Dealership {
  id: number;
  name: string;
  is_active: boolean;
  address?: string;
  contact_email?: string;
  contact_phone?: string;
  rag_config?: RagConfig;
  created_at: string;
  updated_at: string;
}

export interface DealershipCreate {
  name: string;
  address?: string;
  contact_email?: string;
  contact_phone?: string;
}

export interface DealershipUpdate {
  name?: string;
  is_active?: boolean;
  address?: string;
  contact_email?: string;
  contact_phone?: string;
}

export interface RagConfig {
  embedding_model: string;
  chunk_size: number;
  chunk_overlap: number;
  namespace: string;
  topics: string[];
  metadata: Record<string, unknown>;
  status: string;
  document_counts: Record<string, number>;
}

export interface RagStatus {
  initialized: boolean;
  dealership_id?: number;
  dealership_name?: string;
  config?: RagConfig;
  total_documents?: number;
  total_chunks?: number;
  documents_by_topic?: Record<string, number>;
  message?: string;
}

export interface ChatMessage {
  message: string;
  mode: 'training' | 'roleplay';
  session_id?: string;
  conversation_history?: Array<{ role: string; content: string }>;
  dealership_id?: number;
}

// UI Chat Message for displaying conversation history
export interface UIChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
  audioBase64?: string; // Base64 encoded audio for playback
  isVoiceMessage?: boolean; // Whether this was originally a voice message
}

export interface ChatResponse {
  response: string;
  session_id: string;
  sources: Array<{ topic: string; filename: string; relevance: string }> | null;
  timestamp: string;
}

export interface VoiceChatRequest {
  audio_base64: string;
  mode: 'training' | 'roleplay';
  session_id?: string;
  mime_type?: string;
  dealership_id?: number;
}

export interface VoiceChatResponse {
  user_transcript: string;
  response_text: string;
  response_audio_base64: string;
  session_id: string;
  confidence: number;
  timestamp: string;
}

// Inaccuracy Report
export interface InaccuracyReportRequest {
  user_input: string;
  avatar_response: string;
  conversation_context?: Array<{ role: string; content: string }>;
  user_note?: string;
  session_id?: string;
  mode?: 'training' | 'roleplay';
  dealership_name?: string;
}

export interface InaccuracyReportResponse {
  success: boolean;
  message: string;
}

// Send to Team
export interface SendToTeamRequest {
  user_question: string;
  ai_response: string;
  conversation_history: Array<{ role: string; content: string }>;
  additional_notes?: string;
  session_id?: string;
  dealership_name?: string;
}

export interface SendToTeamResponse {
  success: boolean;
  message: string;
}
