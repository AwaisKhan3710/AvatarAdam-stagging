Avatar Adam MVP - Requirements Document
Project: AI-Powered F&I Training Platform
Version: MVP (Minimum Viable Product)
Project Goal
Build a platform where F&I managers at automotive dealerships can interact with an AI-powered digital avatar of Adam Marburger to receive on-demand training, ask questions, and practice scenarios.


Core Requirements
1. Conversational Training
Users need to be able to ask questions and receive answers based on Adam's training content.
What it needs to do:
•Accept text-based questions from users
•Retrieve relevant information from Adam's content (books, videos, playbooks, coaching sessions)
•Generate responses that reflect Adam's teaching style and expertise
•Display responses through a digital avatar that looks and sounds like Adam
•Maintain conversation context across multiple questions in a session
•Allow users to start new sessions
Content to be used:
•Adam's published books (1-2 books on F&I theory, process, framework, objection handling)
•Black Belt Playbook (structured progression from entry-level to elite)
•Video training library
•Professional video assets (green screen recordings)
•Recorded coaching sessions
•Papers, blogs, and other written content
Content organization approach (from meeting discussion):
•Multiple specialized knowledge bases organized by topic rather than one large database
•Separate knowledge bases for: books, objection handling, specific training modules, etc.
•From user perspective, appears as single unified system
•System routes queries to appropriate knowledge base based on question topic
2. Role-Play Training
Users need to be able to practice F&I scenarios with the AI acting as a customer.
What it needs to do:
•Provide pre-defined training scenarios (objection handling, product presentation, deal structuring)
•AI plays the role of a customer with realistic objections and concerns
•Accept text responses from the user
•Evaluate user responses and provide specific feedback
•Continue the conversation for multiple exchanges
•Generate a session summary with strengths, areas for improvement, and recommendations
Scenarios needed for MVP:
•Objection handling scenarios
•Product presentation scenarios
•Deal structuring scenarios
3. Content Library
Users need to be able to browse and access Adam's training materials.
What it needs to do:
•Display content organized by categories and topics
•Allow users to search for specific content
•Support different content types (PDFs, videos, documents)
•Allow users to view/play content within the platform
•Let users bookmark content for later access
•Track which content users have accessed
Content categories:
•Books
•Playbooks
•Videos
•Objection handling techniques
•Product knowledge
•Compliance information
•Deal structuring guidance
4. Analytics Dashboard
Users and administrators need to see usage data and engagement metrics.
What it needs to do:
•Track user sessions (training and role-play)
•Track time spent in the platform
•Track questions asked and topics accessed
•Track content views
•Track role-play completions
•Display metrics for individual users
•Display aggregated metrics for dealerships
•Allow data export
•Show usage trends over time
Metrics needed:
•Session count and duration
•Questions asked
•Topics accessed
•Content views
•Role-play completions
•Login frequency
•Active users vs total users


User Requirements
User Types
F&I Managers (Primary Users)
•Need access to training, role-play, and content library
•Need to see their own analytics
•Range from entry-level to experienced managers
Dealer Principals (Administrators)
•Need access to all features
•Need to see dealership-wide analytics
•Need to manage users within their dealership
System Administrators
•Need to manage all dealerships and users
•Need access to system-wide analytics
User Authentication
What it needs to do:
•Users must log in with credentials to access the platform
•Sessions must be secure
•Sessions should timeout after period of inactivity
•Users should be able to reset passwords
•Access must be restricted to authorized users only
Access control needed:
•Users can only access their own dealership's data
•Dealer principals can see all users in their dealership
•Content is only accessible to authenticated users


Avatar Requirements
Avatar Appearance and Behavior
What it needs to do:
•Look like Adam Marburger
•Sound like Adam Marburger (voice cloning from his existing audio)
•Lip-sync accurately with generated speech
•Display video responses to user questions
•Support extended conversation sessions (no arbitrary time limits)
From meeting discussion:
•Platforms discussed: D-ID and HeyGen
•Voice cloning: ElevenLabs mentioned as solution
•Need unlimited streaming session duration
•Cost consideration: $100-330/month range discussed
•Avatar creation time: 24 hours mentioned
Avatar Integration
What it needs to do:
•Receive text from the AI system
•Convert text to speech in Adam's voice
•Generate video of avatar speaking the text
•Stream video to user interface
•Handle interruptions and reconnections gracefully


