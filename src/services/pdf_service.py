import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import structlog
from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter as TextSplitter

from src.config import Config

logger = structlog.get_logger()

@dataclass
class PDFChunk:
    content: str
    page_number: int
    chunk_index: int
    metadata: Dict[str, Any]

class PDFService:
    
    def __init__(self):
        self.chunk_size = Config.PDF_CHUNK_SIZE
        self.chunk_overlap = Config.PDF_CHUNK_OVERLAP
        self.text_splitter = TextSplitter(
            chunk_size=Config.PDF_CHUNK_SIZE,
            chunk_overlap=Config.PDF_CHUNK_OVERLAP,
            separators=["\n\n", "\n", " ", ""]
        )
    
    def extract_text_from_pdf(self, pdf_path: str) -> Optional[List[PDFChunk]]:
        if not os.path.exists(pdf_path):
            logger.error(f"PDF file not found: {pdf_path}")
            return None
        
        try:
            reader = PdfReader(pdf_path)
            full_text = ""
            page_texts = []
            
            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text.strip():
                    page_texts.append((page_num, page_text))
                    full_text += page_text + "\n"
            
            if not full_text.strip():
                logger.warning(f"No text found in PDF: {pdf_path}")
                return None
            
            chunks = self.text_splitter.split_text(full_text)
            
            pdf_chunks = []
            for i, chunk in enumerate(chunks):
                page_num = self._estimate_page_number(chunk, page_texts)
                
                pdf_chunk = PDFChunk(
                    content=chunk.strip(),
                    page_number=page_num,
                    chunk_index=i,
                    metadata={
                        "source": pdf_path,
                        "total_pages": len(reader.pages),
                        "chunk_size": len(chunk)
                    }
                )
                pdf_chunks.append(pdf_chunk)
            
            logger.info(f"Successfully processed PDF: {len(pdf_chunks)} chunks created")
            return pdf_chunks
        
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {str(e)}")
            return None
    
    def _estimate_page_number(self, chunk: str, page_texts: List[tuple]) -> int:
        if not page_texts:
            return 0
        
        max_overlap = 0
        best_page = 0
        
        for page_num, page_text in page_texts:
            overlap = len(set(chunk.split()) & set(page_text.split()))
            if overlap > max_overlap:
                max_overlap = overlap
                best_page = page_num
        
        return best_page
    
    def process_pdf_directory(self, directory_path: str) -> List[PDFChunk]:
        """
        Process all PDF files in a directory.
        
        Args:
            directory_path: Path to directory containing PDF files
            
        Returns:
            List of all PDFChunk objects from all PDFs
        """
        if not os.path.exists(directory_path):
            logger.error(f"Directory not found: {directory_path}")
            return []
        
        all_chunks = []
        pdf_files = [f for f in os.listdir(directory_path) if f.lower().endswith('.pdf')]
        
        for pdf_file in pdf_files:
            pdf_path = os.path.join(directory_path, pdf_file)
            chunks = self.extract_text_from_pdf(pdf_path)
            if chunks:
                all_chunks.extend(chunks)
        
        logger.info(f"Processed {len(pdf_files)} PDF files, total chunks: {len(all_chunks)}")
        return all_chunks
    
    def get_pdf_summary(self, chunks: List[PDFChunk]) -> str:
        """Generate a summary of processed PDF chunks."""
        if not chunks:
            return "No PDF content available."
        
        sources = set()
        total_pages = set()
        
        for chunk in chunks:
            if "source" in chunk.metadata:
                sources.add(os.path.basename(chunk.metadata["source"]))
            if "total_pages" in chunk.metadata:
                total_pages.add(chunk.metadata["total_pages"])
        
        return f"""PDF Summary:
- Sources: {', '.join(sorted(sources))}
- Total chunks: {len(chunks)}
- Total pages: {sum(total_pages)}
- Average chunk size: {sum(len(chunk.content) for chunk in chunks) // len(chunks) if chunks else 0} characters"""
