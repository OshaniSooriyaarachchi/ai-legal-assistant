import logging
import re
from typing import Dict, List, Optional
from datetime import datetime
from config.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self):
        self.supabase = get_supabase_client()
    
    async def create_chat_session(self, user_id: str, title: str = None) -> str:
        """Create new chat session"""
        try:
            title = title or f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            result = self.supabase.table('chat_sessions').insert({
                'user_id': user_id,
                'title': title,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'is_active': True
            }).execute()
            
            if not result.data:
                raise Exception("Failed to create chat session")
            
            session_id = result.data[0]['id']
            logger.info(f"Created chat session {session_id} for user {user_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Error creating chat session: {str(e)}")
            raise Exception(f"Failed to create chat session: {str(e)}")
    
    async def get_user_chat_sessions(self, user_id: str) -> List[Dict]:
        """Get all chat sessions for user"""
        try:
            result = self.supabase.table('chat_sessions').select(
                'id, title, created_at, updated_at, is_active'
            ).eq('user_id', user_id).eq('is_active', True).order('updated_at', desc=True).execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error getting user chat sessions: {str(e)}")
            raise Exception(f"Failed to retrieve chat sessions: {str(e)}")
    
    async def get_chat_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        """Get chat history for session"""
        try:
            result = self.supabase.table('query_history').select(
                'id, query_text, response_text, message_type, created_at, '
                'document_ids, processing_time_ms'
            ).eq('session_id', session_id).order('created_at', desc=False).limit(limit).execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error getting chat history: {str(e)}")
            raise Exception(f"Failed to retrieve chat history: {str(e)}")
    
    async def add_message_to_session(self, session_id: str, user_id: str, message_type: str,
                                   content: str, response_text: str = None, 
                                   document_ids: List[str] = None, 
                                   processing_time_ms: int = None):
        """Add message to chat session"""
        try:
            # Prepare message data
            message_data = {
                'session_id': session_id,
                'user_id': user_id,
                'message_type': message_type,
                'created_at': datetime.now().isoformat(),
                'document_ids': document_ids or []
            }
            
            # Add content based on message type
            if message_type == 'user_query':
                message_data['query_text'] = content
            elif message_type == 'assistant_response':
                message_data['query_text'] = content  # Original query
                message_data['response_text'] = response_text
                message_data['processing_time_ms'] = processing_time_ms
            elif message_type == 'document_upload':
                message_data['query_text'] = content  # Filename or description
                message_data['document_ids'] = document_ids
            
            # Insert message
            result = self.supabase.table('query_history').insert(message_data).execute()
            
            if not result.data:
                raise Exception("Failed to add message to session")
            
            # Update session's updated_at timestamp
            self.supabase.table('chat_sessions').update({
                'updated_at': datetime.now().isoformat()
            }).eq('id', session_id).execute()
            
            logger.info(f"Added {message_type} message to session {session_id}")
            return result.data[0]['id']
            
        except Exception as e:
            logger.error(f"Error adding message to session: {str(e)}")
            raise Exception(f"Failed to add message to session: {str(e)}")
    
    async def get_session_context(self, session_id: str, last_n_messages: int = 5) -> str:
        """Get recent conversation context"""
        try:
            # Get last N messages from the session
            result = self.supabase.table('query_history').select(
                'query_text, response_text, message_type, created_at'
            ).eq('session_id', session_id).order('created_at', desc=True).limit(last_n_messages).execute()
            
            if not result.data:
                return ""
            
            # Format context (reverse to get chronological order)
            context_parts = []
            for message in reversed(result.data):
                if message['message_type'] == 'user_query':
                    context_parts.append(f"User: {message['query_text']}")
                elif message['message_type'] == 'assistant_response':
                    context_parts.append(f"Assistant: {message['response_text']}")
                elif message['message_type'] == 'document_upload':
                    context_parts.append(f"System: Document uploaded - {message['query_text']}")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error getting session context: {str(e)}")
            return ""
    
    async def update_session_title(self, session_id: str, user_id: str, new_title: str) -> bool:
        """Update chat session title"""
        try:
            result = self.supabase.table('chat_sessions').update({
                'title': new_title,
                'updated_at': datetime.now().isoformat()
            }).eq('id', session_id).eq('user_id', user_id).execute()
            
            if not result.data:
                raise Exception("Session not found or not authorized")
            
            logger.info(f"Updated session {session_id} title to '{new_title}'")
            return True
            
        except Exception as e:
            logger.error(f"Error updating session title: {str(e)}")
            raise Exception(f"Failed to update session title: {str(e)}")
    
    async def generate_chat_title(self, first_message: str, max_length: int = 50) -> str:
        """Generate a meaningful title from the first message"""
        try:
            # Use enhanced method for better results
            return await self.generate_enhanced_title(first_message)
            
        except Exception as e:
            logger.error(f"Error generating title: {str(e)}")
            return "New Chat"
    
    async def generate_smart_title(self, message: str) -> str:
        """Generate title using AI"""
        try:
            import google.generativeai as genai
            from config.settings import settings
            
            genai.configure(api_key=settings.gemini_api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""
            Generate a meaningful, descriptive title for a legal chat conversation that starts with this message:
            
            "{message}"
            
            Requirements:
            - Maximum 50 characters total
            - Capture the main legal topic, not just the first few words
            - Be specific and meaningful
            - Use legal terminology when appropriate
            - Return only the title, no quotes or explanation
            
            Examples of GOOD titles:
            - "Employment Contract Review"
            - "Property Dispute Resolution" 
            - "Intellectual Property Rights"
            - "Corporate Compliance Issue"
            - "Tenant Rights Question"
            - "Business Formation Help"
            - "Privacy Law Compliance"
            - "Tax Law Consultation"
            
            Examples of BAD titles (avoid these):
            - "I need help with my..."
            - "Can you help me..."
            - "What should I do about..."
            """
            
            response = model.generate_content(prompt)
            title = response.text.strip().replace('"', '').replace("'", "")
            
            # Validate the title quality
            if self._is_meaningful_title(title, message):
                return title[:50]  # Ensure character limit
            else:
                # Try enhanced extraction method
                return await self.generate_enhanced_title(message)
            
        except Exception as e:
            logger.error(f"AI title generation failed: {str(e)}")
            return await self.generate_enhanced_title(message)
    
    def _is_meaningful_title(self, title: str, original_message: str) -> bool:
        """Check if the generated title is meaningful"""
        if not title or len(title) < 5:
            return False
            
        # Check for bad patterns
        bad_patterns = [
            "i need help", "can you help", "what should i", 
            "how do i", "please help", "i have a question",
            "i want to", "i'm looking for"
        ]
        
        title_lower = title.lower()
        for pattern in bad_patterns:
            if pattern in title_lower:
                return False
        
        # Check if title is just truncated first words
        first_words = " ".join(original_message.split()[:4]).lower()
        if title_lower.startswith(first_words.lower()[:20]):
            return False
            
        return True
    
    async def generate_enhanced_title(self, message: str) -> str:
        """Enhanced title generation with legal keyword extraction"""
        try:
            # Legal keywords to prioritize
            legal_keywords = {
                'contract': 'Contract',
                'employment': 'Employment',
                'property': 'Property', 
                'intellectual property': 'IP',
                'copyright': 'Copyright',
                'trademark': 'Trademark',
                'patent': 'Patent',
                'corporate': 'Corporate',
                'business': 'Business',
                'compliance': 'Compliance',
                'privacy': 'Privacy',
                'tenant': 'Tenant Rights',
                'landlord': 'Landlord Issue',
                'divorce': 'Divorce',
                'custody': 'Child Custody',
                'immigration': 'Immigration',
                'criminal': 'Criminal Law',
                'personal injury': 'Personal Injury',
                'medical malpractice': 'Medical Malpractice',
                'tax': 'Tax Law',
                'estate': 'Estate Planning',
                'will': 'Will/Testament',
                'lawsuit': 'Litigation',
                'settlement': 'Settlement',
                'liability': 'Liability',
                'insurance': 'Insurance',
                'bankruptcy': 'Bankruptcy',
                'discrimination': 'Discrimination',
                'harassment': 'Harassment',
                'wrongful termination': 'Wrongful Termination',
                'non-disclosure': 'NDA',
                'non-compete': 'Non-Compete'
            }
            
            message_lower = message.lower()
            
            # Find relevant legal topics
            found_topics = []
            for keyword, topic in legal_keywords.items():
                if keyword in message_lower:
                    found_topics.append(topic)
            
            # Action keywords
            action_keywords = {
                'review': 'Review',
                'help': 'Help',
                'advice': 'Advice', 
                'question': 'Question',
                'issue': 'Issue',
                'problem': 'Problem',
                'dispute': 'Dispute',
                'concern': 'Concern',
                'consultation': 'Consultation',
                'guidance': 'Guidance'
            }
            
            found_actions = []
            for keyword, action in action_keywords.items():
                if keyword in message_lower:
                    found_actions.append(action)
            
            # Generate meaningful title
            if found_topics:
                main_topic = found_topics[0]
                if found_actions:
                    title = f"{main_topic} {found_actions[0]}"
                else:
                    title = f"{main_topic} Matter"
            else:
                # Extract key nouns and create a title
                import re
                words = re.findall(r'\b[A-Za-z]{3,}\b', message)
                important_words = [w for w in words[:8] if w.lower() not in 
                                 ['the', 'and', 'for', 'with', 'need', 'help', 'can', 'you', 'please', 'want', 'have']]
                
                if important_words:
                    if len(important_words) >= 2:
                        title = f"{important_words[0]} {important_words[1]} Matter"
                    else:
                        title = f"{important_words[0]} Question"
                else:
                    title = "Legal Consultation"
            
            # Ensure proper capitalization and length
            title = ' '.join(word.capitalize() for word in title.split())
            return title[:50]
            
        except Exception as e:
            logger.error(f"Enhanced title generation failed: {str(e)}")
            return "Legal Question"
    
    async def update_session_title_from_message(self, session_id: str, user_id: str, 
                                              first_message: str) -> bool:
        """Update session title based on first message"""
        try:
            # Check if session already has a custom title
            result = self.supabase.table('chat_sessions').select('title').eq('id', session_id).execute()
            
            if not result.data:
                return False
            
            current_title = result.data[0]['title']
            
            # Only update if title is generic (contains "Chat" and timestamp pattern)
            if "Chat" in current_title and any(c.isdigit() for c in current_title):
                # Use AI-powered title generation
                new_title = await self.generate_smart_title(first_message)
                return await self.update_session_title(session_id, user_id, new_title)
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating session title from message: {str(e)}")
            return False
    
    async def delete_chat_session(self, session_id: str, user_id: str) -> bool:
        """Delete chat session and all its messages"""
        try:
            # Delete all messages in the session
            self.supabase.table('query_history').delete().eq('session_id', session_id).eq('user_id', user_id).execute()
            
            # Delete the session
            result = self.supabase.table('chat_sessions').delete().eq('id', session_id).eq('user_id', user_id).execute()
            
            if not result.data:
                raise Exception("Session not found or not authorized")
            
            logger.info(f"Deleted chat session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting chat session: {str(e)}")
            raise Exception(f"Failed to delete chat session: {str(e)}")
    
    async def get_session_documents(self, session_id: str, user_id: str) -> List[Dict]:
        """Get all documents uploaded in this session"""
        try:
            result = self.supabase.table('documents').select(
                'id, title, file_name, file_type, file_size, upload_date, processing_status'
            ).eq('chat_session_id', session_id).eq('user_id', user_id).execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error getting session documents: {str(e)}")
            raise Exception(f"Failed to retrieve session documents: {str(e)}")
    
    async def get_session_stats(self, session_id: str, user_id: str) -> Dict:
        """Get session statistics"""
        try:
            # Get message counts
            messages = self.supabase.table('query_history').select('message_type', count='exact').eq('session_id', session_id).eq('user_id', user_id).execute()
            
            # Get document count
            documents = self.supabase.table('documents').select('id', count='exact').eq('chat_session_id', session_id).eq('user_id', user_id).execute()
            
            # Get session info
            session_info = self.supabase.table('chat_sessions').select('created_at, updated_at').eq('id', session_id).eq('user_id', user_id).execute()
            
            return {
                'total_messages': messages.count,
                'total_documents': documents.count,
                'created_at': session_info.data[0]['created_at'] if session_info.data else None,
                'last_activity': session_info.data[0]['updated_at'] if session_info.data else None
            }
            
        except Exception as e:
            logger.error(f"Error getting session stats: {str(e)}")
            raise Exception(f"Failed to get session statistics: {str(e)}")
    
    async def search_chat_history(self, user_id: str, query: str, limit: int = 20) -> List[Dict]:
        """Search through user's chat history"""
        try:
            # Search in query_text and response_text
            result = self.supabase.table('query_history').select(
                'id, session_id, query_text, response_text, message_type, created_at'
            ).eq('user_id', user_id).or_(
                f'query_text.ilike.%{query}%,response_text.ilike.%{query}%'
            ).order('created_at', desc=True).limit(limit).execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error searching chat history: {str(e)}")
            raise Exception(f"Failed to search chat history: {str(e)}")