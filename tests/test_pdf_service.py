import pytest
import os
from unittest.mock import Mock, patch, mock_open, MagicMock
from src.services.pdf_service import PDFService

class TestPDFService:
    
    @pytest.fixture
    def pdf_service(self):
        return PDFService()
    
    def test_extract_text_from_pdf_success(self, pdf_service):
        with patch('src.services.pdf_service.PdfReader') as mock_reader:
            mock_page = Mock()
            mock_page.extract_text.return_value = "Sample PDF content for testing"
            
            mock_pdf = Mock()
            mock_pdf.pages = [mock_page, mock_page]
            mock_reader.return_value = mock_pdf
            
            with patch('os.path.exists', return_value=True):
                result = pdf_service.extract_text_from_pdf("test.pdf")
                
                assert result is not None
                assert len(result) >= 1
    
    def test_extract_text_from_pdf_file_not_found(self, pdf_service):
        result = pdf_service.extract_text_from_pdf("nonexistent.pdf")
        
        assert result is None
    
    def test_text_splitter_initialization(self, pdf_service):
        assert pdf_service.text_splitter is not None
        assert pdf_service.chunk_size > 0
        assert pdf_service.chunk_overlap >= 0
