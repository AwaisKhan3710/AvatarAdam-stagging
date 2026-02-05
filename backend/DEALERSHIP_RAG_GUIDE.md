# Dealership RAG System Guide

## Overview

The Avatar Adam backend now supports multi-tenant dealerships with RAG (Retrieval-Augmented Generation) capabilities. Each dealership can have its own knowledge base for AI chat functionality.

## User Roles

### 1. Super Admin (`SUPER_ADMIN`)
- Create new dealerships
- Edit any dealership
- Delete dealerships
- View all dealerships
- Full system access

### 2. Dealership Admin (`DEALERSHIP_ADMIN`)
- Edit their own dealership
- Configure RAG settings for their dealership
- Manage users within their dealership
- View their dealership data

### 3. User (`USER`)
- Chat with AI using their dealership's RAG
- View their dealership information
- Access dealership-specific knowledge

## Database Schema

### Dealership Model
```python
{
    "id": 1,
    "name": "Premium Auto Group",
    "is_active": true,
    "address": "123 Main St",
    "contact_email": "contact@premiumauto.com",
    "contact_phone": "(555) 123-4567",
    "rag_config": {
        "vector_db_collection": "dealership_1_knowledge",
        "embedding_model": "text-embedding-3-small",
        "chunk_size": 1000,
        "chunk_overlap": 200,
        "metadata": {
            "dealership_id": 1,
            "dealership_name": "Premium Auto Group",
            "industry": "automotive"
        }
    },
    "created_at": "2025-12-11T...",
    "updated_at": "2025-12-11T..."
}
```

### User Model
```python
{
    "id": 1,
    "email": "admin@premiumauto.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "dealership_admin",
    "dealership_id": 1,  # Links user to dealership
    "is_active": true,
    "is_verified": false,
    "last_login": "2025-12-11T..."
}
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/signup` - Register new user
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/refresh` - Refresh access token
- `GET /api/v1/auth/me` - Get current user info

### Dealerships
- `POST /api/v1/dealerships/` - Create dealership (Super Admin only)
- `GET /api/v1/dealerships/` - List dealerships
- `GET /api/v1/dealerships/{id}` - Get dealership
- `PATCH /api/v1/dealerships/{id}` - Update dealership
- `PATCH /api/v1/dealerships/{id}/rag-config` - Update RAG config (Dealership Admin)
- `DELETE /api/v1/dealerships/{id}` - Delete dealership (Super Admin only)

## RAG Configuration

### Structure
The `rag_config` field stores all RAG-related metadata:

```json
{
  "vector_db_collection": "dealership_123_knowledge",
  "embedding_model": "text-embedding-3-small",
  "chunk_size": 1000,
  "chunk_overlap": 200,
  "metadata": {
    "dealership_id": 123,
    "dealership_name": "Premium Auto",
    "industry": "automotive",
    "custom_field": "value"
  }
}
```

### Usage in RAG System

When a user chats with AI:
1. Get user's `dealership_id` from JWT token
2. Fetch dealership's `rag_config`
3. Use `vector_db_collection` to query the correct knowledge base
4. Apply `metadata` filters to ensure dealership-specific results
5. Use `chunk_size` and `chunk_overlap` for document processing

### Example: Vector DB Query
```python
# Get dealership config
dealership = await get_dealership(user.dealership_id)
rag_config = dealership.rag_config

# Query vector DB with dealership-specific collection
results = vector_db.query(
    collection=rag_config["vector_db_collection"],
    query_text=user_question,
    filter_metadata={
        "dealership_id": dealership.id
    },
    top_k=5
)
```

## Workflow Examples

### 1. Super Admin Creates Dealership
```bash
POST /api/v1/dealerships/
{
  "name": "Elite Motors",
  "address": "456 Oak Ave",
  "contact_email": "info@elitemotors.com",
  "contact_phone": "(555) 987-6543"
}
```

### 2. Dealership Admin Configures RAG
```bash
PATCH /api/v1/dealerships/1/rag-config
{
  "vector_db_collection": "dealership_1_knowledge",
  "embedding_model": "text-embedding-3-small",
  "chunk_size": 1000,
  "chunk_overlap": 200,
  "metadata": {
    "dealership_id": 1,
    "dealership_name": "Elite Motors",
    "industry": "automotive",
    "location": "Los Angeles"
  }
}
```

### 3. User Signup with Dealership
```bash
POST /api/v1/auth/signup
{
  "email": "user@elitemotors.com",
  "password": "SecurePass123!",
  "first_name": "Jane",
  "last_name": "Smith",
  "role": "user",
  "dealership_id": 1
}
```

### 4. JWT Token Contains Dealership
```json
{
  "sub": "123",
  "email": "user@elitemotors.com",
  "role": "user",
  "dealership_id": 1,
  "exp": 1702345678
}
```

## Data Isolation

### Row-Level Security
- All queries automatically filter by `dealership_id`
- Users can only access data from their dealership
- Super Admins bypass dealership filtering

### RAG Isolation
- Each dealership has its own vector DB collection
- Metadata filters ensure cross-dealership data leakage prevention
- Collection naming: `dealership_{id}_knowledge`

## Migration Guide

### 1. Create Database Tables
```bash
uv run alembic revision --autogenerate -m "Add dealerships and RAG support"
uv run alembic upgrade head
```

### 2. Seed Initial Data
```bash
uv run python scripts/seed_db.py
```

This creates:
- Super Admin: `admin@avataradam.com` / `Admin123!@#`
- Test Dealership: "Premium Auto Group"
- Dealership Admin: `admin@premiumauto.com` / `Admin123!`
- Test User: `user@premiumauto.com` / `User123!`

## Security Considerations

1. **JWT Claims**: Dealership ID is embedded in JWT for fast access control
2. **Database Constraints**: Foreign key with CASCADE delete ensures data integrity
3. **Role Validation**: Endpoints check user role before allowing operations
4. **Metadata Validation**: RAG config is validated before storage

## Next Steps for RAG Integration

1. **Vector Database Setup**
   - Choose vector DB (Pinecone, Weaviate, Chroma, etc.)
   - Create collections per dealership
   - Store collection names in `rag_config`

2. **Document Processing**
   - Upload dealership-specific documents
   - Chunk using `chunk_size` and `chunk_overlap` from config
   - Embed using `embedding_model` from config
   - Store with `metadata` from config

3. **Chat Endpoint**
   - Create `/api/v1/chat` endpoint
   - Extract `dealership_id` from JWT
   - Query appropriate vector DB collection
   - Apply metadata filters
   - Generate response with LLM

4. **Admin Interface**
   - Document upload UI for dealership admins
   - RAG config management UI
   - Knowledge base statistics

## Example RAG Chat Flow

```python
@router.post("/chat")
async def chat(
    message: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # Get user's dealership
    dealership = await get_dealership(db, current_user.dealership_id)
    
    # Get RAG config
    rag_config = dealership.rag_config
    collection = rag_config["vector_db_collection"]
    
    # Query vector DB
    context = await vector_db.query(
        collection=collection,
        query=message,
        filter={"dealership_id": dealership.id},
        top_k=5
    )
    
    # Generate response
    response = await llm.generate(
        prompt=f"Context: {context}\\n\\nQuestion: {message}",
        metadata=rag_config["metadata"]
    )
    
    return {"response": response}
```
