"""
Step 3: Embedding Generation & Vector Store Setup
Generates embeddings and stores in ChromaDB
"""

import json
from pathlib import Path
from typing import List, Dict
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import time


class EmbeddingGenerator:
    """Generate embeddings and manage vector store"""
    
    def __init__(self, 
                 model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
                 chroma_path: str = "data/chroma_db"):
        """
        Initialize embedding generator
        
        Args:
            model_name: HuggingFace model name for embeddings
            chroma_path: Path to ChromaDB storage
        """
        print("Initializing Embedding Generator...")
        
        # Load embedding model
        print(f"  Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        print(f"  ✓ Model loaded (dimension: {self.model.get_sentence_embedding_dimension()})")
        
        # Initialize ChromaDB
        self.chroma_path = Path(chroma_path)
        self.chroma_path.mkdir(parents=True, exist_ok=True)
        
        print(f"  Initializing ChromaDB at: {self.chroma_path}")
        self.client = chromadb.PersistentClient(path=str(self.chroma_path))
        
        # Create or get collection
        self.collection_name = "pf_course_docs"
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Programming Fundamentals course documents"}
        )
        
        print(f"  ✓ ChromaDB collection: {self.collection_name}")
        print(f"  ✓ Current documents in collection: {self.collection.count()}")
    
    def generate_embeddings(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate embeddings for a list of texts
        
        Args:
            texts: List of text strings
            batch_size: Batch size for encoding
            
        Returns:
            List of embeddings
        """
        print(f"\nGenerating embeddings for {len(texts)} texts...")
        
        embeddings = []
        for i in tqdm(range(0, len(texts), batch_size), desc="Embedding batches"):
            batch = texts[i:i + batch_size]
            batch_embeddings = self.model.encode(batch, show_progress_bar=False)
            embeddings.extend(batch_embeddings.tolist())
        
        print(f"✓ Generated {len(embeddings)} embeddings")
        return embeddings
    
    def add_chunks_to_vectorstore(self, chunks: List[Dict]):
        """
        Add chunks to vector store with embeddings
        
        Args:
            chunks: List of chunk dictionaries
        """
        print("\n" + "="*70)
        print("ADDING CHUNKS TO VECTOR STORE")
        print("="*70)
        
        if not chunks:
            print("✗ No chunks to add")
            return
        
        # Prepare data
        texts = [chunk['text'] for chunk in chunks]
        
        # Generate embeddings
        embeddings = self.generate_embeddings(texts)
        
        # Prepare metadata
        metadatas = []
        for chunk in chunks:
            metadata = {
                'source_document': chunk['source_document'],
                'doc_type': chunk['doc_type'],
                'chunk_type': chunk['chunk_type'],
                'course': chunk['course'],
                'course_code': chunk['course_code'],
                'word_count': chunk['word_count']
            }
            
            # Add specific metadata based on chunk type
            if 'question_id' in chunk['metadata']:
                metadata['question_id'] = chunk['metadata']['question_id']
            if 'section_heading' in chunk['metadata']:
                metadata['section_heading'] = chunk['metadata']['section_heading']
            if 'page_number' in chunk['metadata']:
                metadata['page_number'] = str(chunk['metadata']['page_number'])
            
            metadatas.append(metadata)
        
        # Generate IDs
        ids = [f"chunk_{i}" for i in range(len(chunks))]
        
        # Add to ChromaDB
        print(f"\nAdding {len(chunks)} chunks to ChromaDB...")
        
        try:
            self.collection.add(
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            print(f"✓ Successfully added {len(chunks)} chunks to vector store")
            print(f"✓ Total documents in collection: {self.collection.count()}")
            
        except Exception as e:
            print(f"✗ Error adding to vector store: {e}")
    
    def search(self, query: str, n_results: int = 5, filter_dict: Dict = None) -> Dict:
        """
        Search the vector store
        
        Args:
            query: Search query
            n_results: Number of results to return
            filter_dict: Optional metadata filter
            
        Returns:
            Search results dictionary
        """
        print(f"\nSearching for: '{query}'")
        
        # Generate query embedding
        query_embedding = self.model.encode([query])[0].tolist()
        
        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filter_dict
        )
        
        return results
    
    def test_retrieval(self):
        """Test the retrieval system with sample queries"""
        print("\n" + "="*70)
        print("TESTING RETRIEVAL")
        print("="*70)
        
        test_queries = [
            "What are pointers in C++?",
            "Explain arrays",
            "How to write a for loop?",
            "What is the difference between pass by value and pass by reference?"
        ]
        
        for query in test_queries:
            print(f"\n{'='*70}")
            print(f"Query: {query}")
            print(f"{'='*70}")
            
            results = self.search(query, n_results=3)
            
            if results['documents'] and results['documents'][0]:
                for i, (doc, metadata, distance) in enumerate(zip(
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
                ), 1):
                    print(f"\nResult {i}:")
                    print(f"  Source: {metadata.get('source_document', 'Unknown')}")
                    print(f"  Type: {metadata.get('doc_type', 'Unknown')}")
                    print(f"  Distance: {distance:.4f}")
                    print(f"  Preview: {doc[:200]}...")
            else:
                print("  No results found")
    
    def get_statistics(self) -> Dict:
        """Get statistics about the vector store"""
        total_docs = self.collection.count()
        
        # Get sample to analyze
        sample = self.collection.get(limit=min(100, total_docs))
        
        stats = {
            'total_documents': total_docs,
            'collection_name': self.collection_name,
            'embedding_dimension': self.model.get_sentence_embedding_dimension(),
            'model_name': self.model._model_name if hasattr(self.model, '_model_name') else 'unknown'
        }
        
        # Count by document type
        if sample['metadatas']:
            doc_types = {}
            for metadata in sample['metadatas']:
                doc_type = metadata.get('doc_type', 'unknown')
                doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
            stats['document_types'] = doc_types
        
        return stats
    
    def print_statistics(self):
        """Print statistics about vector store"""
        stats = self.get_statistics()
        
        print("\n" + "="*70)
        print("VECTOR STORE STATISTICS")
        print("="*70)
        print(f"Collection: {stats['collection_name']}")
        print(f"Total documents: {stats['total_documents']}")
        print(f"Embedding dimension: {stats['embedding_dimension']}")
        print(f"Model: {stats['model_name']}")
        
        if 'document_types' in stats:
            print("\nDocument types in collection:")
            for doc_type, count in stats['document_types'].items():
                print(f"  {doc_type}: {count}")
        
        print("="*70)


def main():
    """Main function to run Step 3"""
    
    print("="*70)
    print("EMBEDDING GENERATION & VECTOR STORE - STEP 3")
    print("="*70)
    
    # Load chunks
    chunks_path = Path("data/processed/past_papers_chunks.json")
    
    if not chunks_path.exists():
        print(f"\n✗ Error: {chunks_path} not found")
        print("Please run Step 2 first (text_chunker.py)")
        return
    
    print(f"\nLoading chunks from: {chunks_path}")
    
    with open(chunks_path, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    
    print(f"✓ Loaded {len(chunks)} chunks")
    
    # Initialize embedding generator
    embedding_gen = EmbeddingGenerator()
    
    # Add chunks to vector store
    embedding_gen.add_chunks_to_vectorstore(chunks)
    
    # Print statistics
    embedding_gen.print_statistics()
    
    # Test retrieval
    embedding_gen.test_retrieval()
    
    print("\n" + "="*70)
    print("✓ STEP 3 COMPLETE!")
    print("="*70)
    print("\nVector store is ready!")
    print(f"Location: {embedding_gen.chroma_path}")
    print("\nNext: Build RAG agents (Step 4)")


if __name__ == "__main__":
    main()