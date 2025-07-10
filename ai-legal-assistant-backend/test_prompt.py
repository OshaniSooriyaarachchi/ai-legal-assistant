"""
Test script to verify the prompt template changes work correctly
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.prompt_templates import PromptTemplates

def test_prompt_changes():
    print("=== TESTING PROMPT TEMPLATE CHANGES ===")
    
    templates = PromptTemplates()
    
    # Test data
    query = "give me a summary about Manual of Conducting Examination document"
    context = """=== LEGAL KNOWLEDGE BASE ===
Source: University Manual (General)
Content: This manual contains procedures for conducting examinations in universities.
---

=== YOUR DOCUMENTS ===
Source: Manual of Conducting Examinations.pdf
Content: The manual outlines examination procedures, examiner selection, and result publication processes.
---"""
    
    # Generate hybrid prompt
    prompt = templates.create_hybrid_rag_prompt(
        query=query,
        context=context,
        session_context="",
        conversation_history=""
    )
    
    print("Generated Prompt:")
    print("=" * 50)
    print(prompt)
    print("=" * 50)
    
    # Check for problematic phrases
    problematic_phrases = [
        "clearly state limitations",
        "cannot find the answer",
        "suggest consulting with a qualified attorney",
        "If the context doesn't contain sufficient information",
        "access limitations"
    ]
    
    found_issues = []
    for phrase in problematic_phrases:
        if phrase.lower() in prompt.lower():
            found_issues.append(phrase)
    
    if found_issues:
        print(f"❌ ISSUES FOUND: The following problematic phrases are still in the prompt:")
        for issue in found_issues:
            print(f"   - {issue}")
    else:
        print("✅ SUCCESS: No problematic phrases found in the prompt!")
    
    # Check for positive instructions
    positive_phrases = [
        "provide comprehensive",
        "maximum value",
        "actionable insights",
        "do not mention access limitations"
    ]
    
    found_positive = []
    for phrase in positive_phrases:
        if phrase.lower() in prompt.lower():
            found_positive.append(phrase)
    
    print(f"\n✅ POSITIVE INSTRUCTIONS FOUND: {len(found_positive)}/{len(positive_phrases)}")
    for phrase in found_positive:
        print(f"   - {phrase}")

if __name__ == "__main__":
    test_prompt_changes()
