"""
Document extraction module for reading various file formats from the data folder.
Supports PDF, Word documents, Excel files, and text files.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional

import structlog

# Document extraction libraries
try:
    import PyPDF2

    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from docx import Document as DocxDocument

    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import openpyxl

    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

log = structlog.get_logger()


class DocumentExtractor:
    """
    Extracts text content from various document formats.

    Supported formats:
    - PDF (.pdf)
    - Word documents (.docx, .doc)
    - Excel spreadsheets (.xlsx, .xls)
    - Text files (.txt, .md)
    """

    def __init__(self, data_folder: str = "./data"):
        """
        Initialize the document extractor.

        Args:
            data_folder: Path to the folder containing documents to extract
        """
        self.data_folder = Path(data_folder)

        # Check for missing dependencies
        missing_deps = []
        if not PDF_AVAILABLE:
            missing_deps.append("PyPDF2 (for PDF support)")
        if not DOCX_AVAILABLE:
            missing_deps.append("python-docx (for Word support)")
        if not EXCEL_AVAILABLE:
            missing_deps.append("openpyxl (for Excel support)")

        if missing_deps:
            log.warning(
                "missing_dependencies",
                dependencies=missing_deps,
                message="Some document formats may not be supported",
            )

        log.info(
            "document_extractor_initialized",
            data_folder=str(self.data_folder),
            pdf_support=PDF_AVAILABLE,
            docx_support=DOCX_AVAILABLE,
            excel_support=EXCEL_AVAILABLE,
        )

    def extract_from_folder(self, folder_path: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Extract text from all supported documents in a folder.

        Args:
            folder_path: Path to folder (defaults to data_folder)

        Returns:
            List of dictionaries containing extracted text and metadata
        """
        if folder_path is None:
            folder_path = self.data_folder
        else:
            folder_path = Path(folder_path)

        if not folder_path.exists():
            log.error("folder_not_found", folder_path=str(folder_path))
            raise FileNotFoundError(f"Folder not found: {folder_path}")

        extracted_docs = []

        # Walk through all files in the folder
        for root, _, files in os.walk(folder_path):
            for filename in files:
                file_path = Path(root) / filename

                try:
                    extracted_text = self.extract_from_file(str(file_path))

                    if extracted_text:
                        doc_data = {
                            "file_path": str(file_path),
                            "file_name": filename,
                            "extracted_text": extracted_text,
                            "file_type": file_path.suffix.lower(),
                            "file_size": file_path.stat().st_size,
                        }
                        extracted_docs.append(doc_data)
                        log.info(
                            "document_extracted",
                            file_name=filename,
                            text_length=len(extracted_text),
                            file_type=file_path.suffix,
                        )

                except Exception as e:
                    log.warning("extraction_failed", file_path=str(file_path), error=str(e))

        log.info("extraction_completed", total_documents=len(extracted_docs))

        return extracted_docs

    def extract_from_file(self, file_path: str) -> str:
        """
        Extract text from a single file based on its extension.

        Args:
            file_path: Path to the file

        Returns:
            Extracted text content
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        extension = file_path.suffix.lower()

        # Route to appropriate extraction method
        if extension == ".pdf":
            return self._extract_pdf(file_path)
        elif extension in [".docx", ".doc"]:
            return self._extract_docx(file_path)
        elif extension in [".xlsx", ".xls"]:
            return self._extract_excel(file_path)
        elif extension in [".txt", ".md", ".text"]:
            return self._extract_text(file_path)
        else:
            log.warning("unsupported_file_type", file_path=str(file_path), extension=extension)
            return ""

    def _extract_pdf(self, file_path: Path) -> str:
        """Extract text from PDF files."""
        if not PDF_AVAILABLE:
            raise ImportError(
                "PyPDF2 is required for PDF extraction. Install with: pip install PyPDF2"
            )

        text_parts = []

        try:
            with open(file_path, "rb") as file:
                pdf_reader = PyPDF2.PdfReader(file)

                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text_parts.append(page.extract_text())

        except Exception as e:
            log.error("pdf_extraction_error", file_path=str(file_path), error=str(e))
            raise

        return "\n\n".join(text_parts)

    def _extract_docx(self, file_path: Path) -> str:
        """Extract text from Word documents."""
        if not DOCX_AVAILABLE:
            raise ImportError(
                "python-docx is required for Word extraction. Install with: pip install python-docx"
            )

        try:
            doc = DocxDocument(file_path)
            text_parts = [paragraph.text for paragraph in doc.paragraphs]
            return "\n\n".join(text_parts)

        except Exception as e:
            log.error("docx_extraction_error", file_path=str(file_path), error=str(e))
            raise

    def _extract_excel(self, file_path: Path) -> str:
        """Extract text from Excel spreadsheets."""
        if not EXCEL_AVAILABLE:
            raise ImportError(
                "openpyxl is required for Excel extraction. Install with: pip install openpyxl"
            )

        try:
            workbook = openpyxl.load_workbook(file_path, data_only=True)
            text_parts = []

            for sheet_name in workbook.sheetnames:
                sheet = workbook[sheet_name]
                text_parts.append(f"=== Sheet: {sheet_name} ===\n")

                for row in sheet.iter_rows(values_only=True):
                    # Filter out None values and convert to strings
                    row_values = [str(cell) for cell in row if cell is not None]
                    if row_values:
                        text_parts.append(" | ".join(row_values))

            return "\n".join(text_parts)

        except Exception as e:
            log.error("excel_extraction_error", file_path=str(file_path), error=str(e))
            raise

    def _extract_text(self, file_path: Path) -> str:
        """Extract text from plain text files."""
        try:
            with open(file_path, encoding="utf-8") as file:
                return file.read()

        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, encoding="latin-1") as file:
                    return file.read()
            except Exception as e:
                log.error("text_extraction_error", file_path=str(file_path), error=str(e))
                raise

        except Exception as e:
            log.error("text_extraction_error", file_path=str(file_path), error=str(e))
            raise
