# AvatarAdam - Quick Reference Guide

## 🎯 System Overview

**AvatarAdam** is an AI-powered F&I training platform that uses:
- **Frontend:** React + TypeScript (Vite)
- **Backend:** FastAPI (Python async)
- **Database:** PostgreSQL + Pinecone (vector DB)
- **AI Services:** OpenRouter (LLM), OpenAI (embeddings), ElevenLabs (TTS), HeyGen (avatar)

---

## 📊 Architecture at a Glance

```
User → Frontend (React) → Backend (FastAPI) → Services → External APIs
                              ↓
                         PostgreSQL + Pinecone
```

---

## 🔑 Key Components

### **Frontend**
- **Location:** `frontend/src/`
- **Pages:** Login, Dashboard, Chat, VoiceChat, RagManagement, etc.
- **State:** AuthContext (JWT tokens, user data)
- **API Client:** Axios with interceptors

### **Backend**
- **Location:** `backend/app/`
- **API Routes:** `/api/v1/{auth,chat,voice,rag,avatar,users,dealerships}`
- **Services:** LLMService, RAGService, VoiceService, AvatarService
- **Database:** SQLAlchemy ORM with async support

### **External Services**
| Service | Purpose | Config |
|---------|---------|--------|
| OpenRouter | LLM (GPT-4o) | `OPENROUTER_API_KEY` |
| OpenAI | Embeddings & STT | `OPENAI_API_KEY` |
| Pinecone | Vector DB | `PINECONE_API_KEY` |
| ElevenLabs | Text-to-Speech | `ELEVENLABS_API_KEY` |
| HeyGen | Avatar Video | `HEYGEN_API_KEY` |
| Mailgun | Email | `MAILGUN_API_KEY` |

---

## 🔐 Authentication Flow

```
1. User logs in → POST /auth/login
2. Backend generates JWT (30 min) + Refresh token (7 days)
3. Frontend stores tokens in localStorage
4. All requests include: Authorization: Bearer <token>
5. On 401 → POST /auth/refresh to get new token
```

**Token Structure:**
- **Access Token:** Short-lived (30 min), includes user ID & role
- **Refresh Token:** Long-lived (7 days), stored in DB

---

## 💬 Chat Flow

### **Text Chat**
```
User message → Frontend → POST /api/v1/chat/
                            ↓
                    Backend processes:
                    1. Verify JWT
                    2. Query RAG (Pinecone)
                    3. Generate response (LLM)
                    4. Return response + sources
                            ↓
                    Frontend displays response
```

**Modes:**
- **Training:** AI acts as Adam (trainer)
- **Role-play:** AI acts as customer

### **Voice Chat**
```
User speaks → Frontend captures audio → WebSocket /api/v1/voice/live
                                            ↓
                                    Backend processes:
                                    1. STT (Whisper)
                                    2. LLM response
                                    3. TTS (ElevenLabs)
                                    4. Stream audio back
                                            ↓
                                    Frontend plays audio
```

---

## 📚 RAG (Retrieval-Augmented Generation)

### **Document Upload**
```
Admin uploads file → Backend:
  1. Extract text
  2. Split into chunks (1000 chars, 200 overlap)
  3. Generate embeddings (OpenAI)
  4. Store in Pinecone (dealership namespace)
  5. Store metadata in PostgreSQL
```

### **Query Process**
```
User asks question → Backend:
  1. Embed query (OpenAI)
  2. Search Pinecone (dealership namespace)
  3. Get top-5 results
  4. Include in LLM prompt
  5. Return response + sources
```

**Caching Levels:**
1. Session context (pre-warmed)
2. Semantic cache (similar queries)
3. Embedding cache (same query)
4. Pinecone query (cache miss)

---

## 👥 User Roles & Permissions

| Role | Access | Permissions |
|------|--------|-------------|
| **super_admin** | All dealerships | Manage all users, view all data, upload RAG docs |
| **dealership_admin** | Own dealership | Manage dealership users, upload RAG docs |
| **user** | Own dealership | Use chat/voice, view own analytics |

**Authorization Check:**
```python
# Super admin must specify dealership_id
# Regular users use their assigned dealership
# Cross-dealership access returns 403
```

---

## 🚀 API Endpoints Summary

