class PromptTemplates:
    """Templates for various AI prompts in the legal assistant."""
    
    def __init__(self):
        # Import here to avoid circular imports
        from services.prompt_management_service import PromptManagementService
        self.prompt_service = PromptManagementService()
    
    async def create_rag_prompt(self, query: str, context: str, conversation_history: str = "") -> str:
        """Create a prompt for RAG-based question answering."""
        
        # Format conversation history if provided
        conversation_part = f"\nCONVERSATION HISTORY:\n{conversation_history}\n" if conversation_history else ""
        
        variables = {
            'query': query,
            'context': context,
            'conversation_history': conversation_part
        }
        
        return await self.prompt_service.format_prompt('rag_prompt', variables)
    
    async def create_summary_prompt(self, document_text: str) -> str:
        """Create a prompt for document summarization."""
        
        variables = {
            'document_text': document_text
        }
        
        return await self.prompt_service.format_prompt('document_summary_prompt', variables)
    
    async def create_analysis_prompt(self, document_text: str, analysis_type: str) -> str:
        """Create a prompt for specific document analysis."""
        
        # Map analysis types to template names
        template_mapping = {
            "contract": "contract_analysis_prompt",
            "agreement": "agreement_analysis_prompt",
            "policy": "policy_analysis_prompt",
            "general": "general_analysis_prompt"
        }
        
        template_name = template_mapping.get(analysis_type, "general_analysis_prompt")
        
        variables = {
            'document_text': document_text
        }
        
        return await self.prompt_service.format_prompt(template_name, variables)
    
    async def create_hybrid_rag_prompt(self, query: str, context: str, 
                               session_context: str = "", 
                               conversation_history: str = "") -> str:
        """Create a prompt for hybrid RAG-based question answering with multiple sources"""
        
        # Format conversation history if provided
        conversation_part = f"\nCONVERSATION HISTORY:\n{conversation_history}\n" if conversation_history else ""
        
        # Format session context if provided
        session_part = f"\nCURRENT SESSION CONTEXT:\n{session_context}\n" if session_context else ""
        
        variables = {
            'query': query,
            'context': context,
            'conversation_history': conversation_part,
            'session_context': session_part
        }
        
        return await self.prompt_service.format_prompt('hybrid_rag_prompt', variables)
    
    async def create_hybrid_rag_prompt_with_user_type(self, query: str, context: str, 
                                              user_type: str = "normal",
                                              session_context: str = "", 
                                              conversation_history: str = "") -> str:
        """Create a prompt for hybrid RAG-based question answering with user type consideration"""
        
        # Format conversation history if provided
        conversation_part = f"\nCONVERSATION HISTORY:\n{conversation_history}\n" if conversation_history else ""
        
        # Format session context if provided
        session_part = f"\nCURRENT SESSION CONTEXT:\n{session_context}\n" if session_context else ""
        
        variables = {
            'query': query,
            'context': context,
            'conversation_history': conversation_part,
            'session_context': session_part
        }
        
        # Use user-type specific templates
        if user_type == "lawyer":
            template_name = 'hybrid_rag_prompt_lawyer'
        else:
            template_name = 'hybrid_rag_prompt_normal'
        
        return await self.prompt_service.format_prompt(template_name, variables, user_type)