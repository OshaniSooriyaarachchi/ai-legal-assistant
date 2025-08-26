import logging
from typing import Dict, List, Optional
from services.embedding_service import EmbeddingService
from services.vector_store import VectorStore
from services.chat_service import ChatService

logger = logging.getLogger(__name__)

class HybridSearchService:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()
        self.chat_service = ChatService()
    
    async def hybrid_search(self, query: str, user_id: str,
                          include_public: bool = True,
                          include_user_docs: bool = True,
                          session_id: str = None,
                          limit: int = 10) -> Dict:
        """
        Search across user documents and public knowledge base
        """
        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.generate_query_embedding(query)
            
            results = {
                'public_results': [],
                'user_results': [],
                'session_results': []
            }
             # Search public documents (common knowledge base)
            if include_public:
                try:
                    results['public_results'] = await self.vector_store.search_public_documents(
                        query_embedding, limit=limit//2, similarity_threshold=0.5  # Lower threshold
                    )
                    logger.info(f"Public search results: Found {len(results['public_results'])} documents")
                    for i, result in enumerate(results['public_results'][:3]):  # Log first 3 results
                        similarity = result.get('similarity_score', result.get('similarity', 'N/A'))
                        doc_title = result.get('document_title', 'Unknown')
                        logger.info(f"  Public result {i+1}: '{doc_title}' (similarity: {similarity})")
                except Exception as e:
                    logger.warning(f"Error searching public documents: {str(e)}")
                    results['public_results'] = []

            # Search user's private documents
            if include_user_docs:
                try:
                    results['user_results'] = await self.vector_store.search_user_documents(
                        query_embedding, user_id, limit=limit//2, similarity_threshold=0.5  # Lower threshold
                    )
                    logger.info(f"User search results: Found {len(results['user_results'])} documents for user_id: {user_id}")
                    if len(results['user_results']) == 0:
                        logger.warning(f"No user documents found for user_id: {user_id}. Check if documents are properly stored.")
                    for i, result in enumerate(results['user_results'][:5]):  # Log first 5 results
                        similarity = result.get('similarity_score', result.get('similarity', 'N/A'))
                        doc_title = result.get('document_title', result.get('filename', 'Unknown'))
                        chunk_preview = result.get('chunk_content', result.get('chunk_text', ''))[:100]
                        logger.info(f"  User result {i+1}: '{doc_title}' (similarity: {similarity})")
                        logger.debug(f"    Chunk preview: {chunk_preview}...")
                except Exception as e:
                    logger.warning(f"Error searching user documents: {str(e)}")
                    results['user_results'] = []

            # Search documents in current session
            if session_id:
                try:
                    results['session_results'] = await self.vector_store.search_session_documents(
                        query_embedding, session_id, limit=limit//3
                    )
                    logger.info(f"Session search results: Found {len(results['session_results'])} documents for session_id: {session_id}")
                    for i, result in enumerate(results['session_results'][:3]):  # Log first 3 results
                        similarity = result.get('similarity_score', result.get('similarity', 'N/A'))
                        doc_title = result.get('document_title', 'Unknown')
                        logger.info(f"  Session result {i+1}: '{doc_title}' (similarity: {similarity})")
                except Exception as e:
                    logger.warning(f"Error searching session documents: {str(e)}")
                    results['session_results'] = []
            
            # Combine and rank results
            combined_results = self._combine_and_rank_results(results)
            
            # Log detailed search summary
            total_results = len(combined_results)
            logger.info(f"=== HYBRID SEARCH SUMMARY ===")
            logger.info(f"Query: '{query}'")
            logger.info(f"User ID: {user_id}")
            logger.info(f"Session ID: {session_id}")
            logger.info(f"Total combined results: {total_results}")
            logger.info(f"Results breakdown - Public: {len(results['public_results'])}, User: {len(results['user_results'])}, Session: {len(results['session_results'])}")
            
            if total_results > 0:
                logger.info("Top 5 final ranked results:")
                for i, result in enumerate(combined_results[:5]):
                    similarity = result.get('boosted_similarity', result.get('similarity_score', result.get('similarity', 'N/A')))
                    original_similarity = result.get('similarity_score', result.get('similarity', 'N/A'))
                    boost = result.get('authority_boost', 0)
                    source_type = result.get('source_type', 'unknown')
                    doc_title = result.get('document_title', result.get('filename', 'Unknown'))
                    logger.info(f"  Final result {i+1}: '{doc_title}' ({source_type}) - Final score: {similarity}, Original: {original_similarity}, Boost: {boost}")
            else:
                logger.warning("No results found in any source!")
                logger.warning("Possible issues:")
                logger.warning("  1. Document not properly stored in vector database")
                logger.warning("  2. Query embedding doesn't match document content")
                logger.warning("  3. Similarity threshold too high")
                logger.warning("  4. User ID mismatch")
            logger.info("=== END SEARCH SUMMARY ===")
            
            # Get session context if available
            session_context = ""
            if session_id:
                session_context = await self.chat_service.get_session_context(session_id)
            
            return {
                'query': query,
                'results': combined_results,
                'source_breakdown': {
                    'public_count': len(results['public_results']),
                    'user_count': len(results['user_results']),
                    'session_count': len(results['session_results']),
                    'total_count': len(combined_results)
                },
                'session_context': session_context,
                'search_params': {
                    'include_public': include_public,
                    'include_user_docs': include_user_docs,
                    'has_session': session_id is not None,
                    'limit': limit
                }
            }
            
        except Exception as e:
            logger.error(f"Error in hybrid search: {str(e)}")
            raise Exception(f"Hybrid search failed: {str(e)}")
    
    def _combine_and_rank_results(self, results: Dict) -> List[Dict]:
        """Combine results from different sources and rank by relevance"""
        combined = []
        
        logger.debug("=== COMBINING AND RANKING RESULTS ===")
        
        # Add public results with source labeling and boost
        for result in results.get('public_results', []):
            result['source_type'] = 'public'
            result['source_label'] = 'Common Knowledge Base'
            result['authority_boost'] = 0.1  # Boost for authoritative sources
            # Apply authority boost to similarity score
            if 'similarity' in result:
                result['boosted_similarity'] = result['similarity'] + result['authority_boost']
            else:
                result['boosted_similarity'] = result['authority_boost']
            combined.append(result)
        
        logger.debug(f"Added {len(results.get('public_results', []))} public results")
        
        # Add user results with source labeling
        for result in results.get('user_results', []):
            result['source_type'] = 'user'
            result['source_label'] = 'Your Documents'
            result['authority_boost'] = 0.05  # Slight boost for user docs
            if 'similarity' in result:
                result['boosted_similarity'] = result['similarity'] + result['authority_boost']
            else:
                result['boosted_similarity'] = result['authority_boost']
            combined.append(result)
        
        logger.debug(f"Added {len(results.get('user_results', []))} user results")
        
        # Add session results with source labeling and recency boost
        for result in results.get('session_results', []):
            result['source_type'] = 'session'
            result['source_label'] = 'Current Session'
            result['authority_boost'] = 0.15  # Higher boost for session relevance
            if 'similarity' in result:
                result['boosted_similarity'] = result['similarity'] + result['authority_boost']
            else:
                result['boosted_similarity'] = result['authority_boost']
            combined.append(result)
        
        logger.debug(f"Added {len(results.get('session_results', []))} session results")
        
        # Sort by boosted similarity score (highest first)
        combined.sort(key=lambda x: x.get('boosted_similarity', 0), reverse=True)
        
        logger.debug(f"Combined total results before deduplication: {len(combined)}")
        
        # Remove duplicates based on content similarity
        deduplicated = self._remove_duplicate_chunks(combined)
        
        logger.debug(f"Final results after deduplication: {len(deduplicated)}")
        
        return deduplicated
    
    def _remove_duplicate_chunks(self, results: List[Dict]) -> List[Dict]:
        """Remove duplicate or very similar chunks"""
        if not results:
            return results
        
        deduplicated = []
        seen_content = set()
        
        for result in results:
            content = result.get('chunk_content', '').strip().lower()
            
            # Create a simple hash for content comparison
            content_hash = hash(content[:200])  # Use first 200 chars for comparison
            
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                deduplicated.append(result)
        
        return deduplicated
    
    async def get_contextual_search_suggestions(self, query: str, user_id: str, session_id: str = None) -> List[str]:
        """Get search suggestions based on context"""
        try:
            suggestions = []
            
            # Get session context for suggestions
            if session_id:
                session_context = await self.chat_service.get_session_context(session_id, last_n_messages=3)
                if session_context:
                    # Extract key terms from recent conversation
                    # This is a simplified version - in production, you'd use more sophisticated NLP
                    words = session_context.lower().split()
                    legal_terms = [word for word in words if len(word) > 5 and word.isalpha()]
                    suggestions.extend(legal_terms[:3])
            
            # Add generic legal search suggestions
            legal_suggestions = [
                "legal procedures",
                "court requirements",
                "document validity",
                "legal obligations",
                "compliance requirements"
            ]
            
            # Filter out suggestions that are too similar to the current query
            query_lower = query.lower()
            filtered_suggestions = [s for s in legal_suggestions if s not in query_lower]
            suggestions.extend(filtered_suggestions[:3])
            
            return suggestions[:5]  # Return top 5 suggestions
            
        except Exception as e:
            logger.error(f"Error getting search suggestions: {str(e)}")
            return []
    
    async def get_search_analytics(self, user_id: str, days: int = 30) -> Dict:
        """Get search analytics for user"""
        try:
            # This would typically query a search analytics table
            # For now, we'll return basic statistics
            return {
                'total_searches': 0,
                'avg_results_per_search': 0,
                'most_common_queries': [],
                'source_usage': {
                    'public': 0,
                    'user': 0,
                    'session': 0
                },
                'period_days': days
            }
            
        except Exception as e:
            logger.error(f"Error getting search analytics: {str(e)}")
            return {}
    
    async def feedback_on_search_result(self, user_id: str, query: str, 
                                      result_id: str, rating: int, 
                                      feedback: str = None) -> bool:
        """Store feedback on search result quality"""
        try:
            # In production, this would store in a feedback table
            # For now, we'll just log it
            logger.info(f"Search feedback - User: {user_id}, Query: {query}, "
                       f"Result: {result_id}, Rating: {rating}, Feedback: {feedback}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing search feedback: {str(e)}")
            return False