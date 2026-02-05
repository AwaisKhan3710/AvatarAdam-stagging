# AvatarAdam - Complete Architecture & Flow Analysis

## 📊 System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (React + TypeScript)                      │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ Pages: Login, Dashboard, Chat, VoiceChat, RagManagement, etc.       │   │
│  │ Components: Layout, ChatPanel, AuthContext                          │   │
│  │ Services: API Client (Axios), WebSocket Management                  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
                    ┌───────────────────────────────┐
                    │   HTTP/WebSocket (REST API)   │
                    │   CORS Enabled                │
                    │   JWT Authentication          │
                    └───────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI + Python)                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ API Routes (v1):                                                     │   │
│  │  • /auth - Login, Signup, Refresh Token, Logout                     │   │
│  │  • /users - User Management                                         │   │
│  │  • /dealerships - Dealership Management                             │   │
│  │  • /chat - Text Chat (Training & Role-play)                         │   │
│  │  • /voice - Voice Chat (WebSocket)                                  │   │
│  │  • /rag - RAG Management & Document Upload                          │   │
│  │  • /avatar - HeyGen Avatar Session Management                       │   │
│  │  • /report - Inaccuracy Reporting                                   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ Core Services:                                                       │   │
│  │  • LLMService (OpenRouter → GPT-4o)                                 │   │
│  │  • RAGService (Pinecone Vector DB + LangChain)                      │   │
│  │  • RealtimeVoiceService (Whisper STT + ElevenLabs TTS)              │   │
│  │  • AvatarService (HeyGen LiveAvatar Integration)                    │   │
│  │  • EmailService (Mailgun)                                           │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ Middleware & Security:                                               │   │
│  │  • CORS Middleware                                                   │   │
│  │  • Security Headers Middleware                                       │   │
│  │  • Rate Limiting (SlowAPI)                                           │   │
│  │  • JWT Authentication & Authorization                               │   │
│  │  • Exception Handling                                                │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ Database Models:                                                     │   │
│  │  • User (with roles: super_admin, dealership_admin, user)           │   │
│  │  • Dealership (with RAG config)                                      │   │
│  │  • Document & DocumentChunk (for RAG)                                │   │
│  │  • RefreshToken (for JWT refresh)                                    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
        ┌───────────────────────────────────────────────────────┐
        │         External Services & Integrations              │
        ├───────────────────────────────────────────────────────┤
        │ • PostgreSQL (Primary Database)                        │
        │ • Pinecone (Vector Database for RAG)                  │
        │ • OpenAI (Embeddings & Whisper STT)                   │
        │ • OpenRouter (LLM - GPT-4o)                           │
        │ • ElevenLabs (Text-to-Speech)                         │
        │ • HeyGen (Avatar Video Generation)                    │
        │ • Mailgun (Email Service)                             │
        └───────────────────────────────────────────────────────┘
```

---

## 🔄 Complete User Flow

### 1. **Authentication Flow**

```
User → Login Page
  ↓
POST /api/v1/auth/login (email, password)
  ↓
Backend:
  • Hash password check against DB
  • Generate JWT access token (30 min expiry)
  • Generate refresh token (7 days expiry)
  • Store refresh token in DB
  ↓
Frontend:
  • Store tokens in localStorage
  • Set Authorization header for future requests
  • Redirect to Dashboard
  ↓
GET /api/v1/auth/me (with JWT)
  ↓
Backend:
  • Verify JWT signature
  • Return user data with role & dealership_id
  ↓
Frontend:
  • Update AuthContext with user data
  • Render role-based UI
```

**Token Refresh Flow:**
```
Request with expired token → 401 Unauthorized
  ↓
POST /api/v1/auth/refresh (with refresh_token)
  ↓
Backend:
  • Verify refresh token in DB
  • Generate new access token
  • Return new token
  ↓
Frontend:
  • Update localStorage
  • Retry original request with new token
```

---

### 2. **Text Chat Flow (Training & Role-play)**

```
User Types Message in Chat Panel
  ↓
Frontend:
  • Validate message (1-5000 chars)
  • Select mode: "training" or "roleplay"
  • Send to backend with session_id & conversation_history
  ↓
POST /api/v1/chat/ (with JWT)
  ↓
Backend:
  • Verify user authentication & authorization
  • Determine dealership_id (from user or super_admin param)
  • Check rate limit (CHAT_LIMIT)
  ↓
RAG Query (if dealership has RAG config):
  • Query Pinecone with user message
  • Retrieve top-5 relevant documents
  • Cache results (semantic + embedding cache)
  ↓
LLM Generation:
  • Build system prompt (Adam trainer or customer role-play)
  • Include RAG context + conversation history
  • Stream response from OpenRouter (GPT-4o)
  ↓
