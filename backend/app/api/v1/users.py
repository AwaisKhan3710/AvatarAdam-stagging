"""User management endpoints - Super Admin only."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.core.exceptions import AuthorizationError, NotFoundError, ConflictError
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter()


async def require_super_admin(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """
    Require super admin role for access.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User: Current user if super admin
        
    Raises:
        AuthorizationError: If user is not a super admin
    """
    if current_user.role != UserRole.SUPER_ADMIN:
        raise AuthorizationError("Only super admins can access this resource")
    return current_user


@router.get("/", response_model=list[UserResponse])
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_super_admin)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    role: UserRole | None = None,
    is_active: bool | None = None,
    dealership_id: int | None = None,
) -> list[User]:
    """
    List all users (Super Admin only).
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        role: Filter by user role
        is_active: Filter by active status
        dealership_id: Filter by dealership
        
    Returns:
        List of users
    """
    query = select(User).order_by(User.created_at.desc())
    
    if role is not None:
        query = query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    if dealership_id is not None:
        query = query.where(User.dealership_id == dealership_id)
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/count")
async def get_users_count(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_super_admin)],
    role: UserRole | None = None,
    is_active: bool | None = None,
    dealership_id: int | None = None,
) -> dict:
    """
    Get total count of users (Super Admin only).
    
    Args:
        db: Database session
        role: Filter by user role
        is_active: Filter by active status
        dealership_id: Filter by dealership
        
    Returns:
        Total count of users
    """
    query = select(func.count(User.id))
    
    if role is not None:
        query = query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    if dealership_id is not None:
        query = query.where(User.dealership_id == dealership_id)
    
    result = await db.execute(query)
    count = result.scalar()
    return {"count": count}


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_super_admin)],
) -> User:
    """
    Get a specific user by ID (Super Admin only).
    
    Args:
        user_id: User ID
        db: Database session
        
    Returns:
        User details
        
    Raises:
        NotFoundError: If user not found
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise NotFoundError(f"User with ID {user_id} not found")
    
    return user


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_super_admin)],
) -> User:
    """
    Create a new user (Super Admin only).
    
    Args:
        user_data: User creation data
        db: Database session
        
    Returns:
        Created user
        
    Raises:
        ConflictError: If user with email already exists
    """
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise ConflictError(f"User with email {user_data.email} already exists")
    
    # Create new user
    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        role=user_data.role,
        dealership_id=user_data.dealership_id,
        is_active=True,
        is_verified=True,  # Admin-created users are pre-verified
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_super_admin)],
) -> User:
    """
    Update a user (Super Admin only).
    
    Args:
        user_id: User ID to update
        user_data: User update data
        db: Database session
        current_user: Current super admin user
        
    Returns:
        Updated user
        
    Raises:
        NotFoundError: If user not found
        ConflictError: If email already exists
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise NotFoundError(f"User with ID {user_id} not found")
    
    # Check email uniqueness if being updated
    if user_data.email and user_data.email != user.email:
        result = await db.execute(select(User).where(User.email == user_data.email))
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise ConflictError(f"User with email {user_data.email} already exists")
    
    # Update fields
    update_data = user_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    await db.commit()
    await db.refresh(user)
    
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_super_admin)],
) -> None:
    """
    Delete a user (Super Admin only).
    
    Args:
        user_id: User ID to delete
        db: Database session
        current_user: Current super admin user
        
    Raises:
        NotFoundError: If user not found
        AuthorizationError: If trying to delete self
    """
    if user_id == current_user.id:
        raise AuthorizationError("Cannot delete your own account")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise NotFoundError(f"User with ID {user_id} not found")
    
    await db.delete(user)
    await db.commit()


@router.patch("/{user_id}/toggle-active", response_model=UserResponse)
async def toggle_user_active(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_super_admin)],
) -> User:
    """
    Toggle user active status (Super Admin only).
    
    Args:
        user_id: User ID
        db: Database session
        current_user: Current super admin user
        
    Returns:
        Updated user
        
    Raises:
        NotFoundError: If user not found
        AuthorizationError: If trying to deactivate self
    """
    if user_id == current_user.id:
        raise AuthorizationError("Cannot deactivate your own account")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise NotFoundError(f"User with ID {user_id} not found")
    
    user.is_active = not user.is_active
    await db.commit()
    await db.refresh(user)
    
    return user
