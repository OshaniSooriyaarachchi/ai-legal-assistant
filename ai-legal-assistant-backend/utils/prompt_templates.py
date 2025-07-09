class PromptTemplates:
    """Templates for various AI prompts in the legal assistant."""
    
    def create_rag_prompt(self, query: str, context: str, conversation_history: str = "") -> str:
        """Create a prompt for RAG-based question answering."""
        
        base_prompt = """You are an AI legal assistant specialized in analyzing legal documents and providing accurate, helpful responses. You have access to the user's uploaded legal documents and should base your responses primarily on this context.

IMPORTANT GUIDELINES:
1. Always base your responses on the provided context from the user's documents
2. If the context doesn't contain relevant information, clearly state that you cannot find the answer in the uploaded documents
3. Never make up legal advice or information not supported by the context
4. Always cite specific documents when referencing information
5. Be precise and professional in your language
6. If asked about legal procedures not covered in the documents, suggest consulting with a qualified attorney

"""

        if conversation_history:
            base_prompt += f"\nCONVERSATION HISTORY:\n{conversation_history}\n"
        
        base_prompt += f"""
CONTEXT FROM USER'S DOCUMENTS:
{context}

USER QUESTION: {query}

Please provide a helpful, accurate response based on the context above. If you reference specific information, please cite the source document."""

        return base_prompt
    
    def create_summary_prompt(self, document_text: str) -> str:
        """Create a prompt for document summarization."""
        
        return f"""Please provide a comprehensive summary of the following legal document. Focus on:

1. Document type and purpose
2. Key parties involved
3. Main terms and conditions
4. Important dates and deadlines
5. Legal obligations and rights
6. Any notable clauses or provisions

Document content:
{document_text}

Summary:"""
    
    def create_analysis_prompt(self, document_text: str, analysis_type: str) -> str:
        """Create a prompt for specific document analysis."""
        
        analysis_prompts = {
            "contract": "Analyze this contract focusing on obligations, rights, termination clauses, and potential risks.",
            "agreement": "Analyze this agreement highlighting key terms, responsibilities, and legal implications.",
            "policy": "Review this policy document and explain its main provisions and compliance requirements.",
            "general": "Provide a detailed legal analysis of this document."
        }
        
        prompt = analysis_prompts.get(analysis_type, analysis_prompts["general"])
        
        return f"""{prompt}

Document content:
{document_text}

Analysis:"""
    
    def create_hybrid_rag_prompt(self, query: str, context: str, 
                               session_context: str = "", 
                               conversation_history: str = "") -> str:
        """Create a prompt for hybrid RAG-based question answering with multiple sources"""
        
        base_prompt = """You are an expert Sri Lankan legal advisor with access to both the common legal knowledge base and user-specific documents. You should provide accurate, comprehensive responses based on the provided context from multiple sources.

IMPORTANT GUIDELINES:
1. Use information from the Legal Knowledge Base for general legal principles and authoritative guidance
2. Use information from user documents for specific case details and document analysis
3. Use current session documents for contextual relevance to the ongoing conversation
4. Clearly distinguish between general legal principles and document-specific information
5. Always cite your sources and specify whether information comes from the legal knowledge base or user documents
6. If information conflicts between sources, explain the differences and provide guidance
7. Be precise and professional in your language
8. If the context doesn't contain sufficient information, clearly state limitations

"""

        if conversation_history:
            base_prompt += f"\nCONVERSATION HISTORY:\n{conversation_history}\n"
        
        if session_context:
            base_prompt += f"\nCURRENT SESSION CONTEXT:\n{session_context}\n"
        
        base_prompt += f"""
AVAILABLE CONTEXT FROM MULTIPLE SOURCES:
{context}

USER QUESTION: {query}

Please provide a comprehensive response based on the available context. When referencing information:
- Use [Legal Knowledge Base] for information from the common legal database
- Use [Your Document: filename] for information from user-uploaded documents
- Use [Session Document: filename] for information from documents in the current session

If you need to reference specific legal procedures or requirements not covered in the provided context, suggest consulting with a qualified attorney.

RESPONSE:"""

        return base_prompt