Response:
  • Return AI response + sources + session_id
  • Frontend displays response
  • Conversation history updated
```

**System Prompts:**
- **Training Mode:** "You are Adam Marburger, an expert F&I trainer..."
- **Role-play Mode:** "You are a realistic customer at an automotive dealership..."

---

### 3. **Voice Chat Flow (Real-time)**

```
User Clicks "Start Voice Chat"
  ↓
Frontend:
  • Request microphone permission
  • Establish WebSocket connection to /api/v1/voice/live
  ↓
WebSocket Connection Established
  ↓
User Speaks
  ↓
Frontend:
  • Capture audio (WebM format)
  • Buffer audio chunks
  • Send to backend when user stops speaking
  ↓
Backend (RealtimeVoiceService):
  • Receive audio bytes
  • STT: OpenAI Whisper transcription
  • Get user transcript
  ↓
LLM Generation:
  • Build prompt with transcript
  • Stream response from OpenRouter
  • Collect full response text
  ↓
TTS: ElevenLabs
  • Convert response text to speech
  • Stream audio chunks via WebSocket
  ↓
Frontend:
  • Receive audio chunks
  • Play audio in real-time
  • Display transcript & response
  • Update conversation history
  ↓
Loop: User can speak again
```

**Latency Optimization:**
- Streaming LLM responses (tokens as generated)
- Streaming TTS audio (plays while generating)
- Minimal conversation history (last 4-5 messages)
- Short max_tokens (60) for voice responses

---

### 4. **RAG (Retrieval-Augmented Generation) Flow**

```
Admin Uploads Documents
  ↓
POST /api/v1/rag/upload
  ↓
Backend:
  • Validate file (PDF, DOCX, TXT)
  • Extract text content
  • Split into chunks (1000 chars, 200 overlap)
  • Generate embeddings (OpenAI text-embedding-3-small)
  • Store in Pinecone with dealership namespace
  • Store metadata in PostgreSQL
  ↓
Document Stored in Vector DB
  ↓
When User Asks Question:
  ↓
Query Pinecone:
  • Embed user query
  • Semantic search in dealership namespace
  • Retrieve top-5 most relevant chunks
  • Multi-level caching:
    1. Session context cache (pre-warmed)
    2. Semantic cache (similar queries)
    3. Embedding cache (same query)
    4. Pinecone query (cache miss)
  ↓
Include Context in LLM Prompt:
  • Grounded responses based on actual content
  • Cite sources
  ↓
Return Response + Sources
```

**Namespace Strategy:**
- Each dealership has isolated namespace: `dealership_{id}`
- Prevents data leakage between dealerships
- Allows per-dealership knowledge bases

---

### 5. **Avatar Integration Flow (HeyGen)**

```
User Starts Avatar Chat
  ↓
Frontend:
  • Request avatar session token
  ↓
POST /api/v1/avatar/session
  ↓
Backend (AvatarService):
  • Call HeyGen API
  • Create session with avatar_id
  • Return session_token
  ↓
Frontend:
  • Initialize HeyGen SDK with token
  • Avatar appears on screen
  ↓
User Types Message
  ↓
Frontend:
  • Send text to HeyGen SDK
  • HeyGen handles TTS internally
  • Avatar speaks response
  ↓
Alternative: Voice Input
  ↓
Frontend:
  • Capture voice
  • Send to backend /api/v1/voice/live
  • Get text response
  • Send text to HeyGen
  • Avatar speaks
```

---

### 6. **Role-Based Access Control Flow**

```
User Logs In
  ↓
Backend:
  • Retrieve user role from DB
  • Include role in JWT token
  ↓
Frontend:
  • Store user role in AuthContext
  • Render role-specific UI
  ↓
Role Types:
  ├─ SUPER_ADMIN
  │  ├─ Access all dealerships
  │  ├─ Manage all users
  │  ├─ View system-wide analytics
  │  └─ Must specify dealership_id for chat/RAG
  │
  ├─ DEALERSHIP_ADMIN
  │  ├─ Access own dealership only
  │  ├─ Manage users in dealership
  │  ├─ Upload RAG documents
  │  └─ View dealership analytics
  │
  └─ USER
     ├─ Access own dealership only
     ├─ Use chat & voice features
     ├─ View own analytics
     └─ Cannot manage users/documents
  ↓
API Authorization:
  • Check user role
  • Verify dealership_id matches
  • Return 403 if unauthorized
