"""
Streamlit UI for UniAssist
Frontend interface that connects to the FastAPI backend
"""

import streamlit as st
import requests
from typing import Dict, List
import json

# Configuration
API_BASE_URL = "http://localhost:8000"

# Page configuration
st.set_page_config(
    page_title="UniAssist - PF Course Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stButton>button {
        width: 100%;
        background-color: #1f77b4;
        color: white;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
    }
</style>
""", unsafe_allow_html=True)


def check_api_health():
    """Check if the API is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def ask_question(question: str) -> Dict:
    """Send question to API"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/ask",
            json={"question": question},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def generate_quiz(topic: str, num_questions: int) -> Dict:
    """Generate quiz via API"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/quiz/generate",
            json={"topic": topic, "num_questions": num_questions},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def grade_quiz(quiz: Dict, answers: Dict[int, str]) -> Dict:
    """Grade quiz via API"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/quiz/grade",
            json={"quiz": quiz, "answers": answers},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def summarize_text(text: str, summary_type: str) -> Dict:
    """Summarize text via API"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/summarize",
            json={"text": text, "summary_type": summary_type},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def upload_pdf(file, doc_type: str) -> Dict:
    """Upload PDF via API"""
    try:
        files = {"file": (file.name, file, "application/pdf")}
        data = {"doc_type": doc_type}
        response = requests.post(
            f"{API_BASE_URL}/upload-pdf",
            files=files,
            data=data,
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def get_stats() -> Dict:
    """Get system statistics"""
    try:
        response = requests.get(f"{API_BASE_URL}/stats", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}


# Main App
def main():
    # Header
    st.markdown('<p class="main-header">🎓 UniAssist - Programming Fundamentals Assistant</p>', 
                unsafe_allow_html=True)
    
    # Check API status
    api_healthy = check_api_health()
    
    if not api_healthy:
        st.error("⚠️ Cannot connect to API server. Please ensure the FastAPI server is running on http://localhost:8000")
        st.info("Run the server with: `python main.py`")
        return
    
    # Sidebar
    with st.sidebar:
        st.header("📚 Navigation")
        page = st.radio(
            "Choose a feature:",
            ["Ask Questions", "Generate Quiz", "Summarize Text", "Upload PDF", "Statistics"]
        )
        
        st.markdown("---")
        st.subheader("ℹ️ About")
        st.write("UniAssist is your AI-powered assistant for the Programming Fundamentals course.")
        
        # Display stats in sidebar
        stats = get_stats()
        if "error" not in stats:
            st.metric("Documents in KB", stats.get("total_documents", 0))
            st.caption(f"Model: {stats.get('model', 'N/A')}")
    
    # Main content area based on selected page
    if page == "Ask Questions":
        show_ask_questions()
    elif page == "Generate Quiz":
        show_generate_quiz()
    elif page == "Summarize Text":
        show_summarize_text()
    elif page == "Upload PDF":
        show_upload_pdf()
    elif page == "Statistics":
        show_statistics()


def show_ask_questions():
    """Ask Questions page"""
    st.header("💬 Ask Questions")
    st.write("Ask any question about the Programming Fundamentals course content.")
    
    # Initialize session state for chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # Question input
    question = st.text_input(
        "Your question:",
        placeholder="e.g., What are pointers in C++?",
        key="question_input"
    )
    
    col1, col2 = st.columns([1, 5])
    with col1:
        ask_button = st.button("🔍 Ask", type="primary")
    with col2:
        if st.button("🗑️ Clear History"):
            st.session_state.chat_history = []
            st.rerun()
    
    if ask_button and question:
        with st.spinner("Thinking..."):
            result = ask_question(question)
            
            if "error" in result:
                st.error(f"Error: {result['error']}")
            else:
                # Add to chat history
                st.session_state.chat_history.append({
                    "question": question,
                    "answer": result["answer"],
                    "sources": result["sources"],
                    "context_used": result["context_used"]
                })
    
    # Display chat history (most recent first)
    if st.session_state.chat_history:
        st.markdown("---")
        st.subheader("📜 Chat History")
        
        for i, chat in enumerate(reversed(st.session_state.chat_history)):
            with st.expander(f"Q: {chat['question']}", expanded=(i == 0)):
                st.markdown(f"**Answer:**\n\n{chat['answer']}")
                st.caption(f"📚 Sources used: {len(chat['sources'])} | Context chunks: {chat['context_used']}")
                if chat['sources']:
                    with st.expander("View Sources"):
                        for idx, source in enumerate(chat['sources'], 1):
                            st.text(f"{idx}. {source}")


def show_generate_quiz():
    """Generate Quiz page"""
    st.header("📝 Generate Quiz")
    st.write("Generate a quiz on any topic from the course material.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        topic = st.text_input(
            "Quiz Topic:",
            placeholder="e.g., pointers, arrays, loops",
            key="quiz_topic"
        )
    
    with col2:
        num_questions = st.slider(
            "Number of Questions:",
            min_value=3,
            max_value=10,
            value=5,
            key="num_questions"
        )
    
    if st.button("🎲 Generate Quiz", type="primary"):
        if not topic:
            st.warning("Please enter a topic!")
        else:
            with st.spinner("Generating quiz..."):
                quiz_data = generate_quiz(topic, num_questions)
                
                if "error" in quiz_data:
                    st.error(f"Error: {quiz_data['error']}")
                else:
                    st.session_state.current_quiz = quiz_data
                    st.session_state.quiz_answers = {}
                    st.success(f"✅ Generated {len(quiz_data['questions'])} questions on '{topic}'")
    
    # Display quiz if generated
    if "current_quiz" in st.session_state:
        st.markdown("---")
        st.subheader(f"Quiz: {st.session_state.current_quiz['topic']}")
        
        quiz_data = st.session_state.current_quiz
        
        # Display questions
        for idx, q in enumerate(quiz_data['questions'], 1):
            st.markdown(f"**Question {idx}:** {q['question']}")
            
            answer = st.radio(
                f"Select your answer for Q{idx}:",
                options=list(q['options'].keys()),
                format_func=lambda x: f"{x}: {q['options'][x]}",
                key=f"q_{idx}",
                label_visibility="collapsed"
            )
            
            st.session_state.quiz_answers[idx] = answer
            st.markdown("---")
        
        # Submit quiz
        if st.button("✅ Submit Quiz", type="primary"):
            with st.spinner("Grading..."):
                result = grade_quiz(quiz_data, st.session_state.quiz_answers)
                
                if "error" in result:
                    st.error(f"Error: {result['error']}")
                else:
                    st.session_state.quiz_result = result
                    st.rerun()
    
    # Display results if quiz submitted
    if "quiz_result" in st.session_state:
        result = st.session_state.quiz_result
        
        st.markdown("---")
        st.subheader("📊 Quiz Results")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Questions", result['total_questions'])
        col2.metric("Correct", result['correct'], delta=None)
        col3.metric("Incorrect", result['incorrect'], delta=None)
        col4.metric("Score", f"{result['score']:.1f}%", delta=None)
        
        # Detailed results
        with st.expander("📋 Detailed Results", expanded=True):
            for item in result['results']:
                if item['correct']:
                    st.success(f"✅ Q{item['question_num']}: {item['selected']} - Correct!")
                else:
                    st.error(f"❌ Q{item['question_num']}: {item['selected']} - Incorrect (Correct: {item['correct_answer']})")


def show_summarize_text():
    """Summarize Text page"""
    st.header("📄 Summarize Text")
    st.write("Summarize documents or long texts.")
    
    text = st.text_area(
        "Enter text to summarize:",
        height=200,
        placeholder="Paste your text here..."
    )
    
    summary_type = st.selectbox(
        "Summary Type:",
        ["concise", "detailed", "bullet_points"],
        format_func=lambda x: x.replace("_", " ").title()
    )
    
    if st.button("✨ Summarize", type="primary"):
        if not text:
            st.warning("Please enter some text to summarize!")
        else:
            with st.spinner("Summarizing..."):
                result = summarize_text(text, summary_type)
                
                if "error" in result:
                    st.error(f"Error: {result['error']}")
                else:
                    st.markdown("---")
                    st.subheader(f"Summary ({result['summary_type'].replace('_', ' ').title()})")
                    st.markdown(result['summary'])


def show_upload_pdf():
    """Upload PDF page"""
    st.header("📤 Upload PDF")
    st.write("Upload your own notes, slides, or study materials to enhance the knowledge base.")
    
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=["pdf"],
        help="Upload course notes, slides, or any relevant PDF document"
    )
    
    doc_type = st.selectbox(
        "Document Type:",
        ["notes", "slides", "textbook", "assignment", "other"],
        help="Categorize your document for better organization"
    )
    
    if uploaded_file is not None:
        st.info(f"📁 File: {uploaded_file.name} ({uploaded_file.size / 1024:.2f} KB)")
        
        if st.button("⬆️ Upload and Process", type="primary"):
            with st.spinner("Processing PDF..."):
                result = upload_pdf(uploaded_file, doc_type)
                
                if "error" in result:
                    st.error(f"Error: {result['error']}")
                else:
                    st.success("✅ PDF processed successfully!")
                    st.json({
                        "Filename": result['filename'],
                        "Pages": result['pages'],
                        "Chunks Added": result['chunks_added'],
                        "Status": result['status']
                    })


