"""
PDF Parser - Extract text from PDF documents
"""
import os
from typing import List, Optional, Dict
from pathlib import Path
import PyPDF2


class PDFParser:
    """Parse PDF documents and extract text content."""

    def __init__(self):
        self.supported_extensions = ['.pdf']

    def parse_file(self, file_path: str) -> Dict:
        """
        Parse a PDF file and return structured content.

        Args:
            file_path: Path to the PDF file

        Returns:
            Dict with page_count, text_content, metadata
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        if not file_path.lower().endswith('.pdf'):
            raise ValueError("File must be a PDF")

        result = {
            "file_path": file_path,
            "file_name": os.path.basename(file_path),
            "page_count": 0,
            "pages": [],
            "full_text": "",
            "metadata": {}
        }

        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)

                result["page_count"] = len(reader.pages)
                result["metadata"] = {
                    "title": reader.metadata.get('/Title', ''),
                    "author": reader.metadata.get('/Author', ''),
                    "subject": reader.metadata.get('/Subject', ''),
                }

                for i, page in enumerate(reader.pages):
                    text = page.extract_text()
                    result["pages"].append({
                        "page_num": i + 1,
                        "text": text
                    })
                    result["full_text"] += text + "\n\n"

        except Exception as e:
            raise Exception(f"Failed to parse PDF: {str(e)}")

        return result

    def parse_directory(self, directory_path: str) -> List[Dict]:
        """
        Parse all PDF files in a directory.

        Args:
            directory_path: Path to directory containing PDFs

        Returns:
            List of parsed document results
        """
        docs = []
        path = Path(directory_path)

        for file_path in path.glob("*.pdf"):
            try:
                doc = self.parse_file(str(file_path))
                docs.append(doc)
            except Exception as e:
                print(f"Failed to parse {file_path}: {e}")
                continue

        return docs

    def extract_sections(self, text: str) -> List[Dict]:
        """
        Extract potential sections from text based on common patterns.
        Looks for headers, chapter markers, etc.

        Args:
            text: Full text content

        Returns:
            List of section dictionaries
        """
        sections = []
        lines = text.split('\n')

        current_section = None
        current_content = []

        for line in lines:
            # Detect section headers (various patterns)
            is_header = False

            # Pattern 1: Numbered chapters (1., 2., 3.1, etc.)
            if any(line.strip().startswith(f"{i}.") for i in range(1, 50)):
                is_header = True
            # Pattern 2: ALL CAPS lines (short)
            elif line.isupper() and 5 < len(line.strip()) < 100:
                is_header = True
            # Pattern 3: Lines ending with colon
            elif line.strip().endswith(':'):
                is_header = True

            if is_header and current_section:
                # Save previous section
                sections.append({
                    "title": current_section,
                    "content": '\n'.join(current_content).strip()
                })
                current_content = []

            if is_header:
                current_section = line.strip()
            else:
                current_content.append(line)

        # Don't forget the last section
        if current_section:
            sections.append({
                "title": current_section,
                "content": '\n'.join(current_content).strip()
            })

        return sections