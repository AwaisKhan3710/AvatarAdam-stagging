#!/usr/bin/env python3
"""
Generate Simple, Clean Professional PDF
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from pathlib import Path

# Simple monochrome colors
BLACK = colors.HexColor('#2d3748')
GRAY = colors.HexColor('#718096')
LIGHT_GRAY = colors.HexColor('#e2e8f0')
BG_GRAY = colors.HexColor('#f7fafc')

class SimpleCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self.pages = []
    
    def showPage(self):
        self.pages.append(dict(self.__dict__))
        self._startPage()
    
    def save(self):
        for page in self.pages:
            self.__dict__.update(page)
            self.setFont('Helvetica', 8)
            self.setFillColor(GRAY)
            self.drawCentredString(A4[0]/2, 1*cm, f'Page {self._pageNumber}')
            if self._pageNumber > 1:
                self.setFont('Helvetica-Bold', 9)
                self.setFillColor(BLACK)
                self.drawString(2*cm, A4[1]-1.2*cm, 'Avatar Adam Documentation')
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

def simple_arch_diagram():
    """Simple 4-box architecture"""
    d = Drawing(400, 320)
    
    boxes = [
        ('Frontend', 'React + TypeScript', 260),
        ('Backend', 'FastAPI + Python', 190),
        ('Database', 'PostgreSQL + Pinecone', 120),
        ('AI Services', 'OpenRouter, OpenAI, ElevenLabs', 50)
    ]
    
    for i, (title, desc, y) in enumerate(boxes):
        d.add(Rect(80, y, 240, 50, fillColor=BG_GRAY, strokeColor=BLACK, strokeWidth=1.5))
        d.add(String(200, y+32, title, fontSize=11, fontName='Helvetica-Bold', textAnchor='middle', fillColor=BLACK))
        d.add(String(200, y+15, desc, fontSize=9, textAnchor='middle', fillColor=GRAY))
        
        if i < len(boxes) - 1:
            d.add(Line(200, y, 200, y-20, strokeColor=BLACK, strokeWidth=2))
            d.add(Line(196, y-15, 200, y-20, strokeColor=BLACK, strokeWidth=2))
            d.add(Line(204, y-15, 200, y-20, strokeColor=BLACK, strokeWidth=2))
    
    return d

def simple_flow_diagram(steps):
    """Simple vertical flow"""
    d = Drawing(400, len(steps) * 50 + 20)
    
    y = len(steps) * 50
    for i, step in enumerate(steps):
        d.add(Rect(60, y-35, 280, 35, fillColor=BG_GRAY, strokeColor=BLACK, strokeWidth=1))
        d.add(String(70, y-17, f'{i+1}. {step}', fontSize=9, fillColor=BLACK))
        
        if i < len(steps) - 1:
            d.add(Line(200, y-35, 200, y-45, strokeColor=BLACK, strokeWidth=1.5))
            d.add(Line(196, y-40, 200, y-45, strokeColor=BLACK, strokeWidth=1.5))
            d.add(Line(204, y-40, 200, y-45, strokeColor=BLACK, strokeWidth=1.5))
        
        y -= 50
    
    return d

def simple_db_diagram():
    """Simple database schema"""
    d = Drawing(400, 200)
    
    # Center box
    d.add(Rect(140, 90, 120, 40, fillColor=BG_GRAY, strokeColor=BLACK, strokeWidth=1.5))
    d.add(String(200, 115, 'USERS', fontSize=10, fontName='Helvetica-Bold', textAnchor='middle', fillColor=BLACK))
    d.add(String(200, 100, 'id, email, role', fontSize=7, textAnchor='middle', fillColor=GRAY))
    
    # Left box
    d.add(Rect(20, 90, 100, 40, fillColor=BG_GRAY, strokeColor=BLACK, strokeWidth=1.5))
    d.add(String(70, 115, 'DEALERSHIPS', fontSize=9, fontName='Helvetica-Bold', textAnchor='middle', fillColor=BLACK))
    d.add(String(70, 100, 'id, name', fontSize=7, textAnchor='middle', fillColor=GRAY))
    
    # Right top box
    d.add(Rect(280, 140, 100, 40, fillColor=BG_GRAY, strokeColor=BLACK, strokeWidth=1.5))
    d.add(String(330, 165, 'DOCUMENTS', fontSize=9, fontName='Helvetica-Bold', textAnchor='middle', fillColor=BLACK))
    d.add(String(330, 150, 'id, filename', fontSize=7, textAnchor='middle', fillColor=GRAY))
    
    # Right bottom box
    d.add(Rect(280, 40, 100, 40, fillColor=BG_GRAY, strokeColor=BLACK, strokeWidth=1.5))
    d.add(String(330, 65, 'TOKENS', fontSize=9, fontName='Helvetica-Bold', textAnchor='middle', fillColor=BLACK))
    d.add(String(330, 50, 'id, token', fontSize=7, textAnchor='middle', fillColor=GRAY))
    
    # Relationships
    d.add(Line(120, 110, 140, 110, strokeColor=BLACK, strokeWidth=1))
    d.add(Line(260, 110, 280, 160, strokeColor=BLACK, strokeWidth=1))
    d.add(Line(260, 110, 280, 60, strokeColor=BLACK, strokeWidth=1))
    
    return d

def generate_pdf():
    pdf_file = 'COMPLETE_PROJECT_DOCUMENTATION.pdf'
    
    doc = SimpleDocTemplate(pdf_file, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    
    styles = getSampleStyleSheet()
    
    title = ParagraphStyle('Title', parent=styles['Title'], fontSize=28, textColor=BLACK, spaceAfter=0.3*inch, alignment=TA_CENTER, fontName='Helvetica-Bold')
    h1 = ParagraphStyle('H1', parent=styles['Heading1'], fontSize=14, textColor=BLACK, spaceAfter=0.15*inch, spaceBefore=0.25*inch, fontName='Helvetica-Bold')
    h2 = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=11, textColor=BLACK, spaceAfter=0.1*inch, spaceBefore=0.15*inch, fontName='Helvetica-Bold')
    body = ParagraphStyle('Body', parent=styles['Normal'], fontSize=9, alignment=TA_JUSTIFY, spaceAfter=0.08*inch, leading=12)
    bullet = ParagraphStyle('Bullet', parent=styles['Normal'], fontSize=8, leftIndent=0.2*inch, spaceAfter=0.04*inch)
    
    story = []
    
    # Title
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph('Avatar Adam', title))
    story.append(Paragraph('Technical Documentation', h1))
    story.append(Spacer(1, 0.3*inch))
    
    # 1. Project Overview
    story.append(Paragraph('1. Project Overview', h1))
    story.append(Paragraph('Avatar Adam is an AI-powered conversational platform for automotive dealerships featuring real-time voice chat, intelligent text conversations, and document-based knowledge retrieval.', body))
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph('Core Features:', h2))
    for item in ['Real-time voice chat with AI avatars', 'Intelligent text chat (training & role-play)', 'Document knowledge base (RAG system)', 'Multi-tenant dealership management', 'Enterprise security (JWT, RBAC)']:
        story.append(Paragraph(f'• {item}', bullet))
    
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph('Key Metrics:', h2))
    for item in ['46 API endpoints', '7 external services', '5 database tables', '3 user roles', '100% backend test coverage']:
        story.append(Paragraph(f'• {item}', bullet))
    
    story.append(Spacer(1, 0.3*inch))
    
    # 2. System Architecture
    story.append(Paragraph('2. System Architecture', h1))
    story.append(Spacer(1, 0.1*inch))
    story.append(simple_arch_diagram())
    story.append(Spacer(1, 0.2*inch))
    
    story.append(Paragraph('Architecture Layers:', h2))
    for item in ['Frontend: React 18 handles user interface with 8 pages', 'Backend: FastAPI processes 46 API routes with 7 services', 'Database: PostgreSQL stores data, Pinecone handles vectors', 'AI Services: OpenRouter, OpenAI, ElevenLabs, HeyGen']:
        story.append(Paragraph(f'• {item}', bullet))
    
    story.append(Spacer(1, 0.3*inch))
    
    # 3. Technology Stack
    story.append(Paragraph('3. Technology Stack', h1))
    
    tech_data = [
        ['Component', 'Technology', 'Version'],
        ['Frontend', 'React + TypeScript', '18.2.0'],
        ['Backend', 'FastAPI', '0.115.0+'],
        ['Database', 'PostgreSQL', '16'],
        ['Vector DB', 'Pinecone', '5.0.0'],
        ['LLM', 'OpenRouter GPT-4o', 'Latest'],
        ['Voice', 'Whisper + ElevenLabs', 'Latest']
    ]
    
    tech_table = Table(tech_data, colWidths=[1.5*inch, 2*inch, 1.3*inch])
    tech_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BLACK),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('BACKGROUND', (0,1), (-1,-1), colors.white),
        ('FONTSIZE', (0,1), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, BLACK),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(tech_table)
    story.append(Spacer(1, 0.3*inch))
    
    # 4. Third-Party Services
    story.append(Paragraph('4. Third-Party Services', h1))
    
    services_data = [
        ['Service', 'Purpose'],
        ['OpenRouter', 'LLM (GPT-4o) for conversations'],
        ['OpenAI', 'Embeddings (1536-dim) & Whisper STT'],
        ['Pinecone', 'Vector database for semantic search'],
        ['ElevenLabs', 'Text-to-speech with natural voices'],
        ['HeyGen', 'AI avatar video generation'],
        ['Mailgun', 'Email delivery service'],
        ['PostgreSQL', 'Primary relational database']
    ]
    
    services_table = Table(services_data, colWidths=[1.5*inch, 3.3*inch])
    services_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BLACK),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('BACKGROUND', (0,1), (-1,-1), colors.white),
        ('FONTSIZE', (0,1), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, BLACK),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(services_table)
    story.append(Spacer(1, 0.3*inch))
    
    # 5. User Flows
    story.append(Paragraph('5. User Flows', h1))
    
    story.append(Paragraph('5.1 Authentication Flow', h2))
    story.append(Spacer(1, 0.1*inch))
    auth_steps = ['User enters email & password', 'Backend verifies credentials', 'Generate JWT tokens', 'Store tokens', 'Redirect to dashboard']
    story.append(simple_flow_diagram(auth_steps))
    story.append(Spacer(1, 0.3*inch))
    
    story.append(Paragraph('5.2 Chat Flow', h2))
    story.append(Spacer(1, 0.1*inch))
    chat_steps = ['User sends message', 'Search documents (RAG)', 'Retrieve relevant context', 'Send to LLM', 'Stream response']
    story.append(simple_flow_diagram(chat_steps))
    story.append(Spacer(1, 0.3*inch))
    
    story.append(Paragraph('5.3 Voice Flow', h2))
    story.append(Spacer(1, 0.1*inch))
    voice_steps = ['User speaks', 'Whisper STT', 'LLM processing', 'ElevenLabs TTS', 'Play audio']
    story.append(simple_flow_diagram(voice_steps))
    story.append(Spacer(1, 0.3*inch))
    
    # 6. API Endpoints
    story.append(Paragraph('6. API Endpoints', h1))
    
    api_data = [
        ['Endpoint', 'Method', 'Purpose'],
        ['/api/v1/auth/login', 'POST', 'User login'],
        ['/api/v1/auth/signup', 'POST', 'User registration'],
        ['/api/v1/auth/refresh', 'POST', 'Refresh token'],
        ['/api/v1/users', 'GET', 'List users'],
        ['/api/v1/users', 'POST', 'Create user'],
        ['/api/v1/chat/message', 'POST', 'Send message'],
        ['/api/v1/voice/ws', 'WebSocket', 'Voice chat'],
        ['/api/v1/rag/documents/upload', 'POST', 'Upload document'],
        ['/api/v1/rag/search', 'POST', 'Search documents'],
        ['/api/v1/dealerships', 'GET', 'List dealerships'],
        ['/api/v1/avatar/session', 'POST', 'Create avatar session']
    ]
    
    api_table = Table(api_data, colWidths=[2.2*inch, 0.8*inch, 1.8*inch])
    api_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BLACK),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('BACKGROUND', (0,1), (-1,-1), colors.white),
        ('FONTSIZE', (0,1), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, BLACK),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(api_table)
    story.append(Spacer(1, 0.3*inch))
    
    # 7. Database Schema
    story.append(Paragraph('7. Database Schema', h1))
    story.append(Spacer(1, 0.1*inch))
    story.append(simple_db_diagram())
    story.append(Spacer(1, 0.15*inch))
    
    # Concise schema overview
    schema_data = [
        ['Table', 'Key Fields', 'Purpose'],
        ['users', 'id, email, role, dealership_id', 'User authentication & RBAC'],
        ['dealerships', 'id, name, rag_enabled', 'Multi-tenant organization'],
        ['documents', 'id, dealership_id, filename', 'Uploaded documents metadata'],
        ['document_chunks', 'id, document_id, embedding', 'Text chunks with vectors'],
        ['refresh_tokens', 'id, user_id, token, expires_at', 'JWT token management']
    ]
    
    schema_table = Table(schema_data, colWidths=[1.3*inch, 1.9*inch, 1.6*inch])
    schema_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BLACK),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8),
        ('BACKGROUND', (0,1), (-1,-1), BG_GRAY),
        ('FONTSIZE', (0,1), (-1,-1), 7),
        ('GRID', (0,0), (-1,-1), 0.5, BLACK),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    
    story.append(Paragraph('Database Tables Overview:', h2))
    story.append(schema_table)
    story.append(Spacer(1, 0.1*inch))
    
    # Key details
    story.append(Paragraph('• All tables use UUID primary keys for security and scalability', body))
    story.append(Paragraph('• Users belong to Dealerships (multi-tenant architecture)', body))
    story.append(Paragraph('• Documents are chunked and embedded with 1536-dimension vectors', body))
    story.append(Paragraph('• Refresh tokens enable secure JWT token rotation (7-day expiry)', body))
    story.append(Spacer(1, 0.3*inch))
    
    # 8. Security
    story.append(Paragraph('8. Security Architecture', h1))
    
    sec_data = [
        ['Layer', 'Security Measure'],
        ['Client', 'JWT tokens in localStorage'],
        ['API Gateway', 'CORS + Rate limiting'],
        ['Authentication', 'JWT validation'],
        ['Authorization', 'Role-based access control'],
        ['Data', 'Bcrypt password hashing']
    ]
    
    sec_table = Table(sec_data, colWidths=[1.5*inch, 3.3*inch])
    sec_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BLACK),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('BACKGROUND', (0,1), (-1,-1), colors.white),
        ('FONTSIZE', (0,1), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, BLACK),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(sec_table)
    story.append(Spacer(1, 0.3*inch))
    
    # 9. File Structure
    story.append(Paragraph('9. File Structure', h1))
    
    backend_tree = [
        'backend/',
        '+-- app/',
        '    +-- main.py              # FastAPI app',
        '    +-- api/v1/              # API routes',
        '    +-- core/                # Config, DB, Security',
        '    +-- models/              # Database models',
        '    +-- schemas/             # Pydantic schemas',
        '    +-- services/            # Business logic',
        '    +-- middleware/          # CORS, Security',
        '+-- alembic/                 # Migrations',
        '+-- pyproject.toml           # Dependencies'
    ]
    
    tree_table = Table([[line] for line in backend_tree], colWidths=[5*inch])
    tree_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Courier'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('TEXTCOLOR', (0,0), (-1,-1), BLACK),
        ('BACKGROUND', (0,0), (-1,-1), BG_GRAY),
        ('BOX', (0,0), (-1,-1), 0.8, BLACK),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
    ]))
    
    story.append(Paragraph('Backend Structure:', h2))
    story.append(tree_table)
    story.append(Spacer(1, 0.15*inch))
    
    frontend_tree = [
        'frontend/',
        '+-- src/',
        '    +-- App.tsx             # Main app',
        '    +-- pages/              # Page components',
        '    +-- components/         # UI components',
        '    +-- context/            # Auth context',
        '    +-- hooks/              # Custom hooks',
        '    +-- services/           # API client',
        '+-- package.json            # Dependencies',
        '+-- vite.config.ts          # Build config'
    ]
    
    tree_table2 = Table([[line] for line in frontend_tree], colWidths=[5*inch])
    tree_table2.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Courier'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('TEXTCOLOR', (0,0), (-1,-1), BLACK),
        ('BACKGROUND', (0,0), (-1,-1), BG_GRAY),
        ('BOX', (0,0), (-1,-1), 0.8, BLACK),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
    ]))
    
    story.append(Paragraph('Frontend Structure:', h2))
    story.append(tree_table2)
    
    # Build
    doc.build(story, canvasmaker=SimpleCanvas)
    size = Path(pdf_file).stat().st_size / 1024
    print(f'✅ Simple, clean PDF created: {pdf_file}')
    print(f'📊 Size: {size:.1f} KB')

if __name__ == "__main__":
    print('='*60)
    print('  Avatar Adam - Simple Professional PDF')
    print('='*60)
    print()
    generate_pdf()
