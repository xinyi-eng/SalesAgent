"""
Knowledge Base Processor - Parse markdown books into knowledge chunks
"""
import re
import json
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict


@dataclass
class KnowledgeChunk:
    """A chunk of knowledge extracted from a book."""
    id: str
    text: str
    category: str  # framework | objection | script | case
    source_book: str
    chapter: str
    section: str
    spin_stage: Optional[str] = None  # situation | problem | implication | need_payoff
    metadata: dict = None

    def to_dict(self) -> Dict:
        return asdict(self)


class MarkdownKnowledgeProcessor:
    """Process markdown books into knowledge chunks."""

    # SPIN stage mapping
    SPIN_STAGES = {
        "4.1": "situation",
        "4.2": "problem",
        "4.3": "implication",
        "4.4": "need_payoff",
        "背景问题": "situation",
        "难点问题": "problem",
        "暗示问题": "implication",
        "需求": "need_payoff",
    }

    def __init__(self):
        self.chunks: List[KnowledgeChunk] = []
        self.chunk_counter = 0

    def process_spin_book(self, markdown_path: str) -> List[KnowledgeChunk]:
        """Process SPIN Selling book."""
        with open(markdown_path, 'r', encoding='utf-8') as f:
            content = f.read()

        chunks = []
        current_chapter = ""
        current_section = ""
        current_content = []

        lines = content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Detect chapter heading (## X.X or ## X.X 标题)
            chapter_match = re.match(r'^## (\d+\.\d+)\s+(.+)$', stripped)
            if chapter_match:
                # Save previous section content
                if current_content and current_section:
                    text = '\n'.join(current_content).strip()
                    if len(text) > 100:
                        chunk = self._create_spin_chunk(
                            text, current_chapter, current_section,
                            markdown_path, chunks
                        )
                        if chunk:
                            chunks.append(chunk)

                current_section = chapter_match.group(1)  # e.g. "4.1"
                current_chapter = "SPIN战略"
                current_content = []
                i += 1
                continue

            # Detect main section (## 标题)
            if stripped.startswith('## ') and not stripped.startswith('### '):
                # Save previous
                if current_content and current_section:
                    text = '\n'.join(current_content).strip()
                    if len(text) > 100:
                        chunk = self._create_spin_chunk(
                            text, current_chapter, current_section,
                            markdown_path, chunks
                        )
                        if chunk:
                            chunks.append(chunk)

                current_section = stripped[3:]
                current_content = []
                i += 1
                continue

            # Detect subsection ### 标题 - skip, merge into parent
            if stripped.startswith('### '):
                i += 1
                continue

            # Regular content
            if current_section:
                current_content.append(line)

            i += 1

        # Don't forget last chunk
        if current_content and current_section:
            text = '\n'.join(current_content).strip()
            if len(text) > 100:
                chunk = self._create_spin_chunk(
                    text, current_chapter, current_section,
                    markdown_path, chunks
                )
                if chunk:
                    chunks.append(chunk)

        return chunks

    def _create_spin_chunk(
        self,
        text: str,
        chapter: str,
        section: str,
        source_path: str,
        existing_chunks: List
    ) -> Optional[KnowledgeChunk]:
        """Create a SPIN knowledge chunk."""
        # Determine SPIN stage
        spin_stage = None
        for key, stage in self.SPIN_STAGES.items():
            if key in section:
                spin_stage = stage
                break

        # Generate ID
        chunk_num = len(existing_chunks) + 1
        chunk_id = f"spin_{spin_stage or 'general'}_{chunk_num:04d}"

        # Clean text - remove image references
        text = re.sub(r'!\[image\]\([^)]+\)', '', text)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        text = text.strip()

        if len(text) < 100:
            return None

        return KnowledgeChunk(
            id=chunk_id,
            text=text[:3000],  # Limit length
            category="framework",
            source_book="SPIN销售巨人",
            chapter=chapter,
            section=section,
            spin_stage=spin_stage,
            metadata={
                "book": "SPIN销售巨人",
                "chapter_num": section.split()[0] if section else "",
            }
        )

    def process_solution_selling_book(self, markdown_path: str) -> List[KnowledgeChunk]:
        """Process Solution Selling book."""
        with open(markdown_path, 'r', encoding='utf-8') as f:
            content = f.read()

        chunks = []
        current_chapter = ""
        current_section = ""
        current_content = []

        lines = content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Detect chapter heading (## 第X章)
            chapter_match = re.match(r'^## 第(\d+)章\s+(.+)$', stripped)
            if chapter_match:
                # Save previous
                if current_content and current_section:
                    text = '\n'.join(current_content).strip()
                    if len(text) > 100:
                        chunk = self._create_chunk(
                            text, current_chapter, current_section,
                            "新解决方案销售", chunks
                        )
                        if chunk:
                            chunks.append(chunk)

                current_chapter = f"第{chapter_match.group(1)}章"
                current_section = chapter_match.group(2)
                current_content = []
                i += 1
                continue

            # Detect main section ## 标题
            if stripped.startswith('## ') and not stripped.startswith('### '):
                if current_content and current_section:
                    text = '\n'.join(current_content).strip()
                    if len(text) > 100:
                        chunk = self._create_chunk(
                            text, current_chapter, current_section,
                            "新解决方案销售", chunks
                        )
                        if chunk:
                            chunks.append(chunk)

                current_section = stripped[3:]
                current_content = []
                i += 1
                continue

            # Detect subsection ### - skip
            if stripped.startswith('### '):
                i += 1
                continue

            if current_section:
                current_content.append(line)

            i += 1

        # Last chunk
        if current_content and current_section:
            text = '\n'.join(current_content).strip()
            if len(text) > 100:
                chunk = self._create_chunk(
                    text, current_chapter, current_section,
                    "新解决方案销售", chunks
                )
                if chunk:
                    chunks.append(chunk)

        return chunks

    def _create_chunk(
        self,
        text: str,
        chapter: str,
        section: str,
        source_book: str,
        existing_chunks: List
    ) -> Optional[KnowledgeChunk]:
        """Create a generic knowledge chunk."""
        chunk_num = len(existing_chunks) + 1
        chunk_id = f"ss_ch{chunk_num:04d}"

        # Clean text
        text = re.sub(r'!\[image\]\([^)]+\)', '', text)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        text = text.strip()

        if len(text) < 100:
            return None

        return KnowledgeChunk(
            id=chunk_id,
            text=text[:3000],
            category="framework",
            source_book=source_book,
            chapter=chapter,
            section=section,
            spin_stage=None,
            metadata={
                "book": source_book,
            }
        )

    def process_strategic_marketing_book(self, markdown_path: str) -> List[KnowledgeChunk]:
        """Process Strategic Marketing book."""
        # Similar structure, can be customized based on actual content
        return self.process_solution_selling_book(markdown_path)

    def export_to_json(self, chunks: List[KnowledgeChunk], output_path: str):
        """Export chunks to JSON file."""
        data = [c.to_dict() for c in chunks]
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Exported {len(chunks)} chunks to {output_path}")


def main():
    """Process all books."""
    base_dir = Path("C:/Users/zsndz/Desktop/SalesAgent/原始数据")

    processor = MarkdownKnowledgeProcessor()

    # Find all markdown files
    md_files = list(base_dir.glob("MinerU_markdown_*.md"))

    # Deduplicate by book name (there are multiple versions)
    seen_books = set()
    unique_files = []
    for f in md_files:
        # Extract book name from filename
        match = re.search(r'MinerU_markdown_(.+?)_\d+\.md', f.name)
        if match:
            book_name = match.group(1)
            if book_name not in seen_books:
                seen_books.add(book_name)
                unique_files.append(f)

    print(f"Found {len(unique_files)} unique books:")
    for f in unique_files:
        print(f"  - {f.name}")

    all_chunks = []

    for md_file in unique_files:
        print(f"\nProcessing: {md_file.name}")

        if "SPIN" in md_file.name:
            chunks = processor.process_spin_book(str(md_file))
            print(f"  SPIN chunks: {len(chunks)}")
        elif "解决方案销售" in md_file.name:
            chunks = processor.process_solution_selling_book(str(md_file))
            print(f"  Solution Selling chunks: {len(chunks)}")
        elif "战略营销" in md_file.name:
            chunks = processor.process_strategic_marketing_book(str(md_file))
            print(f"  Strategic Marketing chunks: {len(chunks)}")
        else:
            print(f"  Unknown book type, skipping")
            continue

        all_chunks.extend(chunks)

    print(f"\n=== Total chunks: {len(all_chunks)} ===")

    # Export to JSON
    output_dir = Path("C:/Users/zsndz/Desktop/SalesAgent/_bmad-output/knowledge-base")
    output_dir.mkdir(parents=True, exist_ok=True)

    processor.export_to_json(all_chunks, str(output_dir / "knowledge_chunks.json"))

    # Also export by category
    spin_chunks = [c for c in all_chunks if c.spin_stage]
    ss_chunks = [c for c in all_chunks if "新解决方案销售" in c.source_book]
    sm_chunks = [c for c in all_chunks if "战略营销" in c.source_book]

    print(f"\nBy category:")
    print(f"  SPIN chunks: {len(spin_chunks)}")
    print(f"  Solution Selling chunks: {len(ss_chunks)}")
    print(f"  Strategic Marketing chunks: {len(sm_chunks)}")

    # Export SPIN chunks separately for easy access
    if spin_chunks:
        processor.export_to_json(spin_chunks, str(output_dir / "spin_chunks.json"))

    # Print sample
    print(f"\n=== Sample SPIN chunks ===")
    for chunk in spin_chunks[:3]:
        print(f"\n[{chunk.id}] {chunk.section}")
        print(f"  spin_stage: {chunk.spin_stage}")
        print(f"  text: {chunk.text[:200]}...")


if __name__ == "__main__":
    main()