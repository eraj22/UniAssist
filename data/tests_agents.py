"""
Complete Test Suite for UniAssist Multi-Agent System
Run this to verify all agents work correctly
"""

import sys
from src.agents import RetrieverAgent, AnswerAgent, QuizAgent, SummaryAgent


def test_retriever():
    """Test the retriever agent"""
    print("\n" + "="*70)
    print("🔍 TEST 1: RETRIEVER AGENT")
    print("="*70)
    
    try:
        retriever = RetrieverAgent(collection_name="pf_course_docs")
        
        # Get stats
        stats = retriever.get_document_stats()
        print(f"\n✅ Database loaded successfully")
        print(f"📊 Total chunks: {stats.get('total_chunks', 0)}")
        print(f"📚 Courses: {stats.get('courses', [])}")
        print(f"📄 Document types: {stats.get('document_types', {})}")
        
        # Test retrieval
        query = "What is a loop?"
        chunks = retriever.retrieve(query, top_k=3)
        
        print(f"\n🔍 Retrieved {len(chunks)} chunks for: '{query}'")
        if chunks:
            print(f"✅ Top result: {chunks[0]['text'][:100]}...")
            print(f"   Relevance: {chunks[0]['relevance_score']:.3f}")
        
        return True
    except Exception as e:
        print(f"❌ Retriever test failed: {e}")
        return False


def test_answer_agent():
    """Test the answer agent"""
    print("\n" + "="*70)
    print("💬 TEST 2: ANSWER AGENT")
    print("="*70)
    
    try:
        agent = AnswerAgent(model_name="llama3.2", collection_name="pf_course_docs")
        
        question = "What are loops in programming?"
        print(f"\n❓ Question: {question}")
        
        result = agent.answer(question, top_k=3)
        
        print(f"\n📝 Answer:\n{result['answer'][:500]}...")
        print(f"\n📚 Sources ({result['num_sources']}):")
        for src in result['sources'][:3]:
            print(f"  - {src['source']}")
        print(f"\n✅ Confidence: {result['confidence']}")
        
        return True
    except Exception as e:
        print(f"❌ Answer agent test failed: {e}")
        return False


def test_quiz_agent():
    """Test the quiz generation agent"""
    print("\n" + "="*70)
    print("📝 TEST 3: QUIZ AGENT")
    print("="*70)
    
    try:
        agent = QuizAgent(model_name="llama3.2", collection_name="pf_course_docs")
        
        print("\n🎯 Generating quiz on 'arrays'...")
        quiz = agent.generate_quiz("arrays", num_questions=3, difficulty="medium")
        
        if 'error' in quiz:
            print(f"⚠️ {quiz['error']}")
            return False
        
        print(f"\n✅ Generated {quiz['num_questions']} questions")
        print(f"📚 Topic: {quiz['topic']}")
        print(f"⚡ Difficulty: {quiz['difficulty']}")
        
        # Display first question
        if quiz['questions']:
            q = quiz['questions'][0]
            print(f"\n📌 Sample Question:")
            print(f"Q: {q['question']}")
            for letter, option in q['options'].items():
                print(f"  {letter}) {option}")
            print(f"  ✓ Correct: {q['correct_answer']}")
        
        # Test grading
        print("\n🎓 Testing auto-grading...")
        student_answers = {0: 'A', 1: 'B', 2: 'C'}
        results = agent.grade_quiz(quiz, student_answers)
        print(f"📊 Score: {results['score']}/{results['max_score']} ({results['percentage']}%)")
        
        return True
    except Exception as e:
        print(f"❌ Quiz agent test failed: {e}")
        return False


def test_summary_agent():
    """Test the summary agent"""
    print("\n" + "="*70)
    print("📄 TEST 4: SUMMARY AGENT")
    print("="*70)
    
    try:
        agent = SummaryAgent(model_name="llama3.2", collection_name="pf_course_docs")
        
        print("\n📚 Summarizing 'loops' topic...")
        result = agent.summarize_topic("loops in programming", summary_type="concise")
        
        if 'error' in result:
            print(f"⚠️ {result['error']}")
            return False
        
        print(f"\n📝 Summary:\n{result['summary'][:400]}...")
        print(f"\n📚 Sources: {', '.join(result['sources'][:3])}")
        
        return True
    except Exception as e:
        print(f"❌ Summary agent test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("="*70)
    print("🚀 UNIASSIST MULTI-AGENT SYSTEM TEST")
    print("="*70)
    
    # Check Ollama
    print("\n🔧 Checking Ollama connection...")
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            print("✅ Ollama is running")
        else:
            print("❌ Ollama not responding correctly")
            return
    except Exception as e:
        print(f"❌ Cannot connect to Ollama: {e}")
        print("   Make sure Ollama is running (ollama serve)")
        return
    
    # Run tests
    tests = [
        ("Retriever Agent", test_retriever),
        ("Answer Agent", test_answer_agent),
        ("Quiz Agent", test_quiz_agent),
        ("Summary Agent", test_summary_agent)
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except KeyboardInterrupt:
            print("\n\n⚠️ Tests interrupted by user")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Unexpected error in {name}: {e}")
            results[name] = False
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    for name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name:.<40} {status}")
    
    total = len(results)
    passed = sum(results.values())
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Multi-agent system is ready!")
        print("\n📌 Next steps:")
        print("   1. Test with your own questions")
        print("   2. Implement the API layer (FastAPI)")
        print("   3. Add more features")
    else:
        print("\n⚠️ Some tests failed. Please check the errors above.")


if __name__ == "__main__":
    main()