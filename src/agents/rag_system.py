"""
Step 4: Complete RAG Agent System
Multi-agent system for Programming Fundamentals course assistant
"""

import requests
import json
from pathlib import Path
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
import chromadb


class RetrieverAgent:
    """Retrieves relevant chunks from vector store"""
    
    def __init__(self, chroma_path: str = "data/chroma_db"):
        print("Initializing Retriever Agent...")
        
        # Load embedding model
        self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        
        # Connect to ChromaDB
        self.client = chromadb.PersistentClient(path=chroma_path)
        self.collection = self.client.get_collection(name="pf_course_docs")
        
        print(f"✓ Connected to vector store ({self.collection.count()} documents)")
    
    def retrieve(self, query: str, n_results: int = 5, filter_dict: Dict = None) -> List[Dict]:
        """
        Retrieve relevant documents for a query
        
        Args:
            query: User question
            n_results: Number of results to return
            filter_dict: Optional metadata filter
            
        Returns:
            List of relevant documents with metadata
        """
        # Generate query embedding
        query_embedding = self.model.encode([query])[0].tolist()
        
        # Search vector store
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filter_dict
        )
        
        # Format results
        retrieved_docs = []
        if results['documents'] and results['documents'][0]:
            for doc, metadata, distance in zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            ):
                retrieved_docs.append({
                    'text': doc,
                    'metadata': metadata,
                    'relevance_score': 1 - distance  # Convert distance to similarity
                })
        
        return retrieved_docs


class AnswerAgent:
    """Generates answers using Ollama LLM"""
    
    def __init__(self, model_name: str = "llama3.2:1b", ollama_url: str = "http://localhost:11434"):
        print("Initializing Answer Agent...")
        self.model_name = model_name
        self.ollama_url = ollama_url
        self.api_endpoint = f"{ollama_url}/api/generate"
        
        # Test connection
        try:
            response = requests.get(f"{ollama_url}/api/tags", timeout=5)
            print(f"✓ Connected to Ollama (model: {model_name})")
        except:
            print("⚠ Warning: Could not connect to Ollama. Make sure it's running.")
    
    def generate_answer(self, query: str, context_docs: List[Dict]) -> Dict:
        """
        Generate answer using retrieved context
        
        Args:
            query: User question
            context_docs: Retrieved documents from vector store
            
        Returns:
            Dictionary with answer and metadata
        """
        # Build context from retrieved documents
        context = self._build_context(context_docs)
        
        # Create prompt
        prompt = self._create_prompt(query, context)
        
        # Generate answer using Ollama
        answer = self._call_ollama(prompt)
        
        return {
            'question': query,
            'answer': answer,
            'sources': [doc['metadata']['source_document'] for doc in context_docs[:3]],
            'context_used': len(context_docs)
        }
    
    def _build_context(self, docs: List[Dict]) -> str:
        """Build context string from documents"""
        context_parts = []
        
        for i, doc in enumerate(docs, 1):
            source = doc['metadata'].get('source_document', 'Unknown')
            text = doc['text']
            context_parts.append(f"[Source {i}: {source}]\n{text}\n")
        
        return "\n".join(context_parts)
    
    def _create_prompt(self, query: str, context: str) -> str:
        """Create prompt for LLM"""
        prompt = f"""You are a helpful Programming Fundamentals (C++) teaching assistant. 
Answer the student's question using ONLY the provided context from past papers and course materials.

Context:
{context}

Student Question: {query}

Instructions:
- Provide a clear, accurate answer based on the context
- If the context contains code examples, explain them
- If you cannot answer from the context, say so
- Keep the answer concise but complete

Answer:"""
        
        return prompt
    
    def _call_ollama(self, prompt: str) -> str:
        """Call Ollama API"""
        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False
            }
            
            response = requests.post(self.api_endpoint, json=payload, timeout=180)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', 'No response generated')
            else:
                return f"Error: Could not generate answer (Status: {response.status_code})"
                
        except Exception as e:
            return f"Error calling Ollama: {str(e)}"


