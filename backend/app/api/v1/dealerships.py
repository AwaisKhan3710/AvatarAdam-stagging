"""Dealership management endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.models.dealership import Dealership
from app.models.user import User, UserRole
from app.schemas.dealership import (
    DealershipCreate,
    DealershipResponse,
    DealershipUpdate,
    RAGConfigUpdate,
)

router = APIRouter()


@router.post("/", response_model=DealershipResponse, status_code=status.HTTP_201_CREATED)
async def create_dealership(
    dealership_data: DealershipCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> DealershipResponse:
    """
    Create a new dealership (Super Admin only).
    
    Args:
        dealership_data: Dealership creation data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Created dealership
        
    Raises:
        AuthorizationError: If user is not super admin
        ConflictError: If dealership name already exists
    """
    # Only super admins can create dealerships
    if current_user.role != UserRole.SUPER_ADMIN:
        raise AuthorizationError("Only super admins can create dealerships")
    
    # Check if dealership with same name exists
    result = await db.execute(
        select(Dealership).where(Dealership.name == dealership_data.name)
    )
    if result.scalar_one_or_none():
        raise ConflictError(f"Dealership with name '{dealership_data.name}' already exists")
    
    # Create dealership
    dealership = Dealership(
        name=dealership_data.name,
        address=dealership_data.address,
        contact_email=dealership_data.contact_email,
        contact_phone=dealership_data.contact_phone,
    )
    db.add(dealership)
    await db.commit()
    await db.refresh(dealership)
    
    return DealershipResponse.model_validate(dealership)


@router.get("/", response_model=list[DealershipResponse], status_code=status.HTTP_200_OK)
async def list_dealerships(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    skip: int = 0,
    limit: int = 100,
) -> list[DealershipResponse]:
    """
    List dealerships.
    
    Super admins see all dealerships.
    Dealership admins and users see only their dealership.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of dealerships
    """
    if current_user.role == UserRole.SUPER_ADMIN:
        # Super admin sees all dealerships
        result = await db.execute(
            select(Dealership).offset(skip).limit(limit)
        )
        dealerships = list(result.scalars().all())
    else:
        # Others see only their dealership
        if not current_user.dealership_id:
            return []
        result = await db.execute(
            select(Dealership).where(Dealership.id == current_user.dealership_id)
        )
        dealership = result.scalar_one_or_none()
        dealerships = [dealership] if dealership else []
    
    return [DealershipResponse.model_validate(d) for d in dealerships]


@router.get("/{dealership_id}", response_model=DealershipResponse, status_code=status.HTTP_200_OK)
async def get_dealership(
    dealership_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> DealershipResponse:
    """
    Get dealership by ID.
    
    Args:
        dealership_id: Dealership ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Dealership information
        
    Raises:
        NotFoundError: If dealership not found
        AuthorizationError: If user doesn't have access
    """
    result = await db.execute(
        select(Dealership).where(Dealership.id == dealership_id)
    )
    dealership = result.scalar_one_or_none()
    
    if not dealership:
        raise NotFoundError("Dealership not found")
    
    # Check access
    if current_user.role != UserRole.SUPER_ADMIN:
        if current_user.dealership_id != dealership_id:
            raise AuthorizationError("Access denied to this dealership")
    
    return DealershipResponse.model_validate(dealership)


@router.patch("/{dealership_id}", response_model=DealershipResponse, status_code=status.HTTP_200_OK)
async def update_dealership(
    dealership_id: int,
    dealership_data: DealershipUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> DealershipResponse:
    """
    Update dealership.
    
    Super admins can update any dealership.
    Dealership admins can update their own dealership.
    
    Args:
        dealership_id: Dealership ID
        dealership_data: Update data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Updated dealership
        
    Raises:
        NotFoundError: If dealership not found
        AuthorizationError: If user doesn't have permission
    """
    result = await db.execute(
        select(Dealership).where(Dealership.id == dealership_id)
    )
    dealership = result.scalar_one_or_none()
    
    if not dealership:
        raise NotFoundError("Dealership not found")
    
    # Check permissions
    if current_user.role == UserRole.SUPER_ADMIN:
        # Super admin can update any dealership
        pass
    elif current_user.role == UserRole.DEALERSHIP_ADMIN:
        # Dealership admin can only update their own dealership
        if current_user.dealership_id != dealership_id:
            raise AuthorizationError("You can only update your own dealership")
    else:
        raise AuthorizationError("Only admins can update dealerships")
    
    # Update fields
    update_data = dealership_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(dealership, field, value)
    
    db.add(dealership)
    await db.commit()
    await db.refresh(dealership)
    
    return DealershipResponse.model_validate(dealership)


@router.patch("/{dealership_id}/rag-config", response_model=DealershipResponse, status_code=status.HTTP_200_OK)
async def update_rag_config(
    dealership_id: int,
    rag_config: RAGConfigUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> DealershipResponse:
    """
    Update RAG configuration for dealership (Dealership Admin only).
    
    This endpoint allows dealership admins to configure their RAG settings
    for AI chat functionality.
    
    Args:
        dealership_id: Dealership ID
        rag_config: RAG configuration data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Updated dealership with new RAG config
        
    Raises:
        NotFoundError: If dealership not found
        AuthorizationError: If user is not dealership admin
    """
    result = await db.execute(
        select(Dealership).where(Dealership.id == dealership_id)
    )
    dealership = result.scalar_one_or_none()
    
    if not dealership:
        raise NotFoundError("Dealership not found")
    
    # Only dealership admin or super admin can update RAG config
    if current_user.role == UserRole.SUPER_ADMIN:
        pass
    elif current_user.role == UserRole.DEALERSHIP_ADMIN:
        if current_user.dealership_id != dealership_id:
            raise AuthorizationError("You can only update RAG config for your own dealership")
    else:
        raise AuthorizationError("Only dealership admins can update RAG configuration")
    
    # Update RAG config
    current_config = dealership.rag_config or {}
    new_config = rag_config.model_dump(exclude_unset=True)
    current_config.update(new_config)
    dealership.rag_config = current_config
    
    db.add(dealership)
    await db.commit()
    await db.refresh(dealership)
    
    return DealershipResponse.model_validate(dealership)


@router.delete("/{dealership_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dealership(
    dealership_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> None:
    """
    Delete dealership (Super Admin only).
    
    Args:
        dealership_id: Dealership ID
        db: Database session
        current_user: Current authenticated user
        
    Raises:
        NotFoundError: If dealership not found
        AuthorizationError: If user is not super admin
    """
    if current_user.role != UserRole.SUPER_ADMIN:
        raise AuthorizationError("Only super admins can delete dealerships")
    
    result = await db.execute(
        select(Dealership).where(Dealership.id == dealership_id)
    )
    dealership = result.scalar_one_or_none()
    
    if not dealership:
        raise NotFoundError("Dealership not found")
    
    await db.delete(dealership)
    await db.commit()