```

---

## 🏗️ Architecture Components

### **Frontend Stack**
- **Framework:** React 18 + TypeScript
- **Routing:** React Router v6
- **HTTP Client:** Axios with interceptors
- **State Management:** React Context (Auth)
- **Styling:** Tailwind CSS
- **Build Tool:** Vite
- **WebSocket:** Native WebSocket API

### **Backend Stack**
- **Framework:** FastAPI (async)
- **Database:** PostgreSQL + pgvector
- **ORM:** SQLAlchemy (async)
- **Migrations:** Alembic
- **Authentication:** JWT (PyJWT)
- **Password Hashing:** Bcrypt
- **Rate Limiting:** SlowAPI
- **Validation:** Pydantic

### **AI/ML Services**
- **LLM:** OpenRouter (GPT-4o)
- **Embeddings:** OpenAI (text-embedding-3-small)
- **Vector DB:** Pinecone
- **RAG Framework:** LangChain
- **STT:** OpenAI Whisper
- **TTS:** ElevenLabs
- **Avatar:** HeyGen LiveAvatar

### **Infrastructure**
- **Containerization:** Docker + Docker Compose
- **Database:** PostgreSQL 16 with pgvector
- **Email:** Mailgun
- **Deployment:** Docker containers

---

## 🔐 Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Security Layers                          │
├─────────────────────────────────────────────────────────────┤
│ 1. CORS Middleware                                          │
│    • Whitelist specific origins                             │
│    • Allow credentials                                      │
│    • Restrict methods & headers                             │
│                                                              │
│ 2. Security Headers Middleware                              │
│    • X-Content-Type-Options: nosniff                        │
│    • X-Frame-Options: DENY                                  │
│    • X-XSS-Protection: 1; mode=block                        │
│                                                              │
│ 3. JWT Authentication                                       │
│    • Access token: 30 minutes                               │
│    • Refresh token: 7 days                                  │
│    • HS256 algorithm                                        │
│    • Stored in localStorage (frontend)                      │
│                                                              │
│ 4. Authorization                                            │
│    • Role-based access control (RBAC)                       │
│    • Dealership isolation                                   │
│    • Resource ownership verification                        │
│                                                              │
│ 5. Rate Limiting                                            │
│    • Chat: 30 requests/minute                               │
│    • Voice: 20 requests/minute                              │
│    • Per-user limits                                        │
│                                                              │
│ 6. Input Validation                                         │
│    • Pydantic schemas                                       │
│    • Message length limits                                  │
│    • File type validation                                   │
│                                                              │
│ 7. Database Security                                        │
│    • Parameterized queries (SQLAlchemy)                     │
│    • Connection pooling                                     │
│    • Async operations                                       │
│                                                              │
│ 8. API Key Management                                       │
│    • Environment variables                                  │
│    • No hardcoded secrets                                   │
│    • .env file (not in git)                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Data Flow Diagram

```
┌──────────────┐
│   Frontend   │
│   (React)    │
└──────┬───────┘
       │
       │ HTTP/WebSocket
       │ JWT Auth
       ↓
┌──────────────────────────────────────┐
│      FastAPI Backend                 │
│  ┌────────────────────────────────┐  │
│  │ Request Validation & Auth      │  │
│  └────────────────────────────────┘  │
│  ┌────────────────────────────────┐  │
│  │ Route Handler                  │  │
│  └────────────────────────────────┘  │
│  ┌────────────────────────────────┐  │
│  │ Business Logic (Services)      │  │
│  └────────────────────────────────┘  │
└──────┬───────────────────────────────┘
       │
       ├─────────────────────────────────────────┐
       │                                         │
       ↓                                         ↓
┌──────────────────┐                  ┌──────────────────┐
│  PostgreSQL      │                  │  External APIs   │
│  ┌────────────┐  │                  │  ┌────────────┐  │
│  │ Users      │  │                  │  │ OpenRouter │  │
│  │ Dealership │  │                  │  │ OpenAI     │  │
│  │ Documents  │  │                  │  │ ElevenLabs │  │
│  │ Tokens     │  │                  │  │ HeyGen     │  │
│  └────────────┘  │                  │  │ Mailgun    │  │
└──────────────────┘                  │  └────────────┘  │
       │                              └──────────────────┘
       │                                         │
       └─────────────────────────────────────────┤
                                                 │
                                                 ↓
                                        ┌──────────────────┐
                                        │  Pinecone        │
                                        │  (Vector DB)     │
                                        │  ┌────────────┐  │
                                        │  │ Embeddings │  │
                                        │  │ Documents  │  │
                                        │  └────────────┘  │
                                        └──────────────────┘
```

---

## 🚀 Request/Response Cycle

### **Typical Chat Request:**
```
1. Frontend sends POST /api/v1/chat/
   {
     "message": "How do I handle price objections?",
     "mode": "training",
     "session_id": "abc123",
     "conversation_history": [...]
   }

