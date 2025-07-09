class ChatService:
    def __init__(self):
        self.supabase = get_supabase_client()
    
    async def create_chat_session(self, user_id: str, title: str = None) -> str:
        """Create new chat session"""
        result = self.supabase.table('chat_sessions').insert({
            'user_id': user_id,
            'title': title or f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        }).execute()
        return result.data[0]['id']
    
    async def get_user_chat_sessions(self, user_id: str) -> List[Dict]:
        """Get all chat sessions for user"""
        pass
    
    async def get_chat_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        """Get chat history for session"""
        pass
    
    async def add_message_to_session(self, session_id: str, message_type: str,
                                   content: str, document_ids: List[str] = None):
        """Add message to chat session"""
        pass
    
    async def get_session_context(self, session_id: str, last_n_messages: int = 5) -> str:
        """Get recent conversation context"""
        pass