AI System Requirements
Knowledge Base Structure
From meeting discussion:
The system needs multiple specialized knowledge bases rather than one monolithic database. Each knowledge base contains content for a specific topic area.
Reasoning (from meeting):
•Single large knowledge base with thousands of documents would create excessive context size
•Large context reduces accuracy
•Topic-specific knowledge bases allow better control over information retrieval
•Easier to manage and update
Implementation approach:
•Create separate knowledge bases for different topics
•System determines which knowledge base(s) to query based on user question
•User sees unified experience despite multiple knowledge bases behind the scenes
Response Generation
What it needs to do:
•Understand user questions
•Retrieve relevant content from appropriate knowledge base(s)
•Generate responses grounded in Adam's actual content
•Maintain Adam's personality, teaching style, and tone
•Provide specific, actionable advice
•Cite sources when appropriate
•Admit when information is not available rather than guessing
Role-Play AI
What it needs to do:
•Play customer role realistically
•Present objections and concerns appropriate to the scenario
•Respond to user's statements as a customer would
•Evaluate user responses based on:
•Whether they address the customer's concern
•Use of proper F&I techniques
•Professional tone
•Compliance with regulations
•Likelihood of moving the deal forward
•Provide specific, actionable feedback
•Generate meaningful session summaries


Performance Requirements
Response Time
What users expect:
•Questions should receive responses quickly enough to feel conversational
•Avatar video should start playing without long delays
•Content should load quickly
•Search results should appear quickly
Reliability
What the system needs:
•Be available during business hours
•Handle errors gracefully without crashing
•Provide fallback options if avatar service is unavailable (text-only mode)
•Recover from temporary failures automatically
Scalability
What the system needs to support:
•50-100 users initially (pilot phase)
•Multiple users accessing the system simultaneously
•Growth to larger user base in future phases


Security Requirements
Data Protection
What needs to be protected:
•User credentials and authentication information
•User conversation history and activity data
•Adam's proprietary content
•Dealership data
How it needs to be protected:
•Secure communication between user and system
•Secure storage of sensitive data
•Isolation of data between dealerships
•Protection against unauthorized access
Session Security
What it needs to do:
•Automatically log users out after inactivity
•Invalidate sessions when users log out
•Prevent unauthorized access to active sessions


Content Requirements
Content Processing
What needs to happen:
•Adam's existing content needs to be extracted and formatted for the AI system
•Text needs to be extracted from PDFs and documents
•Videos need to be transcribed to text
•Content needs to be organized by topic
•Content needs to be prepared for semantic search
Content types to process:
•Books (PDF format)
•Playbooks (PDF format)
•Videos (transcription needed)
•Audio recordings (transcription needed)
•Written documents and blog posts
Content Management
What needs to be possible:
•Add new content to the system
•Update existing content
•Organize content by category and topic
•Make content searchable
•Track which content is most accessed


Integration Requirements
External Services
What needs to be integrated:
•Large language model service for AI responses
•Voice synthesis service for Adam's voice
•Avatar platform for video generation
•Storage for video and content files
•Database for user data and analytics
Data Flow
What needs to happen:
1.User sends question
2.System retrieves relevant content
3.AI generates response text
4.Text is converted to speech
5.Speech is used to generate avatar video
6.Video is delivered to user
7.Interaction is logged for analytics


MVP Scope Boundaries
What IS included in MVP:
•Text-based questions and answers
•Digital avatar with voice and video
•Role-play scenarios with AI feedback
•Content library with search
•Basic analytics dashboard
•User authentication and session management
•Support for multiple dealerships
•Web-based interface (desktop and mobile browsers)
What is NOT included in MVP:
•Voice input (speaking questions instead of typing)
•Native mobile apps (iOS/Android)
•Advanced analytics (predictive insights, recommendations)
•Gamification (badges, points, leaderboards)
•Social features (user forums, peer interaction)
•Integration with dealership CRM/DMS systems
•Multi-language support
•Custom avatars for other trainers
•Content creation tools
•White-label customization
•API for third-party integrations