def show_statistics():
    """Statistics page"""
    st.header("📊 System Statistics")
    st.write("Overview of the UniAssist system.")
    
    stats = get_stats()
    
    if "error" in stats:
        st.error(f"Error fetching statistics: {stats['error']}")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "Total Documents in Knowledge Base",
                stats.get("total_documents", 0),
                help="Number of document chunks in the vector store"
            )
        
        with col2:
            st.metric(
                "System Status",
                stats.get("system_status", "Unknown").upper(),
                help="Current operational status"
            )
        
        st.markdown("---")
        
        st.subheader("🤖 Model Information")
        st.code(f"Model: {stats.get('model', 'N/A')}")
        
        st.markdown("---")
        
        st.subheader("🔗 API Endpoints")
        endpoints = [
            ("Health Check", "/health", "GET"),
            ("Ask Question", "/ask", "POST"),
            ("Generate Quiz", "/quiz/generate", "POST"),
            ("Grade Quiz", "/quiz/grade", "POST"),
            ("Summarize", "/summarize", "POST"),
            ("Upload PDF", "/upload-pdf", "POST"),
            ("Statistics", "/stats", "GET"),
        ]
        
        for name, endpoint, method in endpoints:
            st.text(f"{method:6} {endpoint:20} - {name}")


if __name__ == "__main__":
    main()