class QuizAgent:
    """Generates quizzes from course materials"""
    
    def __init__(self, answer_agent: AnswerAgent, retriever_agent: RetrieverAgent):
        print("Initializing Quiz Agent...")
        self.answer_agent = answer_agent
        self.retriever_agent = retriever_agent
        print("✓ Quiz Agent ready")
    
    def generate_quiz(self, topic: str, num_questions: int = 5) -> Dict:
        """
        Generate a quiz on a specific topic
        
        Args:
            topic: Topic for quiz (e.g., "pointers", "arrays", "loops")
            num_questions: Number of questions to generate
            
        Returns:
            Quiz dictionary with questions
        """
        # Retrieve relevant content
        docs = self.retriever_agent.retrieve(topic, n_results=10)
        
        if not docs:
            return {
                'topic': topic,
                'questions': [],
                'error': 'No relevant content found for this topic'
            }
        
        # Build context
        context = "\n\n".join([doc['text'] for doc in docs[:5]])
        
        # Create quiz generation prompt
        prompt = f"""Based on the following C++ programming content, generate {num_questions} multiple choice questions.

Content:
{context}

Generate {num_questions} questions in this EXACT format:
Q1: [Question text]
A) [Option A]
B) [Option B]
C) [Option C]
D) [Option D]
Correct: [A/B/C/D]

Q2: [Question text]
...

Topic: {topic}
Generate questions now:"""
        
        # Generate quiz
        quiz_text = self.answer_agent._call_ollama(prompt)
        
        # Parse questions (basic parsing)
        questions = self._parse_quiz(quiz_text)
        
        return {
            'topic': topic,
            'num_questions': len(questions),
            'questions': questions,
            'sources': [doc['metadata']['source_document'] for doc in docs[:3]]
        }
    
    def _parse_quiz(self, quiz_text: str) -> List[Dict]:
        """Parse generated quiz text into structured format"""
        questions = []
        lines = quiz_text.split('\n')
        
        current_q = None
        for line in lines:
            line = line.strip()
            
            if line.startswith('Q') and ':' in line:
                if current_q:
                    questions.append(current_q)
                current_q = {'question': line.split(':', 1)[1].strip(), 'options': {}}
            
            elif current_q and line.startswith(('A)', 'B)', 'C)', 'D)')):
                option = line[0]
                text = line[2:].strip()
                current_q['options'][option] = text
            
            elif current_q and line.startswith('Correct:'):
                current_q['correct'] = line.split(':')[1].strip()[0]
        
        if current_q:
            questions.append(current_q)
        
        return questions
    
    def grade_quiz(self, quiz: Dict, answers: Dict) -> Dict:
        """
        Grade a quiz submission
        
        Args:
            quiz: Quiz dictionary from generate_quiz
            answers: Dictionary mapping question numbers to answers {1: 'A', 2: 'B', ...}
            
        Returns:
            Grading results
        """
        results = []
        correct_count = 0
        
        for i, question in enumerate(quiz['questions'], 1):
            user_answer = answers.get(i)
            correct_answer = question.get('correct')
            
            is_correct = user_answer == correct_answer
            if is_correct:
                correct_count += 1
            
            results.append({
                'question_num': i,
                'question': question['question'],
                'user_answer': user_answer,
                'correct_answer': correct_answer,
                'is_correct': is_correct
            })
        
        total = len(quiz['questions'])
        score = (correct_count / total * 100) if total > 0 else 0
        
        return {
            'total_questions': total,
            'correct': correct_count,
            'incorrect': total - correct_count,
            'score': score,
            'results': results
        }


class SummaryAgent:
    """Generates summaries of documents"""
    
    def __init__(self, answer_agent: AnswerAgent):
        print("Initializing Summary Agent...")
        self.answer_agent = answer_agent
        print("✓ Summary Agent ready")
    
    def summarize_document(self, text: str, summary_type: str = "concise") -> str:
        """
        Summarize a document
        
        Args:
            text: Document text to summarize
            summary_type: "concise", "detailed", or "bullet_points"
            
        Returns:
            Summary text
        """
        if summary_type == "concise":
            instruction = "Provide a concise 3-4 sentence summary"
        elif summary_type == "detailed":
            instruction = "Provide a detailed paragraph summary"
        else:  # bullet_points
            instruction = "Provide a summary in bullet points (5-7 key points)"
        
        prompt = f"""Summarize the following C++ programming content.

{instruction}:

Content:
{text[:3000]}

Summary:"""
        
        summary = self.answer_agent._call_ollama(prompt)
        return summary


# Main RAG System
class PFCourseAssistant:
    """Complete Programming Fundamentals Course Assistant"""
    
    def __init__(self):
        print("="*70)
        print("INITIALIZING PF COURSE ASSISTANT")
        print("="*70)
        
        # Initialize all agents
        self.retriever = RetrieverAgent()
        self.answer_agent = AnswerAgent()
        self.quiz_agent = QuizAgent(self.answer_agent, self.retriever)
        self.summary_agent = SummaryAgent(self.answer_agent)
        
        print("\n✓ All agents initialized!")
        print("="*70)
    
    def ask(self, question: str) -> Dict:
        """Ask a question about the course"""
        print(f"\nQuestion: {question}")
        
        # Retrieve relevant context
        docs = self.retriever.retrieve(question, n_results=5)
        
        if not docs:
            return {'error': 'No relevant information found'}
        
        # Generate answer
        result = self.answer_agent.generate_answer(question, docs)
        
        return result
    
    def generate_quiz(self, topic: str, num_questions: int = 5) -> Dict:
        """Generate a quiz on a topic"""
        return self.quiz_agent.generate_quiz(topic, num_questions)
    
    def grade_quiz(self, quiz: Dict, answers: Dict) -> Dict:
        """Grade a quiz"""
        return self.quiz_agent.grade_quiz(quiz, answers)
    
    def summarize(self, text: str, summary_type: str = "concise") -> str:
        """Summarize text"""
        return self.summary_agent.summarize_document(text, summary_type)


def main():
    """Test the RAG system"""
    
    print("\n" + "="*70)
    print("STEP 4: RAG SYSTEM TEST")
    print("="*70)
    
    # Initialize assistant
    assistant = PFCourseAssistant()
    
    # Test 1: Ask a question
    print("\n" + "="*70)
    print("TEST 1: Question Answering")
    print("="*70)
    
    result = assistant.ask("What are pointers in C++?")
    print(f"\nAnswer: {result['answer']}")
    print(f"Sources: {', '.join(result['sources'])}")
    
    # Test 2: Generate quiz
    print("\n" + "="*70)
    print("TEST 2: Quiz Generation")
    print("="*70)
    
    quiz = assistant.generate_quiz("arrays", num_questions=3)
    print(f"\nTopic: {quiz['topic']}")
    print(f"Generated {quiz['num_questions']} questions")
    
    if quiz['questions']:
        for i, q in enumerate(quiz['questions'], 1):
            print(f"\nQ{i}: {q['question']}")
            for opt, text in q.get('options', {}).items():
                print(f"  {opt}) {text}")
    
    print("\n" + "="*70)
    print("✓ STEP 4 COMPLETE!")
    print("="*70)
    print("\nYour RAG system is working!")
    print("Next: Build FastAPI backend (Step 5)")


if __name__ == "__main__":
    main()