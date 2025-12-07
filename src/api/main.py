"""
Step 5: FastAPI Backend for UniAssist
REST API for the RAG system
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.rag_system import PFCourseAssistant
from processing.pdf_processor import PDFProcessor
from processing.text_chunker import TextChunker
from embeddings.embedding_generator import EmbeddingGenerator

import uvicorn

# Initialize FastAPI app
app = FastAPI(
    title="UniAssist API",
    description="AI Assistant for Programming Fundamentals Course",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG system (global instance)
assistant = None


# Pydantic models for request/response
class QuestionRequest(BaseModel):
    question: str
    
class QuestionResponse(BaseModel):
    question: str
    answer: str
    sources: List[str]
    context_used: int

class QuizRequest(BaseModel):
    topic: str
    num_questions: int = 5

class QuizQuestion(BaseModel):
    question: str
    options: Dict[str, str]
    correct: Optional[str] = None

class QuizResponse(BaseModel):
    topic: str
    num_questions: int
    questions: List[Dict]
    sources: List[str]

class GradeRequest(BaseModel):
    quiz: Dict
    answers: Dict[int, str]

class GradeResponse(BaseModel):
    total_questions: int
    correct: int
    incorrect: int
    score: float
    results: List[Dict]

class SummaryRequest(BaseModel):
    text: str
    summary_type: str = "concise"  # concise, detailed, bullet_points

class SummaryResponse(BaseModel):
    summary: str
    summary_type: str


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize the RAG system on startup"""
    global assistant
    print("\n" + "="*70)
    print("STARTING UNIASSIST API SERVER")
    print("="*70)
    
    try:
        assistant = PFCourseAssistant()
        print("\n✓ UniAssist API is ready!")
        print("="*70)
    except Exception as e:
        print(f"\n✗ Error initializing assistant: {e}")
        print("Make sure:")
        print("  1. ChromaDB is populated (run embedding_generator.py)")
        print("  2. Ollama is running (ollama serve)")
        print("="*70)


# API Endpoints
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to UniAssist API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if assistant is None:
        raise HTTPException(status_code=503, detail="Assistant not initialized")
    
    return {
        "status": "healthy",
        "assistant": "ready",
        "vector_store": assistant.retriever.collection.count()
    }

@app.post("/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """
    Ask a question about the PF course
    
    Example:
    ```
    POST /ask
    {
        "question": "What are pointers in C++?"
    }
    ```
    """
    if assistant is None:
        raise HTTPException(status_code=503, detail="Assistant not initialized")
    
    try:
        result = assistant.ask(request.question)
        
        if 'error' in result:
            raise HTTPException(status_code=404, detail=result['error'])
        
        return QuestionResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/quiz/generate", response_model=QuizResponse)
async def generate_quiz(request: QuizRequest):
    """
    Generate a quiz on a specific topic
    
    Example:
    ```
    POST /quiz/generate
    {
        "topic": "pointers",
        "num_questions": 5
    }
    ```
    """
    if assistant is None:
        raise HTTPException(status_code=503, detail="Assistant not initialized")
    
    try:
        quiz = assistant.generate_quiz(request.topic, request.num_questions)
        
        if 'error' in quiz:
            raise HTTPException(status_code=404, detail=quiz['error'])
        
        return QuizResponse(**quiz)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/quiz/grade", response_model=GradeResponse)
async def grade_quiz(request: GradeRequest):
    """
    Grade a quiz submission
    
    Example:
    ```
    POST /quiz/grade
    {
        "quiz": {...},
        "answers": {
            1: "A",
            2: "B",
            3: "C"
        }
    }
    ```
    """
    if assistant is None:
        raise HTTPException(status_code=503, detail="Assistant not initialized")
    
    try:
        result = assistant.grade_quiz(request.quiz, request.answers)
        return GradeResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/summarize", response_model=SummaryResponse)
async def summarize_text(request: SummaryRequest):
    """
    Summarize a document or text
    
    Example:
    ```
    POST /summarize
    {
        "text": "Long text here...",
        "summary_type": "concise"
    }
    ```
    """
    if assistant is None:
        raise HTTPException(status_code=503, detail="Assistant not initialized")
    
    try:
        summary = assistant.summarize(request.text, request.summary_type)
        
        return SummaryResponse(
            summary=summary,
            summary_type=request.summary_type
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    doc_type: str = "notes"
):
    """
    Upload and process a PDF (student's own notes/slides)
    
    Example:
    ```
    POST /upload-pdf
    file: [PDF file]
    doc_type: "notes"
    ```
    """
    if assistant is None:
        raise HTTPException(status_code=503, detail="Assistant not initialized")
    
    try:
        # Save uploaded file temporarily
        temp_path = Path(f"data/temp/{file.filename}")
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Process PDF
        processor = PDFProcessor()
        processed_doc = processor.process_pdf(str(temp_path), doc_type)
        
        if not processed_doc:
            raise HTTPException(status_code=400, detail="Failed to process PDF")
        
        # Chunk the document
        chunker = TextChunker()
        chunks = chunker.chunk_document(processed_doc)
        
        # Add to vector store
        embedding_gen = EmbeddingGenerator()
        embedding_gen.add_chunks_to_vectorstore(chunks)
        
        # Clean up temp file
        temp_path.unlink()
        
        return {
            "status": "success",
            "filename": file.filename,
            "pages": processed_doc['total_pages'],
            "chunks_added": len(chunks),
            "message": f"PDF processed and added to knowledge base"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_statistics():
    """Get system statistics"""
    if assistant is None:
        raise HTTPException(status_code=503, detail="Assistant not initialized")
    
    try:
        stats = assistant.retriever.collection.count()
        
        return {
            "total_documents": stats,
            "system_status": "operational",
            "model": "llama3.2:1b"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def main():
    """Run the API server"""
    print("\n" + "="*70)
    print("STARTING UNIASSIST API")
    print("="*70)
    print("\nAPI will be available at:")
    print("  - Local:   http://localhost:8000")
    print("  - Docs:    http://localhost:8000/docs")
    print("  - Redoc:   http://localhost:8000/redoc")
    print("\nPress Ctrl+C to stop the server")
    print("="*70 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    main()