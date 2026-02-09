#!/usr/bin/env python3
"""
Generate Clean Professional PDF - No Overlapping
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Circle
from pathlib import Path

# Colors
LIGHT_BLACK = colors.HexColor('#404040')
DARK_GRAY = colors.HexColor('#1f2937')
MED_GRAY = colors.HexColor('#6b7280')
LIGHT_GRAY = colors.HexColor('#e5e7eb')
VERY_LIGHT_GRAY = colors.HexColor('#f5f5f5')

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
            # No page numbers or headers - clean pages
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

def create_arch_diagram():
    """Clear and simple system architecture"""
    d = Drawing(400, 320)
    
    # Layer 1: Frontend
    d.add(Rect(50, 260, 300, 50, fillColor=VERY_LIGHT_GRAY, strokeColor=LIGHT_BLACK, strokeWidth=2))
    d.add(String(200, 295, 'FRONTEND', fontSize=11, fontName='Helvetica-Bold', textAnchor='middle', fillColor=DARK_GRAY))
    d.add(String(200, 280, 'React + TypeScript', fontSize=9, textAnchor='middle', fillColor=MED_GRAY))
    d.add(String(200, 267, 'UI Pages & Components', fontSize=8, textAnchor='middle', fillColor=MED_GRAY))
    
    # Arrow
    d.add(Line(200, 260, 200, 240, strokeColor=LIGHT_BLACK, strokeWidth=2))
    d.add(Line(195, 245, 200, 240, strokeColor=LIGHT_BLACK, strokeWidth=2))
    d.add(Line(205, 245, 200, 240, strokeColor=LIGHT_BLACK, strokeWidth=2))
    d.add(String(240, 248, 'HTTP/WebSocket', fontSize=7, fillColor=MED_GRAY))
    
    # Layer 2: Backend
    d.add(Rect(50, 175, 300, 65, fillColor=VERY_LIGHT_GRAY, strokeColor=LIGHT_BLACK, strokeWidth=2))
    d.add(String(200, 225, 'BACKEND', fontSize=11, fontName='Helvetica-Bold', textAnchor='middle', fillColor=DARK_GRAY))
    d.add(String(200, 210, 'FastAPI + Python', fontSize=9, textAnchor='middle', fillColor=MED_GRAY))
    d.add(String(200, 197, '46 API Routes', fontSize=8, textAnchor='middle', fillColor=MED_GRAY))
    d.add(String(200, 184, '7 Services | 3 Middleware', fontSize=7, textAnchor='middle', fillColor=MED_GRAY))
    
    # Arrow
    d.add(Line(200, 175, 200, 155, strokeColor=LIGHT_BLACK, strokeWidth=2))
    d.add(Line(195, 160, 200, 155, strokeColor=LIGHT_BLACK, strokeWidth=2))
    d.add(Line(205, 160, 200, 155, strokeColor=LIGHT_BLACK, strokeWidth=2))
    d.add(String(240, 163, 'Database Queries', fontSize=7, fillColor=MED_GRAY))
    
    # Layer 3: Data
    d.add(Rect(50, 100, 300, 55, fillColor=VERY_LIGHT_GRAY, strokeColor=LIGHT_BLACK, strokeWidth=2))
    d.add(String(200, 140, 'DATA STORAGE', fontSize=11, fontName='Helvetica-Bold', textAnchor='middle', fillColor=DARK_GRAY))
    d.add(String(200, 125, 'PostgreSQL + pgvector', fontSize=9, textAnchor='middle', fillColor=MED_GRAY))
    d.add(String(200, 112, 'Pinecone Vector Database', fontSize=8, textAnchor='middle', fillColor=MED_GRAY))
    
    # Arrow
    d.add(Line(200, 100, 200, 80, strokeColor=LIGHT_BLACK, strokeWidth=2))
    d.add(Line(195, 85, 200, 80, strokeColor=LIGHT_BLACK, strokeWidth=2))
    d.add(Line(205, 85, 200, 80, strokeColor=LIGHT_BLACK, strokeWidth=2))
    d.add(String(240, 88, 'API Calls', fontSize=7, fillColor=MED_GRAY))
    
    # Layer 4: External Services
    d.add(Rect(50, 10, 300, 70, fillColor=VERY_LIGHT_GRAY, strokeColor=LIGHT_BLACK, strokeWidth=2))
    d.add(String(200, 65, 'EXTERNAL SERVICES', fontSize=11, fontName='Helvetica-Bold', textAnchor='middle', fillColor=DARK_GRAY))
    d.add(String(200, 50, 'OpenRouter (GPT-4o)', fontSize=8, textAnchor='middle', fillColor=MED_GRAY))
    d.add(String(200, 38, 'OpenAI | Pinecone | ElevenLabs', fontSize=7, textAnchor='middle', fillColor=MED_GRAY))
    d.add(String(200, 26, 'HeyGen | Mailgun', fontSize=7, textAnchor='middle', fillColor=MED_GRAY))
    d.add(String(200, 15, '7 AI/ML Services', fontSize=7, textAnchor='middle', fillColor=MED_GRAY))
    
    return d

def create_flow_diagram(title, steps):
    """Vertical flow - compact"""
    box_height = 25
    arrow_height = 15
    total_height = len(steps) * (box_height + arrow_height) + 40
    d = Drawing(380, total_height)
    
    y = total_height - 30
    d.add(String(190, y, title, fontSize=10, fontName='Helvetica-Bold', textAnchor='middle', fillColor=DARK_GRAY))
    y -= 35
    
    for i, step in enumerate(steps):
        d.add(Rect(40, y, 300, box_height, fillColor=VERY_LIGHT_GRAY, strokeColor=LIGHT_BLACK, strokeWidth=1))
        d.add(String(50, y+10, f'{i+1}. {step}', fontSize=8, fillColor=DARK_GRAY))
        
        if i < len(steps) - 1:
            arrow_y = y - arrow_height
            d.add(Line(190, y, 190, arrow_y, strokeColor=LIGHT_BLACK, strokeWidth=1.5))
            d.add(Line(186, arrow_y+4, 190, arrow_y, strokeColor=LIGHT_BLACK, strokeWidth=1.5))
            d.add(Line(194, arrow_y+4, 190, arrow_y, strokeColor=LIGHT_BLACK, strokeWidth=1.5))
        
        y -= (box_height + arrow_height)
    
    return d

def create_voice_diagram():
    """Voice flow - horizontal"""
    d = Drawing(420, 140)
    
    components = [
        ('User\nSpeaks', 40),
        ('Whisper\nSTT', 110),
        ('LLM', 180),
        ('ElevenLabs\nTTS', 250),
        ('HeyGen\nAvatar', 320),
        ('User\nHears', 390)
    ]
    
    y = 70
    for i, (label, x) in enumerate(components):
        d.add(Circle(x, y, 22, fillColor=VERY_LIGHT_GRAY, strokeColor=LIGHT_BLACK, strokeWidth=1.5))
        lines = label.split('\n')
        for j, line in enumerate(lines):
            d.add(String(x, y+5-j*9, line, fontSize=7, fontName='Helvetica-Bold', textAnchor='middle', fillColor=DARK_GRAY))
        
        if i < len(components) - 1:
            next_x = components[i+1][1]
            d.add(Line(x+22, y, next_x-22, y, strokeColor=LIGHT_BLACK, strokeWidth=1.5))
            d.add(Line(next_x-26, y+3, next_x-22, y, strokeColor=LIGHT_BLACK, strokeWidth=1.5))
            d.add(Line(next_x-26, y-3, next_x-22, y, strokeColor=LIGHT_BLACK, strokeWidth=1.5))
    
    # Labels
    labels = [('Audio', 75), ('Text', 145), ('Response', 215), ('Audio', 285), ('Video', 355)]
    for label, x in labels:
        d.add(String(x, 100, label, fontSize=7, fillColor=MED_GRAY, textAnchor='middle'))
    
    return d

def create_rag_diagram():
    """RAG flow - dual path"""
    d = Drawing(420, 240)
    
    # Upload path
    upload_steps = [('Upload\nDoc', 60, 200), ('Extract\nText', 60, 150), ('Chunk\nText', 60, 100), ('Generate\nEmbedding', 60, 50)]
    
    for i, (label, x, y) in enumerate(upload_steps):
        d.add(Rect(x-35, y-15, 70, 30, fillColor=VERY_LIGHT_GRAY, strokeColor=LIGHT_BLACK, strokeWidth=1))
        lines = label.split('\n')
        for j, line in enumerate(lines):
            d.add(String(x, y+5-j*10, line, fontSize=7, textAnchor='middle', fillColor=DARK_GRAY))
        
        if i < len(upload_steps) - 1:
            d.add(Line(x, y-15, x, y-25, strokeColor=LIGHT_BLACK, strokeWidth=1.5))
            d.add(Line(x-3, y-21, x, y-25, strokeColor=LIGHT_BLACK, strokeWidth=1.5))
            d.add(Line(x+3, y-21, x, y-25, strokeColor=LIGHT_BLACK, strokeWidth=1.5))
    
    # Query path
    query_steps = [('User\nQuery', 280, 200), ('Generate\nEmbedding', 280, 150), ('Search\nPinecone', 280, 100), ('Retrieve\nChunks', 280, 50)]
    
    for i, (label, x, y) in enumerate(query_steps):
        d.add(Rect(x-35, y-15, 70, 30, fillColor=VERY_LIGHT_GRAY, strokeColor=LIGHT_BLACK, strokeWidth=1))
        lines = label.split('\n')
        for j, line in enumerate(lines):
            d.add(String(x, y+5-j*10, line, fontSize=7, textAnchor='middle', fillColor=DARK_GRAY))
        
        if i < len(query_steps) - 1:
            d.add(Line(x, y-15, x, y-25, strokeColor=LIGHT_BLACK, strokeWidth=1.5))
            d.add(Line(x-3, y-21, x, y-25, strokeColor=LIGHT_BLACK, strokeWidth=1.5))
            d.add(Line(x+3, y-21, x, y-25, strokeColor=LIGHT_BLACK, strokeWidth=1.5))
    
    # Connection
    d.add(Line(95, 35, 245, 35, strokeColor=LIGHT_BLACK, strokeWidth=1, strokeDashArray=[3,3]))
    d.add(String(170, 40, 'indexed', fontSize=7, fillColor=MED_GRAY, textAnchor='middle'))
    
    # Labels
    d.add(String(60, 220, 'Upload Path', fontSize=9, fontName='Helvetica-Bold', textAnchor='middle', fillColor=DARK_GRAY))
    d.add(String(280, 220, 'Query Path', fontSize=9, fontName='Helvetica-Bold', textAnchor='middle', fillColor=DARK_GRAY))
    
    return d

def create_db_diagram():
    """Simple clean database schema"""
    d = Drawing(400, 180)
    
    # Row 1: USERS and DEALERSHIPS
    d.add(Rect(30, 130, 130, 35, fillColor=VERY_LIGHT_GRAY, strokeColor=LIGHT_BLACK, strokeWidth=1.5))
    d.add(String(95, 152, 'USERS', fontSize=10, fontName='Helvetica-Bold', textAnchor='middle', fillColor=DARK_GRAY))
    d.add(String(95, 138, 'Auth & Roles', fontSize=7, textAnchor='middle', fillColor=MED_GRAY))
    
    d.add(Rect(240, 130, 130, 35, fillColor=VERY_LIGHT_GRAY, strokeColor=LIGHT_BLACK, strokeWidth=1.5))
    d.add(String(305, 152, 'DEALERSHIPS', fontSize=10, fontName='Helvetica-Bold', textAnchor='middle', fillColor=DARK_GRAY))
    d.add(String(305, 138, 'Multi-tenant', fontSize=7, textAnchor='middle', fillColor=MED_GRAY))
    
    # Row 2: DOCUMENTS
    d.add(Rect(240, 70, 130, 35, fillColor=VERY_LIGHT_GRAY, strokeColor=LIGHT_BLACK, strokeWidth=1.5))
    d.add(String(305, 92, 'DOCUMENTS', fontSize=10, fontName='Helvetica-Bold', textAnchor='middle', fillColor=DARK_GRAY))
    d.add(String(305, 78, 'Files Metadata', fontSize=7, textAnchor='middle', fillColor=MED_GRAY))
    
    # Row 3: REFRESH_TOKENS and DOCUMENT_CHUNKS
    d.add(Rect(30, 10, 130, 35, fillColor=VERY_LIGHT_GRAY, strokeColor=LIGHT_BLACK, strokeWidth=1.5))
    d.add(String(95, 32, 'REFRESH_TOKENS', fontSize=9, fontName='Helvetica-Bold', textAnchor='middle', fillColor=DARK_GRAY))
    d.add(String(95, 18, 'JWT Tokens', fontSize=7, textAnchor='middle', fillColor=MED_GRAY))
    
    d.add(Rect(240, 10, 130, 35, fillColor=VERY_LIGHT_GRAY, strokeColor=LIGHT_BLACK, strokeWidth=1.5))
    d.add(String(305, 32, 'DOC_CHUNKS', fontSize=9, fontName='Helvetica-Bold', textAnchor='middle', fillColor=DARK_GRAY))
    d.add(String(305, 18, 'Text + Vectors', fontSize=7, textAnchor='middle', fillColor=MED_GRAY))
    
    # Clean arrows
    # USERS → DEALERSHIPS
    d.add(Line(160, 147, 240, 147, strokeColor=LIGHT_BLACK, strokeWidth=1.5))
    d.add(Line(235, 150, 240, 147, strokeColor=LIGHT_BLACK, strokeWidth=1.5))
    d.add(Line(235, 144, 240, 147, strokeColor=LIGHT_BLACK, strokeWidth=1.5))
    d.add(String(200, 152, 'belongs to', fontSize=7, fillColor=MED_GRAY))
    
    # USERS → REFRESH_TOKENS
    d.add(Line(95, 130, 95, 45, strokeColor=LIGHT_BLACK, strokeWidth=1.5))
    d.add(Line(92, 50, 95, 45, strokeColor=LIGHT_BLACK, strokeWidth=1.5))
    d.add(Line(98, 50, 95, 45, strokeColor=LIGHT_BLACK, strokeWidth=1.5))
    d.add(String(105, 87, 'has', fontSize=7, fillColor=MED_GRAY))
    
    # DEALERSHIPS → DOCUMENTS
    d.add(Line(305, 130, 305, 105, strokeColor=LIGHT_BLACK, strokeWidth=1.5))
    d.add(Line(302, 110, 305, 105, strokeColor=LIGHT_BLACK, strokeWidth=1.5))
    d.add(Line(308, 110, 305, 105, strokeColor=LIGHT_BLACK, strokeWidth=1.5))
    d.add(String(315, 117, 'owns', fontSize=7, fillColor=MED_GRAY))
    
    # DOCUMENTS → DOC_CHUNKS
    d.add(Line(305, 70, 305, 45, strokeColor=LIGHT_BLACK, strokeWidth=1.5))
    d.add(Line(302, 50, 305, 45, strokeColor=LIGHT_BLACK, strokeWidth=1.5))
    d.add(Line(308, 50, 305, 45, strokeColor=LIGHT_BLACK, strokeWidth=1.5))
    d.add(String(315, 57, 'contains', fontSize=7, fillColor=MED_GRAY))
    
    return d

def create_security_diagram():
    """Security layers - compact"""
    d = Drawing(380, 260)
    
    layers = [
        ('Client Layer', 'Browser, Tokens', 220),
        ('API Gateway', 'CORS, Rate Limit', 180),
        ('Authentication', 'JWT Validation', 140),
        ('Authorization', 'RBAC', 100),
        ('Application', 'API Routes', 60),
        ('Data Security', 'Encryption', 20)
    ]
    
    for i, (name, desc, y) in enumerate(layers):
        d.add(Rect(40, y, 300, 35, fillColor=VERY_LIGHT_GRAY, strokeColor=LIGHT_BLACK, strokeWidth=1))
        d.add(String(190, y+22, name, fontSize=8, fontName='Helvetica-Bold', textAnchor='middle', fillColor=DARK_GRAY))
        d.add(String(190, y+10, desc, fontSize=7, textAnchor='middle', fillColor=MED_GRAY))
        
        if i < len(layers) - 1:
            d.add(Line(190, y, 190, y-5, strokeColor=LIGHT_BLACK, strokeWidth=1.5))
            d.add(Line(186, y-1, 190, y-5, strokeColor=LIGHT_BLACK, strokeWidth=1.5))
            d.add(Line(194, y-1, 190, y-5, strokeColor=LIGHT_BLACK, strokeWidth=1.5))
    
    return d

def generate_pdf():
    pdf_file = 'COMPLETE_PROJECT_DOCUMENTATION.pdf'
    
    doc = SimpleDocTemplate(
        pdf_file, 
        pagesize=A4, 
        rightMargin=2*cm, 
        leftMargin=2*cm, 
        topMargin=2.5*cm, 
        bottomMargin=2.5*cm,
        title='Avatar Adam - Technical Documentation',
        author='Development Team',
        subject='AI-Powered Conversational Platform Documentation'
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Title'], fontSize=28, textColor=DARK_GRAY, spaceAfter=0.15*inch, alignment=TA_CENTER, fontName='Helvetica-Bold')
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Heading2'], fontSize=13, textColor=MED_GRAY, spaceAfter=0.25*inch, alignment=TA_CENTER)
    h1_style = ParagraphStyle('H1', parent=styles['Heading1'], fontSize=14, textColor=DARK_GRAY, spaceAfter=0.1*inch, spaceBefore=0.15*inch, fontName='Helvetica-Bold')
    h2_style = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=11, textColor=DARK_GRAY, spaceAfter=0.08*inch, spaceBefore=0.12*inch, fontName='Helvetica-Bold')
    h3_style = ParagraphStyle('H3', parent=styles['Heading3'], fontSize=9, textColor=MED_GRAY, spaceAfter=0.05*inch, spaceBefore=0.08*inch, fontName='Helvetica-Bold')
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=9, alignment=TA_JUSTIFY, spaceAfter=0.05*inch, leading=11)
    bullet_style = ParagraphStyle('Bullet', parent=styles['Normal'], fontSize=8, leftIndent=0.2*inch, spaceAfter=0.03*inch, leading=10)
    
    story = []
    
    # Title (no cover page)
    story.append(Paragraph('Avatar Adam', title_style))
    story.append(Paragraph('Technical Documentation', subtitle_style))
    story.append(Spacer(1, 0.15*inch))
    
    # 1. Project Information
    story.append(Paragraph('1. Project Information', h1_style))
    
    story.append(Paragraph('Avatar Adam is an enterprise AI conversational platform for automotive dealerships, combining real-time voice chat, intelligent text conversations, and document-based knowledge retrieval.', body_style))
    story.append(Spacer(1, 0.12*inch))
    
    story.append(Paragraph('Core Features:', h3_style))
    for feature in ['Real-time voice chat with AI avatars', 'Intelligent text chat (training & role-play)', 'RAG system with document knowledge base', 'Multi-tenant dealership management', 'Enterprise security (JWT, RBAC)']:
        story.append(Paragraph(f'• {feature}', bullet_style))
    
    story.append(Spacer(1, 0.1*inch))
    
    # 2. System Architecture
    story.append(Paragraph('2. System Architecture', h1_style))
    story.append(Paragraph('2.1 Architecture Overview', h2_style))
    story.append(Spacer(1, 0.08*inch))
    story.append(create_arch_diagram())
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph('Architecture Explanation:', h3_style))
    for point in [
        'Layer 1: React frontend with 8 pages and WebSocket client.',
        'Layer 2: FastAPI backend with 46 routes and 7 services.',
        'Layer 3: PostgreSQL (5 tables) and Pinecone (vectors).',
        'Layer 4: AI/ML services (OpenRouter, OpenAI, ElevenLabs, HeyGen).'
    ]:
        story.append(Paragraph(f'• {point}', bullet_style))
    
    story.append(Spacer(1, 0.12*inch))
    
    # 3. Technology Stack
    story.append(Paragraph('3. Technology Stack', h1_style))
    
    tech_data = [
        ['Component', 'Technology', 'Version'],
        ['Frontend', 'React + TypeScript', '18.2.0'],
        ['Backend', 'FastAPI', '0.115.0+'],
        ['Database', 'PostgreSQL + pgvector', '16'],
        ['Vector DB', 'Pinecone', '5.0.0'],
        ['LLM', 'OpenRouter (GPT-4o)', 'Latest'],
        ['Voice', 'Whisper + ElevenLabs', 'Latest']
    ]
    
    tech_table = Table(tech_data, colWidths=[1.5*inch, 2.2*inch, 1.3*inch])
    tech_table.setStyle(TableStyle([
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
    story.append(tech_table)
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph('Stack Rationale:', h3_style))
    story.append(Paragraph('Technologies selected for performance and scalability: React 18 for modern UI, FastAPI for async operations, PostgreSQL 16 with pgvector for unified data storage, and Pinecone for managed vector search. This combination delivers sub-200ms API responses and supports 100+ concurrent users.', body_style))
    story.append(Spacer(1, 0.08*inch))
    
    story.append(Paragraph('Key Benefits:', h3_style))
    story.append(Paragraph('The technology stack is carefully selected for performance, scalability, and developer productivity. React with TypeScript ensures type-safe frontend development, while FastAPI provides high-performance async backend operations. PostgreSQL with pgvector extension eliminates the need for separate vector databases for relational data, and Pinecone offers managed vector search at scale.', body_style))
    story.append(Spacer(1, 0.08*inch))
    
    story.append(Paragraph('Key Technology Benefits:', h3_style))
    story.append(Paragraph('• Frontend: React 18 with TypeScript provides type safety and modern component architecture. Vite offers lightning-fast builds and hot module replacement for efficient development.', bullet_style))
    story.append(Paragraph('• Backend: FastAPI is chosen for its high performance, automatic API documentation, and native async support, making it ideal for real-time applications.', bullet_style))
    story.append(Paragraph('• Database: PostgreSQL 16 with pgvector extension enables both relational data storage and vector operations for semantic search in a single database.', bullet_style))
    story.append(Paragraph('• Vector DB: Pinecone provides managed vector database with automatic scaling, making it perfect for production RAG systems.', bullet_style))
    story.append(Paragraph('• LLM: OpenRouter with GPT-4o offers state-of-the-art language understanding and generation with cost-effective API access.', bullet_style))
    story.append(Paragraph('• Voice: Whisper provides industry-leading speech recognition, while ElevenLabs delivers natural-sounding text-to-speech with multiple voice options.', bullet_style))
    
    story.append(Spacer(1, 0.15*inch))
    
    # 4. Third-Party Services
    story.append(Paragraph('4. Third-Party Services', h1_style))
    
    services_data = [
        ['Service', 'Purpose', 'Integration'],
        ['OpenRouter', 'LLM (GPT-4o)', 'LLMService'],
        ['OpenAI', 'Embeddings & STT', 'RAGService, VoiceService'],
        ['Pinecone', 'Vector Database', 'RAGService'],
        ['ElevenLabs', 'Text-to-Speech', 'VoiceService, RealtimeVoiceService'],
        ['HeyGen', 'Avatar Video', 'AvatarService'],
        ['Mailgun', 'Email', 'EmailService'],
        ['PostgreSQL', 'Primary Database', 'Database Layer']
    ]
    
    services_table = Table(services_data, colWidths=[1.4*inch, 1.9*inch, 1.7*inch])
    services_table.setStyle(TableStyle([
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
    story.append(services_table)
    story.append(Spacer(1, 0.15*inch))
    
    # Additional Components
    story.append(Paragraph('4.1 Additional Components', h2_style))
    
    components_data = [
        ['Component', 'Technology', 'Purpose'],
        ['Caching', 'RAG Cache Service', 'Multi-level in-memory caching'],
        ['WebSocket', 'websockets 12.0', 'Real-time voice streaming'],
        ['Middleware', 'CORS, Security, Rate Limit', 'Request processing'],
        ['Docker', 'Docker Compose', 'Containerization'],
        ['Migrations', 'Alembic', 'Database versioning'],
        ['Document Processing', 'pypdf, python-docx', 'PDF/DOCX extraction']
    ]
    
    components_table = Table(components_data, colWidths=[1.4*inch, 1.9*inch, 1.7*inch])
    components_table.setStyle(TableStyle([
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
    story.append(components_table)
    story.append(Spacer(1, 0.12*inch))
    
    story.append(Paragraph('Integration Architecture:', h3_style))
    story.append(Paragraph('The platform integrates 7 core services with 6 additional components to create a cohesive system. RAG Cache Service implements intelligent 3-level caching to reduce external API calls by 70%. WebSocket support enables real-time voice streaming with sub-second latency. Docker Compose orchestrates PostgreSQL and backend services for consistent deployment across environments.', body_style))
    story.append(Spacer(1, 0.08*inch))
    
    story.append(Paragraph('Component Details:', h3_style))
    story.append(Paragraph('• RAG Cache: 3-level in-memory caching reduces API calls by 70%.', bullet_style))
    story.append(Paragraph('• WebSocket: Real-time voice chat with low-latency streaming.', bullet_style))
    story.append(Paragraph('• Middleware: CORS, Security Headers, and Rate Limiting protection.', bullet_style))
    story.append(Paragraph('• Docker: Containerized PostgreSQL and FastAPI with health checks.', bullet_style))
    
    story.append(Spacer(1, 0.15*inch))
    
    # 5. User Flows
    story.append(Paragraph('5. User Flows', h1_style))
    
    story.append(Paragraph('5.1 Authentication Flow', h2_style))
    story.append(Spacer(1, 0.08*inch))
    auth_steps = ['User enters credentials', 'POST /api/v1/auth/login', 'Verify password', 'Generate JWT tokens', 'Store tokens', 'Redirect to Dashboard']
    story.append(create_flow_diagram('Authentication', auth_steps))
    story.append(Spacer(1, 0.15*inch))
    
    story.append(Paragraph('Explanation:', h3_style))
    story.append(Paragraph('• User login verified with bcrypt, JWT tokens generated (30min/7day).', bullet_style))
    
    story.append(Spacer(1, 0.15*inch))
    
    story.append(Paragraph('5.2 Chat Flow with RAG', h2_style))
    story.append(Spacer(1, 0.08*inch))
    chat_steps = ['User enters message', 'POST /api/v1/chat/message', 'Generate embedding', 'Search Pinecone', 'Retrieve chunks', 'Add to LLM context', 'Stream response']
    story.append(create_flow_diagram('Chat Process', chat_steps))
    story.append(Spacer(1, 0.15*inch))
    
    story.append(Paragraph('Explanation:', h3_style))
    story.append(Paragraph('• Message embedded, Pinecone searches top 5 chunks, GPT-4o generates contextual response.', bullet_style))
    
    story.append(Spacer(1, 0.15*inch))
    
    story.append(Paragraph('5.3 Voice Chat Flow', h2_style))
    story.append(Spacer(1, 0.08*inch))
    story.append(create_voice_diagram())
    story.append(Spacer(1, 0.15*inch))
    
    story.append(Paragraph('Explanation:', h3_style))
    story.append(Paragraph('• Real-time pipeline: Audio → Whisper STT → LLM → ElevenLabs TTS → HeyGen Avatar.', bullet_style))
    
    story.append(Spacer(1, 0.15*inch))
    
    story.append(Paragraph('5.4 RAG Document Processing', h2_style))
    story.append(Spacer(1, 0.08*inch))
    story.append(create_rag_diagram())
    story.append(Spacer(1, 0.15*inch))
    
    story.append(Paragraph('Explanation:', h3_style))
    story.append(Paragraph('• Upload → Extract → Chunk (1000 chars) → Embed (OpenAI) → Store (Pinecone) → Query (Semantic Search).', bullet_style))
    
    story.append(Spacer(1, 0.15*inch))
    
    # 6. API Endpoints
    story.append(Paragraph('6. API Endpoints Reference', h1_style))
    
    endpoints_data = [
        ['Endpoint', 'Method', 'Auth', 'Purpose'],
        ['/api/v1/auth/login', 'POST', 'No', 'User login'],
        ['/api/v1/auth/signup', 'POST', 'No', 'Registration'],
        ['/api/v1/auth/refresh', 'POST', 'Refresh', 'Refresh token'],
        ['/api/v1/auth/me', 'GET', 'Yes', 'Get user'],
        ['/api/v1/users', 'GET', 'Yes', 'List users'],
        ['/api/v1/users', 'POST', 'Admin', 'Create user'],
        ['/api/v1/users/{id}', 'PATCH', 'Admin', 'Update user'],
        ['/api/v1/chat/message', 'POST', 'Yes', 'Send message'],
        ['/api/v1/voice/ws', 'WS', 'Yes', 'Voice chat'],
        ['/api/v1/rag/documents/upload', 'POST', 'Admin', 'Upload doc'],
        ['/api/v1/rag/documents', 'GET', 'Yes', 'List docs'],
        ['/api/v1/rag/search', 'POST', 'Yes', 'Search'],
        ['/api/v1/dealerships', 'GET', 'Yes', 'List dealerships'],
        ['/api/v1/avatar/session', 'POST', 'Yes', 'Create avatar']
    ]
    
    endpoints_table = Table(endpoints_data, colWidths=[2.1*inch, 0.6*inch, 0.6*inch, 1.7*inch])
    endpoints_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), LIGHT_BLACK),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8),
        ('BACKGROUND', (0,1), (-1,-1), colors.white),
        ('FONTSIZE', (0,1), (-1,-1), 7),
        ('GRID', (0,0), (-1,-1), 0.5, LIGHT_BLACK),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(endpoints_table)
    story.append(Spacer(1, 0.15*inch))
    
    story.append(Paragraph('6.1 Request/Response Examples', h2_style))
    
    # Login Example
    story.append(Paragraph('POST /api/v1/auth/login - User Authentication', h3_style))
    story.append(Paragraph('<font face="Courier" size="7">Request Body:</font>', body_style))
    story.append(Paragraph('<font face="Courier" size="7">  {"email": "admin@avataradam.com", "password": "Admin123!@#"}</font>', body_style))
    story.append(Paragraph('<font face="Courier" size="7">Response (200 OK):</font>', body_style))
    story.append(Paragraph('<font face="Courier" size="7">  {"access_token": "eyJhbG...", "refresh_token": "eyJhbG...", "token_type": "bearer",</font>', body_style))
    story.append(Paragraph('<font face="Courier" size="7">   "user": {"id": "uuid", "email": "admin@avataradam.com", "role": "super_admin"}}</font>', body_style))
    story.append(Spacer(1, 0.1*inch))
    
    # Get Current User
    story.append(Paragraph('GET /api/v1/auth/me - Get Current User', h3_style))
    story.append(Paragraph('<font face="Courier" size="7">Headers: Authorization: Bearer {access_token}</font>', body_style))
    story.append(Paragraph('<font face="Courier" size="7">Response (200 OK):</font>', body_style))
    story.append(Paragraph('<font face="Courier" size="7">  {"id": "uuid", "email": "user@example.com", "full_name": "John Doe",</font>', body_style))
    story.append(Paragraph('<font face="Courier" size="7">   "role": "user", "dealership_id": "uuid", "is_active": true}</font>', body_style))
    story.append(Spacer(1, 0.1*inch))
    
    # Create User
    story.append(Paragraph('POST /api/v1/users - Create User (Admin Only)', h3_style))
    story.append(Paragraph('<font face="Courier" size="7">Request Body:</font>', body_style))
    story.append(Paragraph('<font face="Courier" size="7">  {"email": "newuser@example.com", "password": "Pass123!", "full_name": "Jane Doe",</font>', body_style))
    story.append(Paragraph('<font face="Courier" size="7">   "role": "user", "dealership_id": "uuid"}</font>', body_style))
    story.append(Paragraph('<font face="Courier" size="7">Response (201 Created):</font>', body_style))
    story.append(Paragraph('<font face="Courier" size="7">  {"id": "uuid", "email": "newuser@example.com", "full_name": "Jane Doe", "role": "user"}</font>', body_style))
    story.append(Spacer(1, 0.1*inch))
    
    # Chat Example
    story.append(Paragraph('POST /api/v1/chat/message - Send Chat Message', h3_style))
    story.append(Paragraph('<font face="Courier" size="7">Request Body:</font>', body_style))
    story.append(Paragraph('<font face="Courier" size="7">  {"message": "What is the price of 2024 Honda Civic?", "mode": "training",</font>', body_style))
    story.append(Paragraph('<font face="Courier" size="7">   "dealership_id": "uuid"}</font>', body_style))
    story.append(Paragraph('<font face="Courier" size="7">Response (200 OK):</font>', body_style))
    story.append(Paragraph('<font face="Courier" size="7">  {"id": "uuid", "user_message": "What is the price...", "assistant_response": "The 2024</font>', body_style))
    story.append(Paragraph('<font face="Courier" size="7">   Honda Civic starts at $28,000...", "mode": "training", "created_at": "2026-02-09T..."}</font>', body_style))
    story.append(Spacer(1, 0.1*inch))
    
    # RAG Upload Example
    story.append(Paragraph('POST /api/v1/rag/documents/upload - Upload Document', h3_style))
    story.append(Paragraph('<font face="Courier" size="7">Content-Type: multipart/form-data</font>', body_style))
    story.append(Paragraph('<font face="Courier" size="7">Fields: file (PDF/DOCX), dealership_id (UUID)</font>', body_style))
    story.append(Paragraph('<font face="Courier" size="7">Response (201 Created):</font>', body_style))
    story.append(Paragraph('<font face="Courier" size="7">  {"id": "uuid", "filename": "inventory.pdf", "size": 102400, "chunks_count": 15,</font>', body_style))
    story.append(Paragraph('<font face="Courier" size="7">   "status": "processing", "created_at": "2026-02-09T..."}</font>', body_style))
    story.append(Spacer(1, 0.1*inch))
    
    # RAG Search Example
    story.append(Paragraph('POST /api/v1/rag/search - Semantic Search', h3_style))
    story.append(Paragraph('<font face="Courier" size="7">Request Body:</font>', body_style))
    story.append(Paragraph('<font face="Courier" size="7">  {"query": "Honda Civic features", "dealership_id": "uuid", "top_k": 5}</font>', body_style))
    story.append(Paragraph('<font face="Courier" size="7">Response (200 OK):</font>', body_style))
    story.append(Paragraph('<font face="Courier" size="7">  {"results": [{"chunk_id": "uuid", "content": "The 2024 Honda Civic features...",</font>', body_style))
    story.append(Paragraph('<font face="Courier" size="7">   "score": 0.95, "document_id": "uuid"}]}</font>', body_style))
    story.append(Spacer(1, 0.12*inch))
    
    story.append(Paragraph('6.2 Authentication & Authorization', h2_style))
    story.append(Paragraph('• All endpoints require JWT token except /auth/login and /auth/signup', bullet_style))
    story.append(Paragraph('• Header format: Authorization: Bearer {access_token}', bullet_style))
    story.append(Paragraph('• Access tokens expire in 30 minutes, refresh tokens in 7 days', bullet_style))
    story.append(Paragraph('• Admin endpoints (POST, PATCH, DELETE) require super_admin or dealership_admin role', bullet_style))
    story.append(Paragraph('• 401 Unauthorized returned for invalid/expired tokens', bullet_style))
    story.append(Paragraph('• 403 Forbidden returned for insufficient permissions', bullet_style))
    
    story.append(Spacer(1, 0.15*inch))
    
    story.append(Paragraph('6.3 Error Responses', h2_style))
    story.append(Paragraph('• 400 Bad Request: Invalid input data or validation errors', bullet_style))
    story.append(Paragraph('• 401 Unauthorized: Missing or invalid authentication token', bullet_style))
    story.append(Paragraph('• 403 Forbidden: Insufficient permissions for the requested resource', bullet_style))
    story.append(Paragraph('• 404 Not Found: Requested resource does not exist', bullet_style))
    story.append(Paragraph('• 429 Too Many Requests: Rate limit exceeded', bullet_style))
    story.append(Paragraph('• 500 Internal Server Error: Server-side error occurred', bullet_style))
    
    story.append(Spacer(1, 0.15*inch))
    
    # 7. Database Schema
    story.append(Paragraph('7. Database Schema', h1_style))
    story.append(Paragraph('7.1 Schema Overview', h2_style))
    story.append(Spacer(1, 0.08*inch))
    story.append(create_db_diagram())
    story.append(Spacer(1, 0.15*inch))
    
    story.append(Paragraph('Schema Explanation:', h3_style))
    story.append(Paragraph('• Relationships: Users belong to Dealerships, have Refresh Tokens. Dealerships own Documents containing Chunks with embeddings.', bullet_style))
    
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph('7.2 Table Details', h2_style))
    
    # Users table
    users_data = [
        ['Field', 'Type', 'Constraints'],
        ['id', 'UUID', 'PRIMARY KEY'],
        ['email', 'VARCHAR(255)', 'UNIQUE, NOT NULL'],
        ['full_name', 'VARCHAR(255)', ''],
        ['hashed_password', 'VARCHAR(255)', 'NOT NULL'],
        ['role', 'VARCHAR(50)', 'NOT NULL'],
        ['dealership_id', 'UUID', 'FOREIGN KEY'],
        ['is_active', 'BOOLEAN', 'DEFAULT TRUE'],
        ['created_at', 'TIMESTAMP', 'DEFAULT NOW()']
    ]
    
    users_table = Table(users_data, colWidths=[1.6*inch, 1.4*inch, 2*inch])
    users_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), LIGHT_BLACK),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8),
        ('BACKGROUND', (0,1), (-1,-1), VERY_LIGHT_GRAY),
        ('FONTSIZE', (0,1), (-1,-1), 7),
        ('GRID', (0,0), (-1,-1), 0.5, LIGHT_BLACK),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    
    story.append(Paragraph('Users Table:', h3_style))
    story.append(users_table)
    story.append(Spacer(1, 0.15*inch))
    
    # Dealerships table
    deal_data = [
        ['Field', 'Type', 'Constraints'],
        ['id', 'UUID', 'PRIMARY KEY'],
        ['name', 'VARCHAR(255)', 'NOT NULL'],
        ['location', 'VARCHAR(255)', ''],
        ['rag_enabled', 'BOOLEAN', 'DEFAULT TRUE'],
        ['created_at', 'TIMESTAMP', 'DEFAULT NOW()']
    ]
    
    deal_table = Table(deal_data, colWidths=[1.6*inch, 1.4*inch, 2*inch])
    deal_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), LIGHT_BLACK),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8),
        ('BACKGROUND', (0,1), (-1,-1), VERY_LIGHT_GRAY),
        ('FONTSIZE', (0,1), (-1,-1), 7),
        ('GRID', (0,0), (-1,-1), 0.5, LIGHT_BLACK),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    
    story.append(Paragraph('Dealerships Table:', h3_style))
    story.append(deal_table)
    story.append(Spacer(1, 0.15*inch))
    
    # Documents table
    doc_data = [
        ['Field', 'Type', 'Constraints'],
        ['id', 'UUID', 'PRIMARY KEY'],
        ['dealership_id', 'UUID', 'FOREIGN KEY'],
        ['filename', 'VARCHAR(255)', 'NOT NULL'],
        ['file_size', 'INTEGER', ''],
        ['status', 'VARCHAR(50)', ''],
        ['chunks_count', 'INTEGER', 'DEFAULT 0']
    ]
    
    doc_table = Table(doc_data, colWidths=[1.6*inch, 1.4*inch, 2*inch])
    doc_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), LIGHT_BLACK),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8),
        ('BACKGROUND', (0,1), (-1,-1), VERY_LIGHT_GRAY),
        ('FONTSIZE', (0,1), (-1,-1), 7),
        ('GRID', (0,0), (-1,-1), 0.5, LIGHT_BLACK),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    
    story.append(Paragraph('Documents Table:', h3_style))
    story.append(doc_table)
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph('Schema Summary:', h3_style))
    story.append(Paragraph('The database schema implements multi-tenant architecture with 5 core tables. Users authenticate via JWT and belong to Dealerships for data isolation. Documents are processed into Chunks with 1536-dimension vector embeddings stored using pgvector. All tables use UUID primary keys for security and include timestamps for audit trails. Foreign key relationships ensure referential integrity across the schema.', body_style))
    story.append(Spacer(1, 0.08*inch))
    
    story.append(Paragraph('Key Schema Features:', h3_style))
    story.append(Paragraph('• Users Table: Central authentication table with bcrypt-hashed passwords. The role field enforces RBAC with three levels. Foreign key to dealerships enables multi-tenant data isolation.', bullet_style))
    story.append(Paragraph('• Dealerships Table: Multi-tenant architecture root. Each dealership has isolated documents and users. The rag_enabled flag controls whether RAG features are active for that dealership.', bullet_style))
    story.append(Paragraph('• Documents Table: Tracks uploaded files with metadata. Status field (processing/completed/failed) enables async processing tracking. chunks_count shows how many chunks were generated.', bullet_style))
    story.append(Paragraph('• Document Chunks Table: Stores text chunks with 1536-dimension vector embeddings. The embedding column uses pgvector type for efficient similarity search. JSONB metadata enables flexible filtering.', bullet_style))
    story.append(Paragraph('• Refresh Tokens Table: Manages JWT refresh tokens with expiration tracking. Tokens are unique and tied to specific users for secure token rotation.', bullet_style))
    story.append(Paragraph('• All tables use UUID primary keys for security and scalability. Timestamps (created_at, updated_at) enable audit trails and data lifecycle management.', bullet_style))
    
    story.append(Spacer(1, 0.15*inch))
    
    # 8. Security
    story.append(Paragraph('8. Security Architecture', h1_style))
    story.append(Paragraph('8.1 Security Layers', h2_style))
    story.append(Spacer(1, 0.08*inch))
    story.append(create_security_diagram())
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph('Security Explanation:', h3_style))
    story.append(Paragraph('• 6-layer security: Client → Gateway (CORS, Rate Limit) → Auth (JWT) → Authorization (RBAC) → Application → Data (Encryption).', bullet_style))
    
    story.append(Spacer(1, 0.15*inch))
    
    # 9. File Structure
    story.append(Paragraph('9. File Structure', h1_style))
    story.append(Paragraph('9.1 Backend Directory Tree', h2_style))
    
    backend_tree = [
        'backend/',
        '+-- app/',
        '|   +-- main.py                    # FastAPI application',
        '|   +-- api/v1/',
        '|   |   +-- auth.py                # Authentication',
        '|   |   +-- users.py               # User management',
        '|   |   +-- chat.py                # Chat endpoints',
        '|   |   +-- voice.py               # Voice endpoints',
        '|   |   +-- rag.py                 # RAG endpoints',
        '|   +-- core/',
        '|   |   +-- config.py              # Configuration',
        '|   |   +-- database.py            # Database setup',
        '|   |   +-- security.py            # JWT & passwords',
        '|   +-- models/',
        '|   |   +-- user.py                # User model',
        '|   |   +-- dealership.py          # Dealership model',
        '|   |   +-- document.py            # Document model',
        '|   +-- schemas/',
        '|   |   +-- auth.py                # Auth schemas',
        '|   |   +-- user.py                # User schemas',
        '|   +-- services/',
        '|       +-- llm_service.py         # LLM integration',
        '|       +-- rag_service.py         # RAG system',
        '|       +-- voice_service.py       # Voice processing',
        '+-- alembic/                       # Migrations',
        '+-- pyproject.toml                 # Dependencies'
    ]
    
    tree_table = Table([[line] for line in backend_tree], colWidths=[5.5*inch])
    tree_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Courier'),
        ('FONTSIZE', (0,0), (-1,-1), 7),
        ('TEXTCOLOR', (0,0), (-1,-1), DARK_GRAY),
        ('BACKGROUND', (0,0), (-1,-1), VERY_LIGHT_GRAY),
        ('BOX', (0,0), (-1,-1), 0.8, LIGHT_BLACK),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(tree_table)
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph('9.2 Frontend Directory Tree', h2_style))
    
    frontend_tree = [
        'frontend/',
        '+-- src/',
        '|   +-- App.tsx                    # Main application',
        '|   +-- main.tsx                   # Entry point',
        '|   +-- pages/',
        '|   |   +-- Login.tsx              # Login page',
        '|   |   +-- Dashboard.tsx          # Dashboard',
        '|   |   +-- Chat.tsx               # Chat interface',
        '|   |   +-- VoiceChat.tsx          # Voice chat',
        '|   |   +-- RagManagement.tsx      # Document mgmt',
        '|   +-- components/',
        '|   |   +-- Layout.tsx             # Layout',
        '|   |   +-- ChatPanel.tsx          # Chat UI',
        '|   +-- context/',
        '|   |   +-- AuthContext.tsx        # Auth context',
        '|   +-- hooks/',
        '|   |   +-- useVoiceChat.ts        # Voice hook',
        '|   +-- services/',
        '|       +-- api.ts                 # API client',
        '+-- package.json                   # Dependencies',
        '+-- vite.config.ts                 # Vite config',
        '+-- tailwind.config.js             # Tailwind config'
    ]
    
    tree_table2 = Table([[line] for line in frontend_tree], colWidths=[5.5*inch])
    tree_table2.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Courier'),
        ('FONTSIZE', (0,0), (-1,-1), 7),
        ('TEXTCOLOR', (0,0), (-1,-1), DARK_GRAY),
        ('BACKGROUND', (0,0), (-1,-1), VERY_LIGHT_GRAY),
        ('BOX', (0,0), (-1,-1), 0.8, LIGHT_BLACK),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(tree_table2)
    
    # Build
    doc.build(story, canvasmaker=PageNumCanvas)
    size = Path(pdf_file).stat().st_size / 1024
    print(f'✅ Clean PDF created: {pdf_file}')
    print(f'📊 Size: {size:.1f} KB')
    print(f'📑 No overlapping content!')

if __name__ == "__main__":
    print('='*70)
    print('  Avatar Adam - Clean PDF Generator (No Overlapping)')
    print('='*70)
    print()
    generate_pdf()
