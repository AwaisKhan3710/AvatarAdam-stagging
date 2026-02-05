# Avatar Adam Backend

Production-ready FastAPI backend with JWT authentication, PostgreSQL, and Alembic migrations.

## Features

- ✅ **JWT Authentication** - Stateless authentication with access and refresh tokens
- ✅ **Role-Based Access Control** - System Admin, Dealer Principal, F&I Manager roles
- ✅ **Multi-Tenant Architecture** - Row-level dealership isolation
- ✅ **PostgreSQL Database** - Async SQLAlchemy with connection pooling
- ✅ **Database Migrations** - Alembic for schema versioning
- ✅ **Production-Ready Error Handling** - Custom exceptions and global handlers
- ✅ **Clean Architecture** - Separation of concerns with CRUD, schemas, and models
- ✅ **API Documentation** - Auto-generated OpenAPI/Swagger docs
- ✅ **Type Safety** - Full type hints with Pydantic validation

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── deps.py              # Dependency injection
│   │   └── v1/
│   │       ├── auth.py          # Authentication endpoints
│   │       └── users.py         # User management endpoints
│   ├── core/
│   │   ├── config.py            # Settings and configuration
│   │   ├── database.py          # Database connection
│   │   ├── exceptions.py        # Custom exceptions
│   │   └── security.py          # JWT and password utilities
│   ├── crud/
│   │   ├── base.py              # Base CRUD operations
│   │   ├── crud_user.py         # User CRUD
│   │   ├── crud_dealership.py   # Dealership CRUD
│   │   └── crud_refresh_token.py # Token CRUD
│   ├── models/
│   │   ├── user.py              # User model
│   │   ├── dealership.py        # Dealership model
│   │   └── refresh_token.py     # Refresh token model
│   ├── schemas/
│   │   ├── auth.py              # Auth request/response schemas
│   │   ├── user.py              # User schemas
│   │   ├── dealership.py        # Dealership schemas
│   │   └── common.py            # Common schemas
│   └── main.py                  # FastAPI application
├── alembic/                     # Database migrations
├── scripts/
│   └── seed_db.py               # Database seeding script
├── .env                         # Environment variables
├── .env.example                 # Example environment file
├── alembic.ini                  # Alembic configuration
├── pyproject.toml               # Dependencies
└── Dockerfile                   # Docker configuration
```

## Prerequisites

- Python 3.12+
- PostgreSQL 14+
- uv (Python package manager)

## Setup

### 1. Install Dependencies

```powershell
# Install uv if not already installed
pip install uv

# Install project dependencies
uv sync
```

### 2. Configure Environment

Copy `.env.example` to `.env` and update the values:

```powershell
cp .env.example .env
```

**Important:** Generate a secure SECRET_KEY:

```powershell
# On Windows with OpenSSL installed
openssl rand -hex 32

# Or use Python
python -c "import secrets; print(secrets.token_hex(32))"
```

Update `.env` with your database credentials and the generated SECRET_KEY.

### 3. Setup PostgreSQL Database

```powershell
# Create database (using psql or pgAdmin)
createdb avatar_adam

# Or using psql
psql -U postgres -c "CREATE DATABASE avatar_adam;"
```

### 4. Run Database Migrations

```powershell
# Generate initial migration
uv run alembic revision --autogenerate -m "Initial migration"

# Apply migrations
uv run alembic upgrade head
```

### 5. Seed Database (Optional)

```powershell
# Seed with test data
uv run python scripts/seed_db.py
```

This creates:
- System Admin: `admin@avataradam.com` / `Admin123!@#`
- Dealer Principal: `principal@premiumauto.com` / `Principal123!`
- F&I Manager: `manager@premiumauto.com` / `Manager123!`

**⚠️ Change these passwords in production!**

### 6. Run Development Server

```powershell
# Run with auto-reload
uv run fastapi dev

# Or specify host and port
uv run fastapi dev --host 0.0.0.0 --port 9000
```

The API will be available at:
- API: http://localhost:8000
- Docs: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

## API Endpoints

### Authentication

- `POST /api/v1/auth/login` - Login with email/password
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/logout` - Logout (revoke refresh token)
- `POST /api/v1/auth/logout-all` - Logout from all sessions
- `GET /api/v1/auth/me` - Get current user info

### Users

- `GET /api/v1/users/` - List users (filtered by role)
- `POST /api/v1/users/` - Create user (admin/principal only)
- `GET /api/v1/users/{id}` - Get user by ID
- `PATCH /api/v1/users/{id}` - Update user
- `DELETE /api/v1/users/{id}` - Delete user (admin only)

## User Roles

### System Admin
- Full access to all dealerships and users
- Can create, update, delete any user
- Can manage all dealerships

### Dealer Principal
- Access to their own dealership only
- Can view and manage users in their dealership
- Can view dealership-wide analytics

### F&I Manager
- Access to their own data only
- Can view their own profile and analytics
- Can access training and role-play features

## Authentication Flow

### Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "manager@premiumauto.com",
    "password": "Manager123!"
  }'
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Authenticated Request
```bash
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Refresh Token
```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "YOUR_REFRESH_TOKEN"
  }'
```

## Database Migrations

```powershell
# Create a new migration
uv run alembic revision --autogenerate -m "Description of changes"

# Apply migrations
uv run alembic upgrade head

# Rollback one migration
uv run alembic downgrade -1

# View migration history
uv run alembic history

# View current revision
uv run alembic current
```

## Development

### Run Tests
```powershell
# Install dev dependencies
uv sync --dev

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=app
```

### Code Quality
```powershell
# Format code
uv run black app/

# Lint code
uv run ruff check app/

# Type checking
uv run mypy app/
```

## Production Deployment

### Environment Variables

Ensure these are set in production:
- `DEBUG=False`
- Strong `SECRET_KEY` (never use the example key)
- Secure database credentials
- Appropriate `BACKEND_CORS_ORIGINS`

### Run with Uvicorn

```powershell
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker

```powershell
# Build image
docker build -t avatar-adam-backend .

# Run container
docker run -p 8000:8000 --env-file .env avatar-adam-backend
```

## Security Considerations

1. **JWT Tokens**
   - Access tokens expire in 30 minutes
   - Refresh tokens expire in 7 days
   - Refresh tokens are stored in database for revocation

2. **Password Security**
   - Passwords hashed with bcrypt (12 rounds)
   - Minimum 8 characters required
   - Never logged or exposed in responses

3. **Multi-Tenancy**
   - Row-level isolation by dealership_id
   - Enforced at dependency injection level
   - System admins can bypass for management

4. **CORS**
   - Configured for specific origins only
   - Credentials allowed for authenticated requests

## Troubleshooting

### Database Connection Issues
```powershell
# Test database connection
uv run python -c "from app.core.database import engine; import asyncio; asyncio.run(engine.connect())"
```

### Migration Issues
```powershell
# Reset database (⚠️ destroys all data)
uv run alembic downgrade base
uv run alembic upgrade head
```

### Import Errors
```powershell
# Ensure you're in the backend directory
cd backend

# Reinstall dependencies
uv sync --reinstall
```

## License

Proprietary - Avatar Adam Platform

## Support

For issues or questions, contact the development team.
