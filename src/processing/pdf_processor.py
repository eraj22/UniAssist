"""
Step 1: PDF Processing Module
Extracts text, images, and metadata from PDFs
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, List, Optional
import json
import re
from datetime import datetime


class PDFProcessor:
    """Process academic PDFs - extract text, images, and metadata"""
    
    def __init__(self, output_dir: str = "data/processed"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.images_dir = self.output_dir / "extracted_images"
        self.images_dir.mkdir(exist_ok=True)
    
    def process_pdf(self, pdf_path: str, doc_type: str = "unknown") -> Optional[Dict]:
        """
        Process a single PDF file
        
        Args:
            pdf_path: Path to PDF file
            doc_type: Type (past_paper, notes, slides, handbook, course_outline)
            
        Returns:
            Dictionary with extracted content
        """
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            print(f"✗ PDF not found: {pdf_path}")
            return None
        
        print(f"\nProcessing: {pdf_path.name}")
        print(f"  Type: {doc_type}")
        
        try:
            doc = fitz.open(pdf_path)
            
            # Get total pages first
            total_pages = len(doc)
            
            # Extract metadata
            metadata = self._extract_metadata(doc, pdf_path, doc_type)
            
            # Extract text from all pages
            pages_content = []
            total_images = 0
            
            for page_num in range(total_pages):
                page_data = self._extract_page_content(doc, page_num, pdf_path.stem)
                pages_content.append(page_data)
                total_images += page_data['images_count']
            
            # Combine all text
            full_text = "\n\n".join([p['text'] for p in pages_content if p['text']])
            
            # Detect if it's a past paper (has questions)
            is_past_paper = self._detect_past_paper(full_text)
            if is_past_paper:
                metadata['doc_type'] = 'past_paper'
                # Extract questions
                questions = self._extract_questions(full_text)
                metadata['questions_detected'] = len(questions)
            
            # Create result BEFORE closing doc
            result = {
                'filename': pdf_path.name,
                'path': str(pdf_path),
                'metadata': metadata,
                'pages': pages_content,
                'full_text': full_text,
                'total_pages': total_pages,
                'total_images': total_images,
                'word_count': len(full_text.split()),
                'processed_at': datetime.now().isoformat()
            }
            
            # Close document
            doc.close()
            
            print(f"  ✓ Extracted: {total_pages} pages, {result['word_count']} words, {total_images} images")
            
            return result
            
        except Exception as e:
            print(f"  ✗ Error processing {pdf_path.name}: {e}")
            return None
    
    def _extract_metadata(self, doc, pdf_path: Path, doc_type: str) -> Dict:
        """Extract PDF metadata"""
        pdf_metadata = doc.metadata or {}
        
        return {
            'title': pdf_metadata.get('title') or pdf_path.stem.replace('_', ' '),
            'author': pdf_metadata.get('author', 'Unknown'),
            'subject': pdf_metadata.get('subject', ''),
            'doc_type': doc_type,
            'course': 'Programming Fundamentals',
            'course_code': 'CS-101',
            'language': 'C++'
        }
    
    def _extract_page_content(self, doc, page_num: int, doc_id: str) -> Dict:
        """Extract content from a single page"""
        page = doc[page_num]
        
        # Extract text
        text = page.get_text("text")
        
        # Extract images
        images = self._extract_images_from_page(page, doc_id, page_num)
        
        return {
            'page_number': page_num + 1,
            'text': text.strip(),
            'images': images,
            'images_count': len(images),
            'char_count': len(text)
        }
    
    def _extract_images_from_page(self, page, doc_id: str, page_num: int) -> List[Dict]:
        """Extract images from a PDF page"""
        images_data = []
        
        try:
            image_list = page.get_images()
            
            for img_index, img in enumerate(image_list):
                try:
                    xref = img[0]
                    base_image = page.parent.extract_image(xref)
                    
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    
                    # Save image
                    img_filename = f"{doc_id}_p{page_num+1}_img{img_index+1}.{image_ext}"
                    img_path = self.images_dir / img_filename
                    
                    with open(img_path, "wb") as f:
                        f.write(image_bytes)
                    
                    images_data.append({
                        'filename': img_filename,
                        'path': str(img_path),
                        'page': page_num + 1,
                        'index': img_index + 1
                    })
                    
                except Exception as e:
                    continue
                    
        except Exception as e:
            pass
        
        return images_data
    
    def _detect_past_paper(self, text: str) -> bool:
        """Detect if document is a past paper"""
        indicators = [
            r'Q\d+[\.\):]',  # Q1. Q2: Q3)
            r'Question\s+\d+',
            r'Total\s+Marks',
            r'Exam\s+Time',
            r'Final\s+Exam',
            r'Midterm\s+Exam',
            r'Quiz'
        ]
        
        for pattern in indicators:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _extract_questions(self, text: str) -> List[str]:
        """Extract question numbers/markers from text"""
        questions = []
        
        # Pattern: Q1, Q2, Question 1, etc.
        pattern = r'(Q\d+|Question\s+\d+)[\.\):]'
        matches = re.finditer(pattern, text, re.IGNORECASE)
        
        for match in matches:
            questions.append(match.group(0))
        
        return questions
    
    def process_directory(self, directory: str, doc_type: str = "unknown") -> List[Dict]:
        """
        Process all PDFs in a directory
        
        Args:
            directory: Path to directory containing PDFs
            doc_type: Document type
            
        Returns:
            List of processed documents
        """
        directory = Path(directory)
        
        if not directory.exists():
            print(f"✗ Directory not found: {directory}")
            return []
        
        pdf_files = list(directory.glob("*.pdf"))
        
        if not pdf_files:
            print(f"✗ No PDF files found in {directory}")
            return []
        
        print(f"\nFound {len(pdf_files)} PDF files in {directory}")
        print("="*70)
        
        processed_docs = []
        
        for pdf_file in pdf_files:
            result = self.process_pdf(pdf_file, doc_type)
            if result:
                processed_docs.append(result)
        
        print("\n" + "="*70)
        print(f"✓ Successfully processed {len(processed_docs)}/{len(pdf_files)} files")
        
        return processed_docs
    
    def save_processed_data(self, processed_docs: List[Dict], output_file: str = "processed_pdfs.json"):
        """Save processed documents to JSON"""
        output_path = self.output_dir / output_file
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(processed_docs, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Saved processed data to: {output_path}")
        return output_path


def main():
    """Test the PDF processor"""
    
    processor = PDFProcessor()
    
    print("="*70)
    print("PDF PROCESSOR - STEP 1")
    print("="*70)
    
    # Process past papers
    print("\n📄 Processing Past Papers...")
    past_papers = processor.process_directory("data/raw/past_papers", doc_type="past_paper")
    
    # Process GeeksforGeeks text files as "notes"
    # (We'll convert them to understand later, for now just PDFs)
    
    # Save all processed data
    if past_papers:
        processor.save_processed_data(past_papers, "past_papers_processed.json")
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Past Papers Processed: {len(past_papers)}")
    print(f"Total Pages: {sum(d['total_pages'] for d in past_papers)}")
    print(f"Total Words: {sum(d['word_count'] for d in past_papers):,}")
    print(f"Total Images: {sum(d['total_images'] for d in past_papers)}")
    print("="*70)
    
    print("\n✓ STEP 1 COMPLETE!")
    print("\nNext: Run text chunking (Step 2)")


if __name__ == "__main__":
    main()