# AI Legal Assistant Implementation Instructions

## Project Overview
This is an AI-powered legal assistant application that makes law books searchable through natural language queries using RAG (Retrieval-Augmented Generation). Users can upload legal documents, ask questions about specific legal scenarios, and receive contextually accurate answers.

## Tech Stack
- **Frontend**: React TypeScript
- **Backend**: Python with LangChain
- **Database**: Supabase with pgvector extension
- **Vector Database**: Supabase (PostgreSQL + pgvector)
- **AI Model**: Google Gemini API
- **Authentication**: Supabase Auth (already implemented)

## Current Status
✅ Authentication system completed (sign in, sign up, social login)
🔄 Need to implement: Document processing, vector storage, and RAG system

## Architecture Overview

### RAG Workflow
1. **Document Upload & Processing**
   - Admins upload law books (PDF/DOCX)
   - Split documents into chunks (500-1000 tokens)
   - Generate embeddings using Gemini API
   - Store chunks + embeddings + metadata in Supabase

2. **Query Processing**
   - User asks a legal question
   - Retrieve top-k relevant document chunks via vector similarity     search
   - Retrieve top-k relevant document chunks via vector similarity search

3. **Response Generation**
   - Combine retrieved chunks into a coherent context
   - Send the user query + context to Gemini for prompt completion
   - Return structured legal advice with references (if applicable)

## Implementation Steps

### Phase 1: Database Setup

#### 1.1 Enable pgvector Extension
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

#### 1.2 Create Database Schema
```sql
-- Documents table
CREATE TABLE documents (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_size BIGINT,
    file_type TEXT CHECK (file_type IN ('pdf', 'docx', 'txt')),
    upload_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processing_status TEXT DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
    book_category TEXT, -- e.g., 'traffic_law', 'criminal_law', 'civil_law'
    language TEXT DEFAULT 'sinhala',
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Document chunks with embeddings
CREATE TABLE document_chunks (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    page_number INTEGER,
    chapter_title TEXT,
    section_title TEXT,
    embedding VECTOR(768), -- Gemini embedding dimensions
    token_count INTEGER,
    metadata JSONB, -- Store additional context like law type, keywords
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Query history for analytics and caching
CREATE TABLE query_history (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    query_text TEXT NOT NULL,
    query_embedding VECTOR(768),
    response_text TEXT,
    retrieved_chunks UUID[], -- Array of chunk IDs used
    feedback_rating INTEGER CHECK (feedback_rating BETWEEN 1 AND 5),
    processing_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### 1.3 Create Indexes
```sql
-- Performance indexes
CREATE INDEX idx_documents_user_id ON documents(user_id);
CREATE INDEX idx_documents_category ON documents(book_category);
CREATE INDEX idx_documents_status ON documents(processing_status);
CREATE INDEX idx_chunks_document_id ON document_chunks(document_id);
CREATE INDEX idx_chunks_vector ON document_chunks USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_queries_user_id ON query_history(user_id);
```

#### 1.4 Row Level Security (RLS)
```sql
-- Enable RLS
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE query_history ENABLE ROW LEVEL SECURITY;

-- User access policies
CREATE POLICY "Users access own documents" ON documents
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users access chunks of own documents" ON document_chunks
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM documents WHERE documents.id = document_chunks.document_id AND documents.user_id = auth.uid())
    );

CREATE POLICY "Users access own queries" ON query_history
    FOR ALL USING (auth.uid() = user_id);

-- Service role policies for backend processing
CREATE POLICY "Service role full access" ON document_chunks
    FOR ALL USING (auth.role() = 'service_role');
```

### Phase 2: Backend Implementation (Python + LangChain)

#### 2.1 Project Structure
```
ai-legal-assistant-backend/
├── requirements.txt
├── .env
├── main.py
├── config/
│   ├── __init__.py
│   ├── settings.py
│   └── supabase_client.py
├── services/
│   ├── __init__.py
│   ├── document_processor.py
│   ├── embedding_service.py
│   ├── vector_store.py
│   └── rag_service.py
├── utils/
│   ├── __init__.py
│   ├── text_chunker.py
│   ├── file_parser.py
│   └── prompt_templates.py
├── api/
│   ├── __init__.py
│   ├── documents.py
│   ├── chat.py
│   └── auth_middleware.py
└── models/
    ├── __init__.py
    └── schemas.py
