"""
Test script to verify context building changes
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.rag_service import RAGService

def test_context_building():
    print("=== TESTING CONTEXT BUILDING CHANGES ===")
    
    rag_service = RAGService()
    
    # Test with empty chunks
    print("\n1. Testing with empty chunks:")
    empty_context = rag_service._build_hybrid_context([])
    print(f"Empty context result: '{empty_context}'")
    
    # Test with sample chunks
    print("\n2. Testing with sample chunks:")
    sample_chunks = [
        {
            'source_type': 'public',
            'document_title': 'University Examination Manual',
            'document_category': 'Education',
            'chunk_content': 'This manual provides guidelines for conducting university examinations.'
        },
        {
            'source_type': 'user',
            'document_title': 'Manual of Conducting Examinations.pdf',
            'chunk_content': 'The examination process involves multiple stages including preparation, conduct, and evaluation.'
        }
    ]
    
    context = rag_service._build_hybrid_context(sample_chunks)
    print("Generated context:")
    print("-" * 50)
    print(context)
    print("-" * 50)
    
    # Check for problematic phrases
    problematic_phrases = [
        "No relevant information found",
        "cannot find",
        "access limitations",
        "insufficient information"
    ]
    
    found_issues = []
    for phrase in problematic_phrases:
        if phrase.lower() in context.lower():
            found_issues.append(phrase)
    
    if found_issues:
        print(f"❌ ISSUES FOUND in context building:")
        for issue in found_issues:
            print(f"   - {issue}")
    else:
        print("✅ SUCCESS: Context building looks good!")

if __name__ == "__main__":
    test_context_building()
