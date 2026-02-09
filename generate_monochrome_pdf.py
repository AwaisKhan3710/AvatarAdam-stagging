#!/usr/bin/env python3
"""
Generate Professional Monochrome PDF with Visual Diagrams
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from datetime import datetime
from pathlib import Path

# Monochrome color scheme - Light Black
LIGHT_BLACK = colors.HexColor('#404040')
VERY_LIGHT_GRAY = colors.HexColor('#f5f5f5')
LIGHT_GRAY = colors.HexColor('#e5e7eb')
DARK_GRAY = colors.HexColor('#1f2937')
MED_GRAY = colors.HexColor('#6b7280')

class PageNumCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self.pages = []
    def showPage(self):
        self.pages.append(dict(self.__dict__))
        self._startPage()
    def save(self):
        page_count = len(self.pages)
        for page in self.pages:
            self.__dict__.update(page)
            self.setFont('Helvetica', 9)
            self.setFillColor(MED_GRAY)
            self.drawCentredString(A4[0]/2, 1.5*cm, f'Page {self._pageNumber} of {page_count}')
            if self._pageNumber > 1:
                self.setFont('Helvetica-Bold', 9)
                self.setFillColor(DARK_GRAY)
                self.drawString(2*cm, A4[1]-1.5*cm, 'Avatar Adam Documentation')
                self.setFont('Helvetica', 8)
                self.setFillColor(MED_GRAY)
                self.drawRightString(A4[0]-2*cm, A4[1]-1.5*cm, 'Feb 8, 2026')
                self.setStrokeColor(LIGHT_GRAY)
                self.setLineWidth(0.5)
                self.line(2*cm, A4[1]-1.7*cm, A4[0]-2*cm, A4[1]-1.7*cm)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

def create_arch_diagram():
    """Create system architecture diagram as table"""
    data = [
        ['PRESENTATION LAYER - Frontend'],
        ['React 18 + TypeScript, Vite, Tailwind CSS'],
        ['Pages: Login, Dashboard, Chat, Voice, RAG Management'],
        ['Components: Layout, ChatPanel, AuthContext'],
        [''],
        ['↓ HTTP/WebSocket with JWT'],
        [''],
        ['APPLICATION LAYER - Backend'],
        ['FastAPI, Python 3.12+, SQLAlchemy'],
        ['API Routes: /auth, /users, /chat, /voice, /rag, /avatar'],
        ['Services: LLM, RAG, Voice, Avatar, Email'],
        ['Middleware: CORS, Security Headers, Rate Limiting'],
        [''],
        ['↓ Database Queries & External API Calls'],
        [''],
        ['DATA LAYER - Storage'],
        ['PostgreSQL 16 + pgvector (Primary Database)'],
        ['Pinecone (Vector Database for Semantic Search)'],
        [''],
        ['↓ External Service Integration'],
        [''],
        ['EXTERNAL SERVICES'],
        ['OpenRouter (GPT-4o LLM), OpenAI (Embeddings & Whisper STT)'],
        ['ElevenLabs (TTS), HeyGen (Avatar), Mailgun (Email)']
    ]
    
    table = Table(data, colWidths=[5.5*inch])
    table.setStyle(TableStyle([
        # Headers
        ('BACKGROUND', (0,0), (-1,0), LIGHT_BLACK),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        
        ('BACKGROUND', (0,7), (-1,7), LIGHT_BLACK),
        ('TEXTCOLOR', (0,7), (-1,7), colors.white),
        ('FONTNAME', (0,7), (-1,7), 'Helvetica-Bold'),
        
        ('BACKGROUND', (0,15), (-1,15), LIGHT_BLACK),
        ('TEXTCOLOR', (0,15), (-1,15), colors.white),
        ('FONTNAME', (0,15), (-1,15), 'Helvetica-Bold'),
        
        ('BACKGROUND', (0,21), (-1,21), LIGHT_BLACK),
        ('TEXTCOLOR', (0,21), (-1,21), colors.white),
        ('FONTNAME', (0,21), (-1,21), 'Helvetica-Bold'),
        
        # Content
        ('BACKGROUND', (0,1), (-1,-1), VERY_LIGHT_GRAY),
        ('FONTSIZE', (0,1), (-1,-1), 8),
        ('ALIGN', (0,1), (-1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        
        # Arrows
        ('FONTSIZE', (0,5), (-1,5), 10),
        ('FONTSIZE', (0,13), (-1,13), 10),
        ('FONTSIZE', (0,19), (-1,19), 10),
        
        # Border
        ('BOX', (0,0), (-1,-1), 1, LIGHT_BLACK),
    ]))
    
    return table

def create_flow_diagram(title, steps):
    """Create a vertical flow diagram as table"""
    data = [[title]]
    for i, step in enumerate(steps, 1):
        data.append([f'{i}. {step}'])
        if i < len(steps):
            data.append(['↓'])
    
    table = Table(data, colWidths=[5.5*inch])
    table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0,0), (-1,0), LIGHT_BLACK),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        
        # Steps
        ('BACKGROUND', (0,1), (-1,-1), VERY_LIGHT_GRAY),
        ('FONTSIZE', (0,1), (-1,-1), 9),
        ('ALIGN', (0,1), (-1,-1), 'LEFT'),
        ('LEFTPADDING', (0,1), (-1,-1), 15),
        
        # Arrows
        ('ALIGN', (0,2), (-1,-1), 'CENTER'),
        ('FONTSIZE', (0,2), (-1,-1), 12),
        
        # Padding
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        
        # Border
        ('BOX', (0,0), (-1,-1), 1, LIGHT_BLACK),
    ]))
    
    return table

def create_schema_diagram(width):
    """Create database schema diagram"""
    d = Drawing(width, 3*inch)
    
    # Tables as boxes
    tables = [
        (80, 200, "USERS"),
        (280, 200, "DEALERSHIPS"),
        (80, 100, "REFRESH_TOKENS"),
        (280, 100, "DOCUMENTS"),
        (280, 20, "DOCUMENT_CHUNKS")
    ]
    
    for x, y, name in tables:
        d.add(Rect(x, y, 100, 30, fillColor=VERY_LIGHT_GRAY, strokeColor=LIGHT_BLACK, strokeWidth=1.5))
        d.add(String(x+50, y+15, name, fontSize=9, fillColor=DARK_GRAY, textAnchor='middle', fontName='Helvetica-Bold'))
    
    # Relationships (lines)
    # USERS to REFRESH_TOKENS
    d.add(Line(130, 200, 130, 130, strokeColor=LIGHT_BLACK, strokeWidth=1))
    
    # USERS to DEALERSHIPS
    d.add(Line(180, 215, 280, 215, strokeColor=LIGHT_BLACK, strokeWidth=1))
    
    # DEALERSHIPS to DOCUMENTS
    d.add(Line(330, 200, 330, 130, strokeColor=LIGHT_BLACK, strokeWidth=1))
    
    # DOCUMENTS to DOCUMENT_CHUNKS
    d.add(Line(330, 100, 330, 50, strokeColor=LIGHT_BLACK, strokeWidth=1))
    
    return d

def generate_pdf():
    pdf_file = "COMPLETE_PROJECT_DOCUMENTATION.pdf"
    doc = SimpleDocTemplate(pdf_file, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2.5*cm, bottomMargin=2.5*cm)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Title'], fontSize=32, textColor=DARK_GRAY, spaceAfter=0.3*inch, alignment=TA_CENTER, fontName='Helvetica-Bold')
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Heading2'], fontSize=16, textColor=MED_GRAY, spaceAfter=0.5*inch, alignment=TA_CENTER)
    h1_style = ParagraphStyle('H1', parent=styles['Heading1'], fontSize=16, textColor=DARK_GRAY, spaceAfter=0.2*inch, spaceBefore=0.3*inch, fontName='Helvetica-Bold')
    h2_style = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=13, textColor=DARK_GRAY, spaceAfter=0.15*inch, spaceBefore=0.2*inch, fontName='Helvetica-Bold')
    h3_style = ParagraphStyle('H3', parent=styles['Heading3'], fontSize=11, textColor=DARK_GRAY, spaceAfter=0.1*inch, spaceBefore=0.1*inch, fontName='Helvetica-Bold')
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=10, alignment=TA_JUSTIFY, spaceAfter=0.1*inch)
    
    story = []
    
    # Cover
    story.append(Spacer(1, 2*inch))
    story.append(Paragraph('Avatar Adam', title_style))
    story.append(Paragraph('Complete Project Documentation', subtitle_style))
    
    info_data = [['Version:', '1.0'], ['Date:', 'February 8, 2026'], ['Status:', 'Production-Ready MVP'], ['Classification:', 'Internal Use']]
    info_table = Table(info_data, colWidths=[2.5*inch, 3*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), VERY_LIGHT_GRAY),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 11),
        ('GRID', (0,0), (-1,-1), 1, LIGHT_BLACK),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(info_table)
    story.append(PageBreak())
    
    # Section 1
    story.append(Paragraph('1. Executive Summary', h1_style))
    story.append(Paragraph('Avatar Adam is an enterprise AI-powered conversational platform for automotive dealerships.', body_style))
    
    cap_data = [['Core Capabilities'], ['• Real-time voice chat with AI avatars'], ['• Intelligent text conversations'], ['• Document-based knowledge retrieval (RAG)'], ['• Multi-tenant dealership management'], ['• Enterprise-grade security (JWT, RBAC)']]
    cap_table = Table(cap_data, colWidths=[5.5*inch])
    cap_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), LIGHT_BLACK),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 11),
        ('BACKGROUND', (0,1), (-1,-1), VERY_LIGHT_GRAY),
        ('FONTSIZE', (0,1), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 0.5, LIGHT_BLACK),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(cap_table)
    story.append(Spacer(1, 0.2*inch))
    
    tech_data = [['Layer', 'Technology', 'Version'], ['Frontend', 'React + TypeScript', '18.2.0'], ['Backend', 'FastAPI', '0.115.0+'], ['Database', 'PostgreSQL + pgvector', '16'], ['Vector DB', 'Pinecone', '5.0.0'], ['LLM', 'OpenRouter (GPT-4o)', 'Latest']]
    tech_table = Table(tech_data, colWidths=[1.8*inch, 2.2*inch, 1.5*inch])
    tech_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), LIGHT_BLACK),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BACKGROUND', (0,1), (-1,-1), colors.white),
        ('FONTSIZE', (0,1), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 0.5, LIGHT_BLACK),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(tech_table)
    story.append(PageBreak())
    
    # Section 2: Architecture
    story.append(Paragraph('2. System Architecture', h1_style))
    story.append(Paragraph('2.1 Architecture Diagram', h2_style))
    story.append(create_arch_diagram())
    story.append(Spacer(1, 0.15*inch))
    
    # Explanation points
    story.append(Paragraph('<b>Key Points:</b>', h3_style))
    story.append(Paragraph('• Frontend handles user interface and interactions', body_style))
    story.append(Paragraph('• Backend processes requests and manages business logic', body_style))
    story.append(Paragraph('• Data layer provides persistent storage and vector search', body_style))
    story.append(Paragraph('• External services provide AI capabilities (LLM, TTS, STT, Avatar)', body_style))
    story.append(Spacer(1, 0.2*inch))
    
    story.append(Paragraph('2.2 Request Processing Flow', h2_style))
    flow_steps = ['User Interaction', 'HTTP/WebSocket Request', 'CORS & Rate Limit', 'JWT Validation', 'API Route Handler', 'Service Layer', 'Response Generation']
    story.append(create_flow_diagram('Request Flow', flow_steps))
    story.append(Spacer(1, 0.15*inch))
    
    # Explanation points
    story.append(Paragraph('<b>Key Points:</b>', h3_style))
    story.append(Paragraph('• Every request passes through security middleware (CORS, rate limiting)', body_style))
    story.append(Paragraph('• JWT tokens are validated before accessing protected endpoints', body_style))
    story.append(Paragraph('• Service layer handles all business logic and external API calls', body_style))
    story.append(Paragraph('• Responses are properly formatted and include appropriate status codes', body_style))
    story.append(PageBreak())
    
    # Section 5: User Flows
    story.append(Paragraph('5. User Flows', h1_style))
    
    story.append(Paragraph('5.1 Authentication Flow', h2_style))
    auth_steps = ['User enters credentials', 'POST /api/v1/auth/login', 'Verify password (bcrypt)', 'Generate JWT tokens', 'Store in localStorage', 'Redirect to Dashboard']
    story.append(create_flow_diagram('Authentication Flow', auth_steps))
    story.append(Spacer(1, 0.15*inch))
    
    # Explanation points
    story.append(Paragraph('<b>Key Points:</b>', h3_style))
    story.append(Paragraph('• Passwords are hashed using bcrypt with 12 rounds for security', body_style))
    story.append(Paragraph('• Access tokens expire after 30 minutes, refresh tokens after 7 days', body_style))
    story.append(Paragraph('• Tokens are stored in localStorage for persistent sessions', body_style))
    story.append(Spacer(1, 0.2*inch))
    
    story.append(Paragraph('5.2 Chat Flow with RAG', h2_style))
    chat_steps = ['User enters message', 'POST /api/v1/chat/message', 'Generate query embedding', 'Semantic search (Pinecone)', 'Retrieve top 5 chunks', 'Add context to LLM', 'Stream AI response', 'Display to user']
    story.append(create_flow_diagram('Chat Flow', chat_steps))
    story.append(Spacer(1, 0.15*inch))
    
    # Explanation points
    story.append(Paragraph('<b>Key Points:</b>', h3_style))
    story.append(Paragraph('• Query embeddings enable semantic search (meaning-based, not keyword)', body_style))
    story.append(Paragraph('• Top 5 most relevant document chunks are retrieved from Pinecone', body_style))
    story.append(Paragraph('• Context is added to LLM prompt for accurate, document-based responses', body_style))
    story.append(Paragraph('• Responses are streamed in real-time for better user experience', body_style))
    story.append(Spacer(1, 0.2*inch))
    
    story.append(Paragraph('5.3 Voice Chat Flow', h2_style))
    voice_steps = ['Start recording', 'WebSocket connection', 'Send audio chunks', 'Whisper STT', 'LLM processing', 'ElevenLabs TTS', 'HeyGen avatar', 'Play audio & video']
    story.append(create_flow_diagram('Voice Chat Flow', voice_steps))
    story.append(PageBreak())
    
    # Section 6: API Endpoints
    story.append(Paragraph('6. API Endpoints Reference', h1_style))
    
    endpoints_data = [
        ['Endpoint', 'Method', 'Auth', 'Purpose'],
        ['/api/v1/auth/login', 'POST', 'No', 'User login'],
        ['/api/v1/auth/signup', 'POST', 'No', 'User registration'],
        ['/api/v1/auth/refresh', 'POST', 'Refresh', 'Refresh token'],
        ['/api/v1/auth/me', 'GET', 'Yes', 'Get current user'],
        ['/api/v1/users', 'GET', 'Yes', 'List users'],
        ['/api/v1/users', 'POST', 'Admin', 'Create user'],
        ['/api/v1/users/{id}', 'GET', 'Yes', 'Get user'],
        ['/api/v1/users/{id}', 'PATCH', 'Admin', 'Update user'],
        ['/api/v1/users/{id}', 'DELETE', 'Admin', 'Delete user'],
        ['/api/v1/chat/message', 'POST', 'Yes', 'Send message'],
        ['/api/v1/chat/history', 'GET', 'Yes', 'Get history'],
        ['/api/v1/voice/ws', 'WS', 'Yes', 'Voice chat'],
        ['/api/v1/rag/documents/upload', 'POST', 'Admin', 'Upload doc'],
        ['/api/v1/rag/documents', 'GET', 'Yes', 'List docs'],
        ['/api/v1/rag/search', 'POST', 'Yes', 'Search'],
        ['/api/v1/dealerships', 'GET', 'Yes', 'List dealerships'],
        ['/api/v1/avatar/session', 'POST', 'Yes', 'Create session']
    ]
    
    endpoints_table = Table(endpoints_data, colWidths=[2.3*inch, 0.7*inch, 0.7*inch, 1.8*inch])
    endpoints_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), LIGHT_BLACK),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('BACKGROUND', (0,1), (-1,-1), colors.white),
        ('FONTSIZE', (0,1), (-1,-1), 7),
        ('GRID', (0,0), (-1,-1), 0.5, LIGHT_BLACK),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(endpoints_table)
    story.append(PageBreak())
    
    # Section 7: Database Schema
    story.append(Paragraph('7. Database Schema', h1_style))
    story.append(Paragraph('7.1 Schema Diagram', h2_style))
    story.append(create_schema_diagram(6*inch))
    story.append(Spacer(1, 0.3*inch))
    
    story.append(Paragraph('7.2 Table Definitions', h2_style))
    
    tables_data = [
        ['Table', 'Key Fields', 'Purpose'],
        ['users', 'id, email, role, dealership_id', 'User accounts'],
        ['dealerships', 'id, name, location, rag_enabled', 'Dealership info'],
        ['documents', 'id, dealership_id, filename, status', 'Document metadata'],
        ['document_chunks', 'id, document_id, content, embedding', 'Text chunks'],
        ['refresh_tokens', 'id, user_id, token, expires_at', 'JWT refresh']
    ]
    
    tables_table = Table(tables_data, colWidths=[1.5*inch, 2.5*inch, 1.5*inch])
    tables_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), LIGHT_BLACK),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('BACKGROUND', (0,1), (-1,-1), colors.white),
        ('FONTSIZE', (0,1), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, LIGHT_BLACK),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(tables_table)
    story.append(PageBreak())
    
    # Section 8: Security
    story.append(Paragraph('8. Security Architecture', h1_style))
    
    sec_steps = ['Client Layer (Browser)', 'API Gateway (CORS, Rate Limit)', 'Authentication (JWT)', 'Authorization (RBAC)', 'Application Layer', 'Data Security (Bcrypt, Validation)']
    story.append(create_flow_diagram('Security Layers', sec_steps))
    story.append(Spacer(1, 0.15*inch))
    
    # Explanation points
    story.append(Paragraph('<b>Key Points:</b>', h3_style))
    story.append(Paragraph('• Multi-layer security approach provides defense in depth', body_style))
    story.append(Paragraph('• CORS and rate limiting protect against common web attacks', body_style))
    story.append(Paragraph('• JWT tokens ensure stateless, scalable authentication', body_style))
    story.append(Paragraph('• RBAC provides granular access control based on user roles', body_style))
    story.append(Paragraph('• Input validation and ORM prevent injection attacks', body_style))
    story.append(Spacer(1, 0.2*inch))
    
    rbac_data = [
        ['Role', 'Permissions'],
        ['super_admin', 'Full system access, manage all'],
        ['dealership_admin', 'Manage dealership, upload docs'],
        ['user', 'Access chat and voice features']
    ]
    
    rbac_table = Table(rbac_data, colWidths=[1.8*inch, 3.7*inch])
    rbac_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), LIGHT_BLACK),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BACKGROUND', (0,1), (-1,-1), colors.white),
        ('FONTSIZE', (0,1), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 0.5, LIGHT_BLACK),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(rbac_table)
    story.append(PageBreak())
    
    # Section 9: Deployment
    story.append(Paragraph('9. Deployment Guide', h1_style))
    story.append(Paragraph('9.1 Backend Deployment', h2_style))
    for cmd in ['cd backend', 'python -m venv venv', 'source venv/bin/activate', 'pip install -r requirements.txt', 'alembic upgrade head', 'python -m uvicorn app.main:app --host 0.0.0.0 --port 8000']:
        story.append(Paragraph(f'<font face=\"Courier\" size=\"8\">{cmd}</font>', body_style))
    
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph('9.2 Frontend Deployment', h2_style))
    for cmd in ['cd frontend', 'npm install', 'npm run build', 'npm run preview']:
        story.append(Paragraph(f'<font face=\"Courier\" size=\"8\">{cmd}</font>', body_style))
    
    story.append(PageBreak())
    
    # Section 10: File Structure
    story.append(Paragraph('10. File Structure', h1_style))
    
    story.append(Paragraph('10.1 Backend Directory Tree', h2_style))
    
    backend_tree = [
        'backend/',
        '+-- app/',
        '|   +-- main.py                    # FastAPI application entry',
        '|   +-- api/',
        '|   |   +-- deps.py                # Dependency injection',
        '|   |   +-- v1/',
        '|   |       +-- auth.py            # Authentication endpoints',
        '|   |       +-- users.py           # User management',
        '|   |       +-- dealerships.py     # Dealership management',
        '|   |       +-- chat.py            # Chat endpoints',
        '|   |       +-- voice.py           # Voice endpoints',
        '|   |       +-- voice_live.py      # WebSocket voice',
        '|   |       +-- rag.py             # RAG endpoints',
        '|   |       +-- avatar.py          # Avatar endpoints',
        '|   |       +-- report.py          # Report endpoints',
        '|   +-- core/',
        '|   |   +-- config.py              # Configuration settings',
        '|   |   +-- database.py            # Database connection',
        '|   |   +-- security.py            # JWT & password utils',
        '|   |   +-- exceptions.py          # Custom exceptions',
        '|   +-- middleware/',
        '|   |   +-- rate_limit.py          # Rate limiting',
        '|   |   +-- security_headers.py    # Security headers',
        '|   +-- models/',
        '|   |   +-- user.py                # User SQLAlchemy model',
        '|   |   +-- dealership.py          # Dealership model',
        '|   |   +-- document.py            # Document models',
        '|   |   +-- refresh_token.py       # RefreshToken model',
        '|   +-- schemas/',
        '|   |   +-- auth.py                # Auth Pydantic schemas',
        '|   |   +-- user.py                # User schemas',
        '|   |   +-- dealership.py          # Dealership schemas',
        '|   |   +-- common.py              # Common schemas',
        '|   +-- services/',
        '|       +-- llm_service.py         # OpenRouter integration',
        '|       +-- rag_service.py         # Pinecone + LangChain',
        '|       +-- rag_cache.py           # Multi-level caching',
        '|       +-- voice_service.py       # Whisper + ElevenLabs',
        '|       +-- realtime_voice_service.py  # WebSocket voice',
        '|       +-- avatar_service.py      # HeyGen integration',
        '|       +-- email_service.py       # Mailgun integration',
        '+-- alembic/',
        '|   +-- env.py                     # Alembic configuration',
        '|   +-- versions/                  # Migration files',
        '+-- scripts/',
        '|   +-- seed_db.py                 # Database seeding',
        '+-- .env                           # Environment variables',
        '+-- alembic.ini                    # Alembic config',
        '+-- pyproject.toml                 # Python dependencies',
        '+-- test_api.py                    # API integration tests',
        '+-- test_simple.py                 # Basic setup tests'
    ]
    
    tree_table = Table([[line] for line in backend_tree], colWidths=[6*inch])
    tree_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Courier'),
        ('FONTSIZE', (0,0), (-1,-1), 7),
        ('TEXTCOLOR', (0,0), (-1,-1), DARK_GRAY),
        ('BACKGROUND', (0,0), (-1,-1), VERY_LIGHT_GRAY),
        ('BOX', (0,0), (-1,-1), 1, LIGHT_BLACK),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(tree_table)
    story.append(Spacer(1, 0.3*inch))
    
    story.append(Paragraph('10.2 Frontend Directory Tree', h2_style))
    
    frontend_tree = [
        'frontend/',
        '+-- src/',
        '|   +-- App.tsx                    # Main application component',
        '|   +-- main.tsx                   # React entry point',
        '|   +-- index.css                  # Global styles',
        '|   +-- pages/',
        '|   |   +-- Login.tsx              # Login page',
        '|   |   +-- Dashboard.tsx          # Main dashboard',
        '|   |   +-- Chat.tsx               # Chat interface',
        '|   |   +-- VoiceChat.tsx          # Voice chat page',
        '|   |   +-- VoiceCall.tsx          # Voice call interface',
        '|   |   +-- RagManagement.tsx      # Document management',
        '|   |   +-- UserManagement.tsx     # User management',
        '|   |   +-- DealershipManagement.tsx  # Dealership mgmt',
        '|   +-- components/',
        '|   |   +-- Layout.tsx             # Main layout wrapper',
        '|   |   +-- ChatPanel.tsx          # Chat UI component',
        '|   +-- context/',
        '|   |   +-- AuthContext.tsx        # Authentication context',
        '|   +-- hooks/',
        '|   |   +-- useVoiceChat.ts        # Voice chat custom hook',
        '|   +-- services/',
        '|   |   +-- api.ts                 # Axios API client',
        '|   +-- types/',
        '|       +-- index.ts               # TypeScript definitions',
        '+-- public/                        # Static assets',
        '+-- package.json                   # NPM dependencies',
        '+-- tsconfig.json                  # TypeScript config',
        '+-- vite.config.ts                 # Vite configuration',
        '+-- tailwind.config.js             # Tailwind CSS config',
        '+-- postcss.config.js              # PostCSS config',
        '+-- .eslintrc.cjs                  # ESLint configuration'
    ]
    
    tree_table2 = Table([[line] for line in frontend_tree], colWidths=[6*inch])
    tree_table2.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Courier'),
        ('FONTSIZE', (0,0), (-1,-1), 7),
        ('TEXTCOLOR', (0,0), (-1,-1), DARK_GRAY),
        ('BACKGROUND', (0,0), (-1,-1), VERY_LIGHT_GRAY),
        ('BOX', (0,0), (-1,-1), 1, LIGHT_BLACK),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(tree_table2)
    
    # Build
    doc.build(story, canvasmaker=PageNumCanvas)
    size = Path(pdf_file).stat().st_size / 1024
    print(f'✅ Monochrome PDF created: {pdf_file}')
    print(f'📊 Size: {size:.1f} KB')

if __name__ == "__main__":
    generate_pdf()