"""
Step 2: Text Chunking Module
Smart chunking for different document types
"""

import json
from pathlib import Path
from typing import List, Dict, Optional
import re


class TextChunker:
    """Smart text chunking for RAG system"""
    
    def __init__(self, 
                 chunk_size: int = 512, 
                 chunk_overlap: int = 50,
                 output_dir: str = "data/processed"):
        """
        Initialize chunker
        
        Args:
            chunk_size: Target chunk size in tokens (approximate)
            chunk_overlap: Overlap between chunks
            output_dir: Directory for output
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def chunk_document(self, document: Dict) -> List[Dict]:
        """
        Chunk a single document based on its type
        
        Args:
            document: Processed document dictionary
            
        Returns:
            List of chunks with metadata
        """
        doc_type = document['metadata'].get('doc_type', 'unknown')
        
        print(f"\nChunking: {document['filename']}")
        print(f"  Type: {doc_type}")
        
        if doc_type == 'past_paper':
            chunks = self._chunk_past_paper(document)
        elif doc_type == 'notes':
            chunks = self._chunk_notes(document)
        elif doc_type == 'slides':
            chunks = self._chunk_slides(document)
        else:
            # Default chunking
            chunks = self._chunk_generic(document)
        
        print(f"  ✓ Created {len(chunks)} chunks")
        
        return chunks
    
    def _chunk_past_paper(self, document: Dict) -> List[Dict]:
        """
        Smart chunking for past papers - chunk by questions
        """
        full_text = document['full_text']
        chunks = []
        
        # Try to split by questions
        question_pattern = r'(Q\d+[\.\):]|Question\s+\d+[\.\):])'
        
        parts = re.split(question_pattern, full_text, flags=re.IGNORECASE)
        
        if len(parts) > 3:  # Found questions
            current_chunk = ""
            current_question = None
            
            for i, part in enumerate(parts):
                if re.match(question_pattern, part, re.IGNORECASE):
                    # Save previous chunk
                    if current_chunk and current_question:
                        chunks.append(self._create_chunk(
                            text=current_chunk,
                            document=document,
                            chunk_type='question',
                            metadata={'question_id': current_question}
                        ))
                    current_question = part
                    current_chunk = part
                else:
                    current_chunk += part
            
            # Save last chunk
            if current_chunk and current_question:
                chunks.append(self._create_chunk(
                    text=current_chunk,
                    document=document,
                    chunk_type='question',
                    metadata={'question_id': current_question}
                ))
        else:
            # No clear questions, use generic chunking
            chunks = self._chunk_generic(document)
        
        return chunks
    
    def _chunk_notes(self, document: Dict) -> List[Dict]:
        """
        Smart chunking for notes - chunk by sections/headings
        """
        full_text = document['full_text']
        chunks = []
        
        # Try to split by headings (lines in ALL CAPS or with specific markers)
        lines = full_text.split('\n')
        
        current_section = ""
        current_heading = "Introduction"
        
        for line in lines:
            line_stripped = line.strip()
            
            # Check if it's a heading
            if self._is_heading(line_stripped):
                # Save previous section
                if current_section:
                    chunks.append(self._create_chunk(
                        text=current_section,
                        document=document,
                        chunk_type='section',
                        metadata={'section_heading': current_heading}
                    ))
                
                current_heading = line_stripped
                current_section = line_stripped + "\n"
            else:
                current_section += line + "\n"
            
            # If section gets too large, chunk it
            if len(current_section.split()) > self.chunk_size * 1.5:
                chunks.append(self._create_chunk(
                    text=current_section,
                    document=document,
                    chunk_type='section',
                    metadata={'section_heading': current_heading}
                ))
                current_section = ""
        
        # Save last section
        if current_section:
            chunks.append(self._create_chunk(
                text=current_section,
                document=document,
                chunk_type='section',
                metadata={'section_heading': current_heading}
            ))
        
        return chunks if chunks else self._chunk_generic(document)
    
    def _chunk_slides(self, document: Dict) -> List[Dict]:
        """
        Smart chunking for slides - one chunk per page
        """
        chunks = []
        
        for page in document['pages']:
            if page['text'].strip():
                chunks.append(self._create_chunk(
                    text=page['text'],
                    document=document,
                    chunk_type='slide',
                    metadata={
                        'page_number': page['page_number'],
                        'has_images': page['images_count'] > 0,
                        'images': page['images']
                    }
                ))
        
        return chunks
    
    def _chunk_generic(self, document: Dict) -> List[Dict]:
        """
        Generic chunking with sliding window
        """
        full_text = document['full_text']
        words = full_text.split()
        chunks = []
        
        start = 0
        chunk_id = 0
        
        while start < len(words):
            end = start + self.chunk_size
            chunk_words = words[start:end]
            chunk_text = ' '.join(chunk_words)
            
            chunks.append(self._create_chunk(
                text=chunk_text,
                document=document,
                chunk_type='generic',
                metadata={'chunk_id': chunk_id}
            ))
            
            chunk_id += 1
            start = end - self.chunk_overlap
        
        return chunks
    
    def _is_heading(self, line: str) -> bool:
        """Check if a line is a heading"""
        if not line or len(line) < 3:
            return False
        
        # Check for common heading patterns
        heading_patterns = [
            r'^[A-Z\s]{3,}$',  # ALL CAPS
            r'^\d+\.',  # 1. 2. 3.
            r'^Chapter\s+\d+',
            r'^Section\s+\d+',
            r'^[IVX]+\.',  # I. II. III.
        ]
        
        for pattern in heading_patterns:
            if re.match(pattern, line):
                return True
        
        return False
    
    def _create_chunk(self, text: str, document: Dict, chunk_type: str, metadata: Dict) -> Dict:
        """Create a chunk with metadata"""
        return {
            'text': text.strip(),
            'chunk_type': chunk_type,
            'word_count': len(text.split()),
            'char_count': len(text),
            'source_document': document['filename'],
            'doc_type': document['metadata']['doc_type'],
            'course': document['metadata']['course'],
            'course_code': document['metadata']['course_code'],
            'metadata': metadata
        }
    
    def chunk_all_documents(self, documents: List[Dict]) -> List[Dict]:
        """
        Chunk all documents
        
        Args:
            documents: List of processed documents
            
        Returns:
            List of all chunks
        """
        all_chunks = []
        
        print("\n" + "="*70)
        print("CHUNKING ALL DOCUMENTS")
        print("="*70)
        
        for doc in documents:
            chunks = self.chunk_document(doc)
            all_chunks.extend(chunks)
        
        print("\n" + "="*70)
        print(f"✓ Total chunks created: {len(all_chunks)}")
        print("="*70)
        
        return all_chunks
    
    def save_chunks(self, chunks: List[Dict], filename: str = "chunks.json"):
        """Save chunks to JSON file"""
        output_path = self.output_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Saved {len(chunks)} chunks to: {output_path}")
        return output_path
    
    def print_chunk_statistics(self, chunks: List[Dict]):
        """Print statistics about chunks"""
        print("\n" + "="*70)
        print("CHUNK STATISTICS")
        print("="*70)
        
        # Count by type
        chunk_types = {}
        for chunk in chunks:
            chunk_type = chunk['chunk_type']
            chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
        
        print("\nChunks by type:")
        for chunk_type, count in chunk_types.items():
            print(f"  {chunk_type}: {count}")
        
        # Count by document type
        doc_types = {}
        for chunk in chunks:
            doc_type = chunk['doc_type']
            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
        
        print("\nChunks by document type:")
        for doc_type, count in doc_types.items():
            print(f"  {doc_type}: {count}")
        
        # Average chunk size
        avg_words = sum(c['word_count'] for c in chunks) / len(chunks)
        print(f"\nAverage chunk size: {avg_words:.1f} words")
        
        print("="*70)


def main():
    """Test the text chunker"""
    
    print("="*70)
    print("TEXT CHUNKER - STEP 2")
    print("="*70)
    
    # Load processed documents
    processed_path = Path("data/processed/past_papers_processed.json")
    
    if not processed_path.exists():
        print(f"\n✗ Error: {processed_path} not found")
        print("Please run Step 1 first (pdf_processor.py)")
        return
    
    print(f"\nLoading processed documents from: {processed_path}")
    
    with open(processed_path, 'r', encoding='utf-8') as f:
        documents = json.load(f)
    
    print(f"✓ Loaded {len(documents)} documents")
    
    # Initialize chunker
    chunker = TextChunker(chunk_size=512, chunk_overlap=50)
    
    # Chunk all documents
    chunks = chunker.chunk_all_documents(documents)
    
    # Save chunks
    chunker.save_chunks(chunks, "past_papers_chunks.json")
    
    # Print statistics
    chunker.print_chunk_statistics(chunks)
    
    print("\n✓ STEP 2 COMPLETE!")
    print("\nNext: Generate embeddings (Step 3)")


if __name__ == "__main__":
    main()