### **Authentication**
```
POST   /api/v1/auth/login          - Login
POST   /api/v1/auth/signup         - Register
POST   /api/v1/auth/refresh        - Refresh token
POST   /api/v1/auth/logout         - Logout
GET    /api/v1/auth/me             - Get current user
```

### **Chat**
```
POST   /api/v1/chat/               - Send message (training/roleplay)
```

### **Voice**
```
WebSocket /api/v1/voice/live       - Real-time voice chat
```

### **RAG**
```
POST   /api/v1/rag/upload          - Upload document
GET    /api/v1/rag/documents       - List documents
DELETE /api/v1/rag/documents/{id}  - Delete document
POST   /api/v1/rag/query           - Query knowledge base
```

### **Avatar**
```
POST   /api/v1/avatar/session      - Create avatar session
GET    /api/v1/avatar/voices       - List available voices
```

### **Users**
```
GET    /api/v1/users/              - List users (admin)
POST   /api/v1/users/              - Create user (admin)
GET    /api/v1/users/{id}          - Get user
PUT    /api/v1/users/{id}          - Update user
DELETE /api/v1/users/{id}          - Delete user (admin)
```

### **Dealerships**
```
GET    /api/v1/dealerships/        - List dealerships (admin)
POST   /api/v1/dealerships/        - Create dealership (admin)
GET    /api/v1/dealerships/{id}    - Get dealership
PUT    /api/v1/dealerships/{id}    - Update dealership (admin)
```

---

## 🔧 Configuration

### **Environment Variables**

**Database:**
```
DATABASE_URL=postgresql+asyncpg://user:password@host:port/database
```

**Security:**
```
SECRET_KEY=<32-char-hex>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

**LLM & AI:**
```
OPENROUTER_API_KEY=<key>
OPENROUTER_MODEL=openai/gpt-4o
OPENAI_API_KEY=<key>
EMBEDDING_MODEL=text-embedding-3-small
ELEVENLABS_API_KEY=<key>
ELEVENLABS_VOICE_ID=<voice-id>
PINECONE_API_KEY=<key>
PINECONE_INDEX_NAME=avatar-adam
HEYGEN_API_KEY=<key>
HEYGEN_AVATAR_ID=<avatar-id>
```

**Email:**
```
MAILGUN_API_KEY=<key>
MAILGUN_DOMAIN=<domain>
MAILGUN_FROM_EMAIL=<email>
```

---

## 📊 Database Schema

### **Key Tables**

**users**
```
id, email, hashed_password, first_name, last_name, role, 
is_active, is_verified, dealership_id, created_at, updated_at, last_login
```

**dealerships**
```
id, name, rag_config (JSON), created_at, updated_at
```

**documents**
```
id, dealership_id, title, content_hash, file_type, 
chunk_count, created_at, updated_at
```

**document_chunks**
```
id, document_id, chunk_index, content, embedding (pgvector), 
created_at
```

**refresh_tokens**
```
id, user_id, token_hash, expires_at, created_at
```

---

## 🔄 Request/Response Examples

### **Login Request**
```json
POST /api/v1/auth/login
{
  "email": "user@example.com",
  "password": "password123"
}

Response:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

### **Chat Request**
```json
POST /api/v1/chat/
Authorization: Bearer <token>
{
  "message": "How do I handle price objections?",
  "mode": "training",
  "session_id": "abc123",
  "conversation_history": [...]
}

Response:
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
```

### **Voice Chat WebSocket**
```
Connect: ws://localhost:8000/api/v1/voice/live?token=<jwt>

Send: { "type": "audio", "data": "<base64-audio>" }

Receive:
{ "type": "transcript", "text": "user said this" }
{ "type": "audio_chunk", "data": "<base64-audio>" }
{ "type": "response_complete", "text": "full response" }
```

---

## 🐛 Common Issues & Solutions

### **Issue: 401 Unauthorized**
**Cause:** Missing or expired JWT token
**Solution:** 
- Check token in localStorage
- Refresh token if expired
- Re-login if refresh fails

### **Issue: 403 Forbidden**
**Cause:** User doesn't have permission
**Solution:**
- Check user role
- Verify dealership_id matches
- Contact admin for permission upgrade

