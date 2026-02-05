"""API endpoints for reporting inaccurate Avatar Adam responses."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.email_service import get_email_service

logger = logging.getLogger(__name__)

router = APIRouter()


class InaccuracyReportRequest(BaseModel):
    """Request model for reporting an inaccurate response."""
    
    user_input: str = Field(..., description="The user's original prompt/input")
    avatar_response: str = Field(..., description="The Avatar Adam response being reported")
    conversation_context: Optional[list[dict]] = Field(
        default=None, 
        description="Previous conversation history for context"
    )
    user_note: Optional[str] = Field(
        default=None, 
        description="Optional user description of what's wrong with the output"
    )
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    mode: Optional[str] = Field(default=None, description="Training or roleplay mode")
    dealership_name: Optional[str] = Field(default=None, description="Name of the dealership")


class InaccuracyReportResponse(BaseModel):
    """Response model for inaccuracy report submission."""
    
    success: bool
    message: str


@router.post(
    "/inaccuracy",
    response_model=InaccuracyReportResponse,
    summary="Report an inaccurate Avatar Adam response",
    description="""
    Submit a report for an inaccurate or low-quality Avatar Adam response.
    
    This endpoint captures the user's input, the problematic response, and any
    additional context to help the support/training team improve the model.
    
    The report is sent via email and tagged as an "Inaccuracy Report" for
    model refinement and training purposes.
    """,
)
async def report_inaccuracy(
    request: InaccuracyReportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InaccuracyReportResponse:
    """
    Report an inaccurate Avatar Adam response for review and model training.
    
    Args:
        request: The inaccuracy report details
        current_user: The authenticated user submitting the report
        db: Database session
        
    Returns:
        Success status and message
    """
    try:
        email_service = get_email_service()
        
        # Get dealership name if available
        dealership_name = request.dealership_name
        if not dealership_name and current_user.dealership_id:
            # Could fetch from DB if needed
            dealership_name = f"Dealership #{current_user.dealership_id}"
        
        success = await email_service.send_inaccuracy_report(
            user_input=request.user_input,
            avatar_response=request.avatar_response,
            conversation_context=request.conversation_context,
            user_note=request.user_note,
            user_id=current_user.id,
            session_id=request.session_id,
            mode=request.mode,
            dealership_name=dealership_name,
        )
        
        if success:
            logger.info(f"Inaccuracy report submitted by user {current_user.id}")
            return InaccuracyReportResponse(
                success=True,
                message="Thank you for your feedback. Your report has been submitted for review.",
            )
        else:
            logger.error(f"Failed to send inaccuracy report for user {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to submit report. Please try again later.",
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting inaccuracy report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while submitting your report.",
        )


class SendToTeamRequest(BaseModel):
    """Request model for sending conversation to team."""
    
    user_question: str = Field(..., description="The user's question")
    ai_response: str = Field(..., description="The AI's response")
    conversation_history: list[dict] = Field(
        ..., 
        description="Full conversation history"
    )
    additional_notes: Optional[str] = Field(
        default=None, 
        description="Optional additional notes from the user"
    )
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    dealership_name: Optional[str] = Field(default=None, description="Name of the dealership")


class SendToTeamResponse(BaseModel):
    """Response model for send to team submission."""
    
    success: bool
    message: str


@router.post(
    "/send-to-team",
    response_model=SendToTeamResponse,
    summary="Send conversation to team",
    description="""
    Send a conversation to the team for review or follow-up.
    
    This endpoint captures the user's question, AI response, full conversation
    history, and any additional notes to share with the team.
    """,
)
async def send_to_team(
    request: SendToTeamRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SendToTeamResponse:
    """
    Send a conversation to the team for review.
    
    Args:
        request: The send to team request details
        current_user: The authenticated user submitting the request
        db: Database session
        
    Returns:
        Success status and message
    """
    try:
        email_service = get_email_service()
        
        # Get dealership name if available
        dealership_name = request.dealership_name
        if not dealership_name and current_user.dealership_id:
            dealership_name = f"Dealership #{current_user.dealership_id}"
        
        success = await email_service.send_to_team(
            user_question=request.user_question,
            ai_response=request.ai_response,
            conversation_history=request.conversation_history,
            additional_notes=request.additional_notes,
            user_id=current_user.id,
            session_id=request.session_id,
            dealership_name=dealership_name,
        )
        
        if success:
            logger.info(f"Send to team request submitted by user {current_user.id}")
            return SendToTeamResponse(
                success=True,
                message="Your message has been sent to the team.",
            )
        else:
            logger.error(f"Failed to send to team for user {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send message. Please try again later.",
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending to team: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while sending your message.",
        )
