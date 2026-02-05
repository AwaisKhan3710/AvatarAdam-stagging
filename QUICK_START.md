# Avatar Adam - Quick Start Guide

## 🚀 Getting Started

### Prerequisites
- Python 3.12+ (Already installed: 3.14.2)
- Virtual environment (Already created: `.venv/`)
- All dependencies (Already installed)

### Step 1: Activate Virtual Environment
```powershell
cd AvatarAdam-stagging
.venv/Scripts/Activate.ps1
```

### Step 2: Start the Backend Server
```powershell
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

### Step 3: Access the API
- **API Documentation:** http://127.0.0.1:8000/docs
- **Alternative Docs:** http://127.0.0.1:8000/redoc
- **API Base URL:** http://127.0.0.1:8000/api/v1

### Step 4: Test Login
Use these credentials in the Swagger UI:
```
Email: admin@avataradam.com
Password: Admin123!@#
```

---

## 📋 Available Commands

### Run Tests
```powershell
# Validate project setup
python test_simple.py

# Test API endpoints (requires server running)
python test_api.py
```

### Database Migrations
```powershell
# Apply migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "Description"

# Rollback
alembic downgrade -1
```

### Seed Database
```powershell
python scripts/seed_db.py
```

---

## 🔑 Test Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@avataradam.com | Admin123!@# |
| Principal | principal@premiumauto.com | Principal123! |
| Manager | manager@premiumauto.com | Manager123! |

---

## 📚 API Endpoints

### Authentication
```
POST   /api/v1/auth/signup          - Register new user
POST   /api/v1/auth/login           - Login user
POST   /api/v1/auth/refresh         - Refresh token
GET    /api/v1/auth/me              - Get current user
```

### Users
```
GET    /api/v1/users/               - List users
POST   /api/v1/users/               - Create user
GET    /api/v1/users/{id}           - Get user
PATCH  /api/v1/users/{id}           - Update user
DELETE /api/v1/users/{id}           - Delete user
```

### Dealerships
```
GET    /api/v1/dealerships/         - List dealerships
POST   /api/v1/dealerships/         - Create dealership
GET    /api/v1/dealerships/{id}     - Get dealership
PATCH  /api/v1/dealerships/{id}     - Update dealership
DELETE /api/v1/dealerships/{id}     - Delete dealership
```

### Chat & Voice
```
GET    /api/v1/chat/                - Chat endpoints
GET    /api/v1/voice/               - Voice endpoints
GET    /api/v1/voice/live           - Live voice streaming
```

### RAG & Avatar
```
GET    /api/v1/rag/                 - RAG endpoints
GET    /api/v1/avatar/              - Avatar endpoints
GET    /api/v1/report/              - Report endpoints
```

---

## 🗂️ Project Structure

```
backend/
├── app/
│   ├── api/v1/              - API endpoints
│   ├── core/                - Configuration
│   ├── models/              - Database models
│   ├── schemas/             - Data validation
│   ├── services/            - Business logic
│   ├── middleware/          - Custom middleware
│   └── main.py              - FastAPI app
├── alembic/                 - Database migrations
├── scripts/                 - Utility scripts
├── .env                     - Environment variables
├── pyproject.toml           - Dependencies
└── test_*.py                - Test files
```

---

## 🔧 Configuration

### Environment Variables (.env)
```
DATABASE_URL=postgresql+asyncpg://...
SECRET_KEY=bd1d1f34c59b030cc130a474fc148beac2a8695fde1e4ce1186cacc1d0dfc96a
DEBUG=true
PROJECT_NAME=Avatar Adam
```

### Database
- **Type:** PostgreSQL 16
- **Host:** dpg-d4ul5qemcj7s73d6s8vg-a.oregon-postgres.render.com
- **Database:** avtaradam_stagging_db

### External Services
- **OpenRouter:** GPT-4o LLM
- **OpenAI:** Embeddings & Whisper STT
- **Pinecone:** Vector database
- **ElevenLabs:** Text-to-speech
- **HeyGen:** Avatar generation
- **Mailgun:** Email delivery

---

## 🧪 Testing

### Run All Tests
```powershell
python test_simple.py
```

### Expected Output
```
✓ PASS - Package Imports
✓ PASS - Environment File
✓ PASS - Project Structure
✓ PASS - Database Config
✓ PASS - API Import
✓ PASS - Database Models
✓ PASS - Pydantic Schemas
✓ PASS - Services
✓ PASS - Security
✓ PASS - API Endpoints (when server running)

Success Rate: 90-100%
```

---

## 🐛 Troubleshooting

### Server Won't Start
1. Check if port 8000 is in use: `netstat -ano | findstr :8000`
2. Kill process if needed: `taskkill /PID <PID> /F`
3. Verify database connection in `.env`

### Database Connection Error
1. Check internet connection to Render.com
2. Verify credentials in `.env`
3. Ensure database exists

### Import Errors
1. Activate virtual environment: `.venv/Scripts/Activate.ps1`
2. Reinstall packages: `pip install -r requirements.txt`
3. Check Python version: `python --version`

### Authentication Fails
1. Verify user exists in database
2. Check password is correct
3. Ensure SECRET_KEY is set in `.env`

---

## 📖 Documentation

- **API Docs:** http://127.0.0.1:8000/docs
- **README:** `backend/README.md`
- **RAG Guide:** `backend/DEALERSHIP_RAG_GUIDE.md`
- **Test Results:** `PROJECT_TEST_RESULTS.md`
- **Setup Guide:** `TESTING_COMPLETE.md`

---

## 🚀 Next Steps

1. **Start the server** - See Step 2 above
2. **Test the API** - Use Swagger UI at `/docs`
3. **Review documentation** - Check the README files
4. **Develop features** - Start building on the API
5. **Deploy** - Use Docker or cloud platform

---

## 📞 Support

For issues or questions:
1. Check the documentation files
2. Review API docs at `/docs`
3. Check server logs for errors
4. Verify environment variables

---

## ✅ Verification Checklist

- [x] Virtual environment created
- [x] Dependencies installed
- [x] Environment configured
- [x] Database connected
- [x] API routes available
- [x] Tests passing (90%)
- [x] Ready for development

**Status: ✅ READY TO USE**

---

**Last Updated:** February 5, 2026