### **Issue: 429 Too Many Requests**
**Cause:** Rate limit exceeded
**Solution:**
- Wait before retrying
- Check rate limit headers
- Implement exponential backoff

### **Issue: Voice chat not working**
**Cause:** Microphone permission denied or WebSocket connection failed
**Solution:**
- Check browser microphone permissions
- Verify WebSocket URL
- Check network connectivity
- Verify ElevenLabs API key

### **Issue: RAG not returning results**
**Cause:** No documents uploaded or query doesn't match content
**Solution:**
- Upload documents first
- Check document processing status
- Try different query terms
- Verify Pinecone connection

---

## 📈 Performance Tips

### **Frontend**
- Use React DevTools Profiler to find slow components
- Implement code splitting for large pages
- Cache API responses when appropriate
- Use lazy loading for images

### **Backend**
- Monitor database query performance
- Use database indexes on frequently queried columns
- Implement caching for expensive operations
- Use connection pooling

### **RAG**
- Optimize chunk size (1000 chars is good)
- Use semantic caching for similar queries
- Monitor Pinecone query latency
- Batch document uploads

---

## 🚀 Deployment Checklist

- [ ] Set all environment variables
- [ ] Run database migrations: `alembic upgrade head`
- [ ] Test authentication flow
- [ ] Test chat endpoints
- [ ] Test voice endpoints
- [ ] Test RAG upload & query
- [ ] Verify rate limiting
- [ ] Check CORS configuration
- [ ] Enable HTTPS in production
- [ ] Set up monitoring & logging
- [ ] Configure backups
- [ ] Test failover procedures

---

## 📞 Support & Debugging

### **Enable Debug Logging**
```python
# backend/app/core/config.py
DEBUG = True
DB_ECHO = True  # Log all SQL queries
```

### **Check Logs**
```bash
# Docker logs
docker logs avatarAdam-backend

# Application logs
tail -f backend/logs/app.log
```

### **Test Endpoints**
```bash
# Using curl
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}'

# Using Swagger UI
http://localhost:8000/docs
```

---

## 📚 Additional Resources

- **API Documentation:** `http://localhost:8000/docs` (Swagger UI)
- **Architecture Details:** See `ARCHITECTURE_FLOW.md`
- **Improvements Guide:** See `ARCHITECTURE_IMPROVEMENTS.md`
- **Setup Instructions:** See `README_SETUP.md`

---

## 🎯 Key Metrics to Monitor

| Metric | Target | Tool |
|--------|--------|------|
| API Response Time | < 500ms | Prometheus |
| Chat Latency | < 2s | Prometheus |
| Voice Latency | < 1s | Prometheus |
| Cache Hit Rate | > 70% | Prometheus |
| Error Rate | < 0.1% | Prometheus |
| Uptime | > 99.9% | Grafana |
| Database Connections | < 80% | Grafana |

---

## 🔐 Security Checklist

- [ ] JWT tokens have short expiry (30 min)
- [ ] Refresh tokens stored securely in DB
- [ ] CORS whitelist configured
- [ ] Rate limiting enabled
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (SQLAlchemy)
- [ ] HTTPS enabled in production
- [ ] API keys in environment variables
- [ ] Audit logging enabled
- [ ] Regular security updates

---

## 📝 Common Commands

```bash
# Start development environment
docker-compose up

# Run migrations
docker exec avatarAdam-backend uv run alembic upgrade head

# Create new migration
docker exec avatarAdam-backend uv run alembic revision --autogenerate -m "description"

# Run tests
docker exec avatarAdam-backend uv run pytest

# View logs
docker logs -f avatarAdam-backend

# Access database
docker exec -it avatarAdam-db psql -U postgres -d avatar_adam

# Rebuild containers
docker-compose build --no-cache

# Clean up
docker-compose down -v
```

---

## 🎓 Learning Path

1. **Understand the Flow:** Read `ARCHITECTURE_FLOW.md`
2. **Review Code Structure:** Explore `backend/app/` and `frontend/src/`
3. **Study Key Services:** RAGService, LLMService, VoiceService
4. **Test Endpoints:** Use Swagger UI at `/docs`
5. **Review Improvements:** Read `ARCHITECTURE_IMPROVEMENTS.md`
6. **Implement Enhancements:** Start with Tier 1 improvements

---

