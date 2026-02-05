"""Email service using Mailgun Python SDK for sending reports."""

import logging
from datetime import datetime
from typing import Optional

from mailgun.client import AsyncClient  # from mailgun package (pip install mailgun)

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via Mailgun Python SDK (AsyncClient)."""

    def __init__(self):
        self.api_key = settings.MAILGUN_API_KEY
        self.domain = settings.MAILGUN_DOMAIN
        self.from_email = settings.MAILGUN_FROM_EMAIL
        self.region = settings.MAILGUN_REGION
        
        # Set API URL based on region (US or EU)
        # US: https://api.mailgun.net/
        # EU: https://api.eu.mailgun.net/
        self.api_url = None
        if self.region and self.region.upper() == "EU":
            self.api_url = "https://api.eu.mailgun.net/"

    async def send_email(
        self,
        to: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """
        Send an email via Mailgun AsyncClient SDK.
        
        Args:
            to: Recipient email address
            subject: Email subject
            html_content: HTML body content
            text_content: Plain text body content (optional)
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        if not self.api_key or not self.domain:
            logger.error("Mailgun not configured - missing API key or domain")
            return False

        try:
            data = {
                "from": self.from_email,
                "to": to,
                "subject": subject,
                "html": html_content,
            }
            
            if text_content:
                data["text"] = text_content

            # Use AsyncClient as context manager for proper connection handling
            async with AsyncClient(auth=("api", self.api_key), api_url=self.api_url) as client:
                response = await client.messages.create(data=data, domain=self.domain)

            if response.status_code == 200:
                logger.info(f"Email sent successfully to {to}")
                return True
            else:
                logger.error(f"Failed to send email: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False

    async def send_inaccuracy_report(
        self,
        user_input: str,
        avatar_response: str,
        conversation_context: Optional[list[dict]] = None,
        user_note: Optional[str] = None,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        mode: Optional[str] = None,
        dealership_name: Optional[str] = None,
    ) -> bool:
        """
        Send an inaccuracy report for Avatar Adam responses.
        
        Args:
            user_input: The user's original prompt/input
            avatar_response: The Avatar Adam response being reported
            conversation_context: Previous conversation history
            user_note: Optional user description of what's wrong
            user_id: User identifier
            session_id: Session identifier
            mode: Training or roleplay mode
            dealership_name: Name of the dealership
            
        Returns:
            True if report was sent successfully, False otherwise
        """
        recipient = settings.REPORT_RECIPIENT_EMAIL
        if not recipient:
            logger.error("Report recipient email not configured")
            return False

        timestamp = datetime.utcnow().isoformat()
        
        # Build HTML email content
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #dc2626; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .content {{ background: #f9fafb; padding: 20px; border: 1px solid #e5e7eb; }}
        .section {{ background: white; padding: 15px; margin: 10px 0; border-radius: 8px; border: 1px solid #e5e7eb; }}
        .section-title {{ font-weight: bold; color: #374151; margin-bottom: 10px; font-size: 14px; text-transform: uppercase; }}
        .metadata {{ display: flex; flex-wrap: wrap; gap: 15px; }}
        .metadata-item {{ background: #f3f4f6; padding: 8px 12px; border-radius: 4px; font-size: 13px; }}
        .metadata-label {{ font-weight: bold; color: #6b7280; }}
        .user-input {{ background: #dbeafe; border-left: 4px solid #3b82f6; padding: 15px; }}
        .avatar-response {{ background: #fee2e2; border-left: 4px solid #dc2626; padding: 15px; }}
        .user-note {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; }}
        .context {{ background: #f3f4f6; padding: 15px; max-height: 300px; overflow-y: auto; }}
        .context-message {{ padding: 8px; margin: 5px 0; border-radius: 4px; }}
        .context-user {{ background: #dbeafe; }}
        .context-assistant {{ background: #e5e7eb; }}
        pre {{ white-space: pre-wrap; word-wrap: break-word; margin: 0; }}
        .footer {{ text-align: center; padding: 15px; color: #6b7280; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚨 Avatar Adam Inaccuracy Report</h1>
        </div>
        <div class="content">
            <div class="section">
                <div class="section-title">📋 Report Metadata</div>
                <div class="metadata">
                    <div class="metadata-item"><span class="metadata-label">Timestamp:</span> {timestamp}</div>
                    <div class="metadata-item"><span class="metadata-label">User ID:</span> {user_id or 'N/A'}</div>
                    <div class="metadata-item"><span class="metadata-label">Session:</span> {session_id or 'N/A'}</div>
                    <div class="metadata-item"><span class="metadata-label">Mode:</span> {mode or 'N/A'}</div>
                    <div class="metadata-item"><span class="metadata-label">Dealership:</span> {dealership_name or 'N/A'}</div>
                </div>
            </div>
            
            <div class="section">
                <div class="section-title">💬 User Input</div>
                <div class="user-input">
                    <pre>{user_input}</pre>
                </div>
            </div>
            
            <div class="section">
                <div class="section-title">🤖 Avatar Adam Response (Reported as Inaccurate)</div>
                <div class="avatar-response">
                    <pre>{avatar_response}</pre>
                </div>
            </div>
            
            {f'''
            <div class="section">
                <div class="section-title">📝 User's Note</div>
                <div class="user-note">
                    <pre>{user_note}</pre>
                </div>
            </div>
            ''' if user_note else ''}
            
            {self._format_context_html(conversation_context) if conversation_context else ''}
        </div>
        <div class="footer">
            <p>This report was automatically generated by Avatar Adam for model training and quality improvement.</p>
            <p>Category: <strong>Inaccuracy Report</strong> | Source: <strong>Avatar Adam</strong></p>
        </div>
    </div>
</body>
</html>
"""

        # Plain text version
        text_content = f"""
AVATAR ADAM INACCURACY REPORT
=============================

METADATA
--------
Timestamp: {timestamp}
User ID: {user_id or 'N/A'}
Session: {session_id or 'N/A'}
Mode: {mode or 'N/A'}
Dealership: {dealership_name or 'N/A'}

USER INPUT
----------
{user_input}

AVATAR ADAM RESPONSE (REPORTED AS INACCURATE)
---------------------------------------------
{avatar_response}

{f"USER'S NOTE\n-----------\n{user_note}" if user_note else ''}

{self._format_context_text(conversation_context) if conversation_context else ''}

---
Category: Inaccuracy Report | Source: Avatar Adam
"""

        subject = f"🚨 Avatar Adam Inaccuracy Report - {timestamp[:10]}"
        
        return await self.send_email(
            to=recipient,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    async def send_to_team(
        self,
        user_question: str,
        ai_response: str,
        conversation_history: list[dict],
        additional_notes: Optional[str] = None,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        dealership_name: Optional[str] = None,
    ) -> bool:
        """
        Send a conversation to the team for review.
        
        Args:
            user_question: The user's question
            ai_response: The AI's response
            conversation_history: Full conversation history
            additional_notes: Optional additional notes from the user
            user_id: User identifier
            session_id: Session identifier
            dealership_name: Name of the dealership
            
        Returns:
            True if message was sent successfully, False otherwise
        """
        recipient = settings.REPORT_RECIPIENT_EMAIL
        if not recipient:
            logger.error("Report recipient email not configured")
            return False

        timestamp = datetime.utcnow().isoformat()
        
        # Build HTML email content
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #059669; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .content {{ background: #f9fafb; padding: 20px; border: 1px solid #e5e7eb; }}
        .section {{ background: white; padding: 15px; margin: 10px 0; border-radius: 8px; border: 1px solid #e5e7eb; }}
        .section-title {{ font-weight: bold; color: #374151; margin-bottom: 10px; font-size: 14px; text-transform: uppercase; }}
        .metadata {{ display: flex; flex-wrap: wrap; gap: 15px; }}
        .metadata-item {{ background: #f3f4f6; padding: 8px 12px; border-radius: 4px; font-size: 13px; }}
        .metadata-label {{ font-weight: bold; color: #6b7280; }}
        .user-question {{ background: #dbeafe; border-left: 4px solid #3b82f6; padding: 15px; }}
        .ai-response {{ background: #d1fae5; border-left: 4px solid #059669; padding: 15px; }}
        .user-note {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; }}
        .context {{ background: #f3f4f6; padding: 15px; max-height: 300px; overflow-y: auto; }}
        .context-message {{ padding: 8px; margin: 5px 0; border-radius: 4px; }}
        .context-user {{ background: #dbeafe; }}
        .context-assistant {{ background: #d1fae5; }}
        pre {{ white-space: pre-wrap; word-wrap: break-word; margin: 0; }}
        .footer {{ text-align: center; padding: 15px; color: #6b7280; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📨 Avatar Adam - Message to Team</h1>
        </div>
        <div class="content">
            <div class="section">
                <div class="section-title">📋 Message Metadata</div>
                <div class="metadata">
                    <div class="metadata-item"><span class="metadata-label">Timestamp:</span> {timestamp}</div>
                    <div class="metadata-item"><span class="metadata-label">User ID:</span> {user_id or 'N/A'}</div>
                    <div class="metadata-item"><span class="metadata-label">Session:</span> {session_id or 'N/A'}</div>
                    <div class="metadata-item"><span class="metadata-label">Dealership:</span> {dealership_name or 'N/A'}</div>
                </div>
            </div>
            
            <div class="section">
                <div class="section-title">💬 User's Question</div>
                <div class="user-question">
                    <pre>{user_question}</pre>
                </div>
            </div>
            
            <div class="section">
                <div class="section-title">🤖 AI Response</div>
                <div class="ai-response">
                    <pre>{ai_response}</pre>
                </div>
            </div>
            
            {f'''
            <div class="section">
                <div class="section-title">📝 Additional Notes</div>
                <div class="user-note">
                    <pre>{additional_notes}</pre>
                </div>
            </div>
            ''' if additional_notes else ''}
            
            {self._format_team_context_html(conversation_history) if conversation_history else ''}
        </div>
        <div class="footer">
            <p>This message was sent from Avatar Adam.</p>
            <p>Category: <strong>Team Message</strong> | Source: <strong>Avatar Adam</strong></p>
        </div>
    </div>
</body>
</html>
"""

        # Plain text version
        text_content = f"""
AVATAR ADAM - MESSAGE TO TEAM
=============================

METADATA
--------
Timestamp: {timestamp}
User ID: {user_id or 'N/A'}
Session: {session_id or 'N/A'}
Dealership: {dealership_name or 'N/A'}

USER'S QUESTION
---------------
{user_question}

AI RESPONSE
-----------
{ai_response}

{f"ADDITIONAL NOTES\n----------------\n{additional_notes}" if additional_notes else ''}

{self._format_team_context_text(conversation_history) if conversation_history else ''}

---
Category: Team Message | Source: Avatar Adam
"""

        subject = f"📨 Avatar Adam - Team Message - {timestamp[:10]}"
        
        return await self.send_email(
            to=recipient,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    def _format_team_context_html(self, context: list[dict]) -> str:
        """Format full conversation history as HTML for team messages."""
        if not context:
            return ""
        
        messages_html = ""
        for msg in context:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            css_class = "context-user" if role == "user" else "context-assistant"
            role_label = "User" if role == "user" else "AI"
            messages_html += f'<div class="context-message {css_class}"><strong>{role_label}:</strong> {content}</div>'
        
        return f'''
        <div class="section">
            <div class="section-title">📜 Full Conversation History ({len(context)} messages)</div>
            <div class="context">
                {messages_html}
            </div>
        </div>
        '''

    def _format_team_context_text(self, context: list[dict]) -> str:
        """Format full conversation history as plain text for team messages."""
        if not context:
            return ""
        
        lines = ["FULL CONVERSATION HISTORY", "-" * 25]
        for msg in context:
            role = msg.get("role", "unknown").upper()
            content = msg.get("content", "")
            lines.append(f"{role}: {content}")
        
        return "\n".join(lines)

    def _format_context_html(self, context: list[dict]) -> str:
        """Format conversation context as HTML."""
        if not context:
            return ""
        
        messages_html = ""
        for msg in context[-10:]:  # Last 10 messages
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            css_class = "context-user" if role == "user" else "context-assistant"
            role_label = "User" if role == "user" else "Assistant"
            messages_html += f'<div class="context-message {css_class}"><strong>{role_label}:</strong> {content}</div>'
        
        return f'''
        <div class="section">
            <div class="section-title">📜 Conversation Context (Last {min(len(context), 10)} messages)</div>
            <div class="context">
                {messages_html}
            </div>
        </div>
        '''

    def _format_context_text(self, context: list[dict]) -> str:
        """Format conversation context as plain text."""
        if not context:
            return ""
        
        lines = ["CONVERSATION CONTEXT", "-" * 20]
        for msg in context[-10:]:
            role = msg.get("role", "unknown").upper()
            content = msg.get("content", "")
            lines.append(f"{role}: {content}")
        
        return "\n".join(lines)


# Singleton instance
email_service = EmailService()


def get_email_service() -> EmailService:
    """Get the email service instance."""
    return email_service