2. Backend processes:
   - Validate JWT token
   - Check rate limit
   - Query Pinecone for context
   - Generate response with LLM
   - Format response

3. Backend returns:
   {
     "response": "Great question! Price objections...",
     "session_id": "abc123",
     "sources": [
       {
         "document_id": "doc1",
         "title": "Objection Handling",
         "excerpt": "..."
       }
     ],
     "timestamp": "2024-02-05T10:30:00Z"
   }

4. Frontend:
   - Display response
   - Show sources
   - Update conversation history
   - Maintain session context
```

---

## 🔄 Caching Strategy

```
┌─────────────────────────────────────────────────────────────┐
│                    Multi-Level Caching                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Level 1: Session Context Cache                              │
│ ├─ Pre-warmed with conversation history                     │
│ ├─ Latency: ~5-20ms                                         │
│ └─ Scope: Current session                                   │
│                                                              │
│ Level 2: Semantic Cache                                     │
│ ├─ Similar queries return cached results                    │
│ ├─ Latency: ~10-50ms                                        │
│ └─ Scope: Dealership-wide                                   │
│                                                              │
│ Level 3: Embedding Cache                                    │
│ ├─ Same query embedding cached                              │
│ ├─ Saves embedding computation                              │
│ └─ Latency: Saves ~100-200ms                                │
│                                                              │
│ Level 4: Pinecone Query                                     │
│ ├─ Semantic search in vector DB                             │
│ ├─ Latency: ~200-400ms                                      │
│ └─ Scope: Full dealership knowledge base                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 📈 Scalability Considerations

### **Current Architecture Strengths:**
1. ✅ Async/await throughout (FastAPI)
2. ✅ Connection pooling (PostgreSQL)
3. ✅ Vector DB for semantic search (Pinecone)
4. ✅ Streaming responses (LLM & TTS)
5. ✅ Rate limiting (SlowAPI)
6. ✅ Caching layers (semantic + embedding)
7. ✅ Dealership isolation (namespaces)

### **Potential Bottlenecks:**
1. ⚠️ Single PostgreSQL instance
2. ⚠️ No request queuing for heavy operations
3. ⚠️ No distributed caching (Redis)
4. ⚠️ No async task queue (Celery/RQ)
5. ⚠️ No CDN for static assets
6. ⚠️ No load balancing

---

## 🎯 Key Features Implemented

| Feature | Status | Implementation |
|---------|--------|-----------------|
| User Authentication | ✅ | JWT with refresh tokens |
| Role-Based Access | ✅ | 3 roles (super_admin, dealership_admin, user) |
| Text Chat | ✅ | Training & role-play modes |
| Voice Chat | ✅ | WebSocket with Whisper STT + ElevenLabs TTS |
| RAG System | ✅ | Pinecone + LangChain with multi-level caching |
| Avatar Integration | ✅ | HeyGen LiveAvatar |
| Document Management | ✅ | Upload, chunk, embed, store |
| Rate Limiting | ✅ | Per-user limits |
| Error Handling | ✅ | Custom exceptions + middleware |
| CORS Security | ✅ | Whitelist origins |
| Email Service | ✅ | Mailgun integration |
| Inaccuracy Reporting | ✅ | Report endpoint |

---

## 📋 Environment Configuration

```
# Database
DATABASE_URL=postgresql+asyncpg://user:password@host:port/database

# Security
SECRET_KEY=<32-char-hex-key>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# LLM
OPENROUTER_API_KEY=<key>
OPENROUTER_MODEL=openai/gpt-4o

# Embeddings & STT
OPENAI_API_KEY=<key>
EMBEDDING_MODEL=text-embedding-3-small

# Vector DB
PINECONE_API_KEY=<key>
PINECONE_INDEX_NAME=avatar-adam

# Voice
ELEVENLABS_API_KEY=<key>
ELEVENLABS_VOICE_ID=<voice-id>

# Avatar
HEYGEN_API_KEY=<key>
HEYGEN_AVATAR_ID=<avatar-id>

# Email
MAILGUN_API_KEY=<key>
MAILGUN_DOMAIN=<domain>
```

---

## 🔍 Monitoring & Logging

```
Logging Points:
├─ Authentication (login, token refresh)
├─ Authorization (access denied)
├─ Chat requests (user, dealership, mode)
├─ RAG queries (query, results count)
├─ LLM calls (model, tokens)
├─ Voice processing (STT, TTS)
├─ Database operations (errors)
├─ External API calls (errors, latency)
└─ Rate limit violations

Metrics to Track:
├─ Request latency (by endpoint)
├─ Error rates (by type)
├─ Cache hit rates
├─ Token usage (LLM, embeddings)
├─ Active users
├─ Chat sessions
├─ Voice sessions
└─ Document uploads
```

---