```

#### 2.2 Dependencies (requirements.txt)
```txt
fastapi==0.104.1
uvicorn==0.24.0
supabase==2.3.4
langchain==0.1.0
langchain-google-genai==0.0.8
langchain-community==0.0.12
python-multipart==0.0.6
PyMuPDF==1.23.9  # PDF processing
python-docx==1.1.0  # DOCX processing
numpy==1.25.2
python-dotenv==1.0.0
pydantic==2.5.0
tiktoken==0.5.1
asyncpg==0.29.0
pgvector==0.2.4
```

#### 2.3 Core Services Implementation

**Document Processing Service**
- Extract text from PDF/DOCX files
- Split into semantic chunks (500-1000 tokens)
- Add 50-100 token overlap between chunks
- Extract metadata (chapter, section, page numbers)
- Generate embeddings using Gemini
- Store in Supabase with metadata tags

**Vector Store Service**
- Interface with Supabase pgvector
- Implement similarity search with configurable k
- Support metadata filtering (law category, document type)
- Implement hybrid search (vector + keyword)

**RAG Service**
- Query embedding generation
- Retrieve top-k relevant chunks
- Re-rank results using cross-encoder (optional)
- Context assembly and prompt engineering
- Generate responses using Gemini

#### 2.4 Key Implementation Details

**Chunking Strategy**
```python
# Semantic chunking with overlap
chunk_size = 800  # tokens
chunk_overlap = 100  # tokens
# Preserve sentence boundaries
# Add chapter/section context to each chunk
```

**Embedding Configuration**
```python
# Use Gemini embedding model
model_name = "models/embedding-001"
embedding_dimensions = 768
```

**Similarity Search**
```python
# Cosine similarity with threshold
similarity_threshold = 0.7
top_k_results = 10  # Retrieve top 10, use best 5
```

**Prompt Template**
```python
LEGAL_EXPERT_PROMPT = """
You are an expert legal advisor. Based on the provided legal passages, answer the user's question accurately and comprehensively.

LEGAL CONTEXT:
{retrieved_passages}

USER QUESTION:
{user_query}

Instructions:
1. Base your answer primarily on the provided legal passages
2. If the passages don't contain sufficient information, clearly state this
3. Provide specific legal references when available
4. Explain the reasoning behind your conclusion
5. Use clear, accessible language while maintaining legal accuracy

RESPONSE:
"""
```

### Phase 3: Frontend Integration

#### 3.1 Required Components
```typescript
// Document upload and management
- DocumentUploader.tsx
- DocumentList.tsx
- ProcessingStatus.tsx

// Chat interface
- ChatInterface.tsx
- MessageBubble.tsx
- QueryInput.tsx

// Legal assistant features
- LegalChat.tsx (general advice)
- DocumentChat.tsx (document-specific queries)
- SearchResults.tsx
```

#### 3.2 API Integration
```typescript
// Services to implement
- documentService.ts (upload, list, delete)
- chatService.ts (send queries, get responses)
- embeddingService.ts (vector operations)
```

#### 3.3 State Management
```typescript
// Redux slices needed
- documentsSlice.ts (document management)
- chatSlice.ts (conversation history)
- uiSlice.ts (loading states, errors)
```

### Phase 4: Advanced Features

#### 4.1 Optimization Features
- **Caching**: Cache frequent queries and embeddings
- **Batch Processing**: Process multiple documents efficiently
- **Progress Tracking**: Real-time upload/processing status
- **Error Handling**: Comprehensive error recovery

#### 4.2 Quality Improvements
- **Re-ranking**: Use cross-encoder for better relevance
- **Metadata Filtering**: Filter by law category, document type
- **Feedback Loop**: Collect user ratings to improve results
- **Query Expansion**: Enhance queries with legal synonyms

#### 4.3 Performance Tuning
- **Chunk Size Optimization**: Test different chunk sizes
- **Embedding Caching**: Cache document embeddings
- **Database Indexing**: Optimize vector search performance
- **API Rate Limiting**: Manage Gemini API usage

### Phase 5: Deployment Considerations

#### 5.1 Environment Configuration
```env
# Backend .env
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
GEMINI_API_KEY=your_gemini_api_key
ENVIRONMENT=production
MAX_CHUNK_SIZE=1000
EMBEDDING_DIMENSIONS=768
```

#### 5.2 Security Measures
- Validate file types and sizes
- Implement rate limiting
- Sanitize user inputs
- Secure API endpoints
- Monitor API usage and costs

#### 5.3 Monitoring & Analytics
- Track query performance
- Monitor embedding generation costs
- Log user interactions
- Measure response accuracy
- Set up alerts for failures

## Usage Examples

### Example 1: Traffic Law Query
**User Input**: "I overtook a vehicle on a solid yellow line because there was an emergency vehicle behind me. Is this illegal?"

**System Process**:
1. Convert query to embedding
2. Search for traffic law chunks about overtaking
3. Retrieve relevant passages about emergency situations
4. Generate response with legal reasoning

### Example 2: Document Upload
**Process**:
1. User uploads "Traffic Law Handbook.pdf"
2. Backend extracts text and splits into chunks
3. Each chunk tagged with metadata: category="traffic_law", chapter="Overtaking Rules"
4. Embeddings generated and stored
5. Document marked as "completed"

## Development Priorities

1. **Phase 1**: Database setup and basic document processing
2. **Phase 2**: Core RAG functionality with simple chunking
3. **Phase 3**: Frontend integration and basic chat interface
4. **Phase 4**: Advanced features and optimization
5. **Phase 5**: Production deployment and monitoring

## Testing Strategy

- Unit tests for chunking and embedding functions
- Integration tests for RAG pipeline
- End-to-end tests for user workflows
- Performance tests for vector search
- User acceptance tests with legal professionals

## Success Metrics

- Query response accuracy (user feedback)
- Response time < 3 seconds
- Document processing time
- User engagement and retention
- Cost per query optimization

---

**Note for AI Agents**: When implementing features, always consider the legal domain requirements for accuracy and reliability. Prioritize clear error messages and graceful failure handling, especially for legal advice applications.