Success Criteria
Technical Success
•All four core features are functional
•Avatar looks and sounds like Adam (validated by Adam)
•AI responses are accurate and grounded in Adam's content
•System performs well with expected user load
•System is reliable and available during business hours
User Success
•10-20 pilot dealerships can be onboarded
•Users find the platform helpful for training
•Users engage with the platform regularly
•Dealer principals see value in the platform
Business Success
•Platform can be deployed within reasonable timeframe
•Operating costs are sustainable
•Architecture supports future growth
•Clear path forward for post-MVP enhancements


Open Questions
These questions need to be answered before or during development:
User Management:
•How are user accounts created? Self-registration or admin-created?
•How are dealerships onboarded?
•What information is collected during user registration?
Subscription & Billing:
•How is access controlled? Per user, per dealership, or other?
•How is billing handled?
•What happens when subscription expires?
Content Management:
•How will Adam add new content after launch?
•Who manages content updates?
•How frequently will content be updated?
Branding & Design:
•What branding elements are required (logo, colors, fonts)?
•What design style is preferred?
•Are there existing brand guidelines?
Support:
•Who provides user support?
•What support channels are needed (email, chat, phone)?
•What are support hours?
Deployment:
•Where will the system be hosted?
•What domain will be used?
•Who manages infrastructure?
Analytics:
•What specific metrics are most important to track?
•Who needs access to analytics data?
•How should data be exported?


Key Decisions from Meeting Discussion
Based on the team meeting, these decisions have been made:
Content Organization:
•Use multiple specialized knowledge bases organized by topic
•Do not use one large monolithic knowledge base
•System should route queries to appropriate knowledge base(s)
Avatar Platform:
•Considering D-ID or HeyGen
•Need unlimited streaming session duration
•Voice cloning via ElevenLabs
•Expected cost: $100-330/month
Voice Cloning:
•Use ElevenLabs for voice synthesis
•Need quality audio samples of Adam speaking
•Existing coaching sessions and videos should provide sufficient audio
Platform Access:
•Web-based application (not native mobile apps for MVP)
•Accessible on desktop and mobile browsers
•Credential-based access with auto-logout for security


Technical Constraints
Must Support:
•Web browsers (Chrome, Safari, Firefox, Edge)
•Desktop and mobile devices
•Secure HTTPS connections
•Video streaming
•Real-time or near-real-time responses
Must Integrate With:
•AI language model service
•Voice synthesis service
•Avatar video generation service
•Storage service for content and videos
•Database for user and analytics data
Must Handle:
•Multiple concurrent users
•Extended conversation sessions
•Large content library
•Video streaming
•User authentication and authorization
•Data privacy and security


Deliverables
At the end of MVP development, the following should be delivered:
Functional Platform:
•Working web application with all four core features
•User authentication and session management
•Digital avatar integration
•Content library with all of Adam's materials
•Analytics dashboard
Documentation:
•User guide for F&I managers
•Admin guide for dealer principals
•System documentation for maintenance
•API documentation (if applicable)
Deployment:
•Production environment setup
•Monitoring and logging configured
•Backup and recovery procedures
•Security measures implemented
Testing:
•All features tested and validated
•Performance tested with expected user load
•Security tested
•User acceptance testing completed


Next Steps
Before Development Starts:
1.Answer open questions listed above
2.Provide access to all of Adam's content
3.Finalize technology choices (avatar platform, hosting, etc.)
4.Define project timeline and milestones
5.Assign development team roles
Content Preparation:
1.Collect all of Adam's content in digital format
2.Organize content by category
3.Extract audio samples for voice cloning
4.Select or record video for avatar creation
Technical Setup:
1.Set up development environment
2.Create accounts for required services
3.Set up version control and collaboration tools
4.Define development workflow


 


This document describes what needs to be built and what it needs to do, leaving how to build it to the development team's expertise and judgment.
