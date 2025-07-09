class HybridSearchService:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()
    
    async def hybrid_search(self, query: str, user_id: str,
                          include_public: bool = True,
                          include_user_docs: bool = True,
                          session_id: str = None,
                          limit: int = 10) -> Dict:
        """
        Search across user documents and public knowledge base
        """
        query_embedding = await self.embedding_service.generate_query_embedding(query)
        
        results = {
            'public_results': [],
            'user_results': [],
            'session_results': []
        }
        
        if include_public:
            results['public_results'] = await self.vector_store.search_public_documents(
                query_embedding, limit=limit//2
            )
        
        if include_user_docs:
            results['user_results'] = await self.vector_store.search_user_documents(
                query_embedding, user_id, limit=limit//2
            )
        
        if session_id:
            results['session_results'] = await self.vector_store.search_session_documents(
                query_embedding, session_id, limit=limit//3
            )
        
        # Combine and rank results
        combined_results = self._combine_and_rank_results(results)
        return combined_results
    
    def _combine_and_rank_results(self, results: Dict) -> List[Dict]:
        """Combine results from different sources and rank by relevance"""
        pass