import os
from pathlib import Path

import chardet


class FileParser:
    SUPPORTED = {".pdf", ".docx", ".txt"}

    def parse(self, file_path: str) -> str:
        ext = Path(file_path).suffix.lower()
        if ext == ".pdf":
            return self._parse_pdf(file_path)
        elif ext == ".docx":
            return self._parse_docx(file_path)
        elif ext == ".txt":
            return self._parse_txt(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {ext}，支持: {self.SUPPORTED}")

    def _parse_pdf(self, path: str) -> str:
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(path)
            texts = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    texts.append(text)
            return "\n".join(texts)
        except Exception as e:
            raise ValueError(f"PDF解析失败: {e}")

    def _parse_docx(self, path: str) -> str:
        try:
            from docx import Document
            doc = Document(path)
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception as e:
            raise ValueError(f"DOCX解析失败: {e}")

    def _parse_txt(self, path: str) -> str:
        with open(path, "rb") as f:
            raw = f.read()
        detected = chardet.detect(raw)
        encoding = detected.get("encoding", "utf-8") or "utf-8"
        return raw.decode(encoding, errors="replace")


file_parser = FileParser()
