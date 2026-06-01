"""
文档解析模块 - 从PDF提取文本用于embedding
"""
import re
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class TextChunk:
    """文本块"""
    id: str
    text: str
    source: str  # 来源文件
    page: Optional[int] = None
    chapter: str = ""
    section: str = ""
    category: str = "general"  # framework, script, case, objection
    spin_stage: Optional[str] = None  # situation, problem, implication, need_payoff
    metadata: dict = None


class DocumentProcessor:
    """
    文档处理器 - 从PDF/Markdown提取文本并分块

    支持MinerU转换的Markdown格式
    """

    def __init__(self, chunk_size: int = 800, overlap: int = 100):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def process_markdown(self, md_path: str, book_name: str) -> List[TextChunk]:
        """
        处理Markdown文件，提取文本块

        Args:
            md_path: Markdown文件路径
            book_name: 书籍名称

        Returns:
            文本块列表
        """
        chunks = []

        try:
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            print(f"File not found: {md_path}")
            return chunks

        # 清洗内容：移除图片链接、元数据、目录等
        cleaned = self._clean_content(content)

        # 按章节分割
        sections = self._split_into_sections(cleaned)

        for i, section in enumerate(sections):
            if not section.get('text', '').strip():
                continue

            # 对每个章节进行分块
            text = section['text'].strip()

            # 如果文本太长，先按段落分割
            if len(text) > 10000:
                # 按换行分割成段落
                paragraphs = re.split(r'\n\s*\n', text)
                text_parts = []
                current_part = []
                current_len = 0
                for para in paragraphs:
                    if current_len + len(para) > 5000:
                        text_parts.append('\n\n'.join(current_part))
                        current_part = []
                        current_len = 0
                    current_part.append(para)
                    current_len += len(para)
                if current_part:
                    text_parts.append('\n\n'.join(current_part))
            else:
                text_parts = [text]

            for j, text_chunk in enumerate(text_parts):
                sub_chunks = self.chunk_text(text_chunk, self.chunk_size, self.overlap)
                for k, sub_chunk in enumerate(sub_chunks):
                    if len(sub_chunk) < 50:  # 跳过太短的块
                        continue

                    chunk = TextChunk(
                        id=f"{book_name}_{i}_{j}_{k}",
                        text=sub_chunk,
                        source=book_name,
                        chapter=section.get('chapter', ''),
                        section=section.get('section', ''),
                        category=self._categorize_content(section),
                        spin_stage=self._detect_spin_stage(section),
                        metadata={
                            'book': book_name,
                            'full_path': md_path,
                            'chunk_index': k
                        }
                    )
                    chunks.append(chunk)

        return chunks

    def _clean_content(self, content: str) -> str:
        """清洗内容：移除图片、元数据、目录等"""
        lines = content.split('\n')
        cleaned_lines = []
        in_metadata = False
        in_toc = False
        prev_line_empty = True

        for line in lines:
            # 跳过图片行
            if line.strip().startswith('![') or line.strip().startswith('![](http'):
                continue

            # 跳过元数据区域（书名、作者等）
            if line.strip().startswith('书名:') or line.strip().startswith('作者:') \
               or line.strip().startswith('责任编辑') or line.strip().startswith('标准书号'):
                continue

            # 跳过版权信息
            if 'Copyright' in line or '版权' in line:
                continue

            # 跳过目录标记
            if re.match(r'^#+\s*[CONTENTS|目录]', line, re.IGNORECASE):
                in_toc = True
                continue
            if in_toc and (line.strip().startswith('#') or re.match(r'^\d+\.', line.strip())):
                continue
            if line.strip() == '':
                in_toc = False

            # 检测章节标题（用于分割）
            if line.strip().startswith('#'):
                cleaned_lines.append('')
                cleaned_lines.append(line)
                cleaned_lines.append('')
                prev_line_empty = True
                continue

            # 移除行内图片
            line = re.sub(r'!\[.*?\]\(.*?\)', '', line)

            # 跳过空白元行
            if not line.strip():
                if prev_line_empty:
                    continue
                prev_line_empty = True
                cleaned_lines.append('')
                continue

            prev_line_empty = False
            cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def _split_into_sections(self, content: str) -> List[dict]:
        """将文档分割成章节"""
        sections = []
        parts = re.split(r'^#+\s+', content, flags=re.MULTILINE)

        current_chapter = ''
        current_text_parts = []

        for part in parts:
            if not part.strip():
                continue

            lines = part.split('\n')
            title = lines[0].strip() if lines else ""
            text = '\n'.join(lines[1:]).strip()

            # 如果有标题，认为是新章节
            if title:
                # 保存之前的章节
                if current_text_parts or current_chapter:
                    sections.append({
                        'chapter': current_chapter,
                        'text': '\n'.join(current_text_parts).strip(),
                        'type': self._classify_chapter(current_chapter)
                    })

                current_chapter = title
                current_text_parts = []
                if text:
                    current_text_parts.append(text)
            elif text:
                current_text_parts.append(text)

        # 保存最后一个章节
        if current_text_parts or current_chapter:
            sections.append({
                'chapter': current_chapter,
                'text': '\n'.join(current_text_parts).strip(),
                'type': self._classify_chapter(current_chapter)
            })

        return sections

    def _classify_chapter(self, title: str) -> str:
        """根据标题分类章节"""
        title_lower = title.lower()

        if any(kw in title_lower for kw in ['背景问题', '现状', '情况', 'situation']):
            return 'situation'
        elif any(kw in title_lower for kw in ['难点问题', '困难', '问题', 'problem']):
            return 'problem'
        elif any(kw in title_lower for kw in ['暗示问题', '影响', '后果', 'implication']):
            return 'implication'
        elif any(kw in title_lower for kw in ['需求效益', '需求-效益', 'need-payoff', 'payoff']):
            return 'need_payoff'
        elif any(kw in title_lower for kw in ['开场', 'opening']):
            return 'opening'
        elif any(kw in title_lower for kw in ['缔结', 'closing', '成交']):
            return 'closing'
        elif any(kw in title_lower for kw in ['异议', '反对', 'objection']):
            return 'objection'
        else:
            return 'general'

    def _categorize_content(self, section: dict) -> str:
        """根据内容分类"""
        text = section.get('text', '').lower()
        chapter = section.get('chapter', '').lower()

        if 'spin' in chapter or 'spin' in text:
            return 'framework'
        elif any(kw in chapter for kw in ['话术', '脚本', 'script']):
            return 'script'
        elif any(kw in chapter for kw in ['案例', 'example', 'case']):
            return 'case'
        elif any(kw in chapter for kw in ['异议', '反对', 'objection']):
            return 'objection'
        else:
            return 'framework'

    def _detect_spin_stage(self, section: dict) -> Optional[str]:
        """检测SPIN阶段"""
        chapter = section.get('chapter', '').lower()

        if 'situation' in chapter or '背景' in chapter:
            return 'situation'
        elif 'problem' in chapter or '难点' in chapter:
            return 'problem'
        elif 'implication' in chapter or '暗示' in chapter:
            return 'implication'
        elif 'need-payoff' in chapter or '需求效益' in chapter:
            return 'need_payoff'

        return None

    def chunk_text(self, text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
        """
        将长文本分割成块

        Args:
            text: 输入文本
            chunk_size: 每块最大字符数
            overlap: 相邻块重叠字符数

        Returns:
            文本块列表
        """
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0
        max_iterations = 1000  # 安全限制
        iteration = 0

        while start < len(text) and iteration < max_iterations:
            iteration += 1
            end = start + chunk_size

            # 在句号或逗号处切割
            if end < len(text):
                for sep in ['\n\n', '\n', '。', '，', '.', ',']:
                    last_sep = text.rfind(sep, start, end)
                    if last_sep > start:
                        end = last_sep + len(sep)
                        break

            chunks.append(text[start:end].strip())
            start = end - overlap

        return chunks