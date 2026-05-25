"""文档处理服务 - 文件上传、文本提取、知识库更新"""
import asyncio
import logging
import os
import re
import hashlib
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import time

from loguru import logger

from app.services.rag_service import rag_service

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """文档处理器 - 从各种文件格式提取文本"""

    @staticmethod
    def process_txt(content: str) -> List[Dict[str, Any]]:
        """处理纯文本文件"""
        # 按行分割，每N行作为一个片段
        lines = content.split("\n")
        chunks = []
        current_chunk = []
        chunk_size = 50  # 每50行一个chunk

        for i, line in enumerate(lines):
            current_chunk.append(line)
            if len(current_chunk) >= chunk_size:
                chunk_text = "\n".join(current_chunk)
                chunks.append({
                    "content": chunk_text,
                    "metadata": {
                        "source": "txt",
                        "lines": f"{i - chunk_size + 1}-{i}"
                    }
                })
                current_chunk = []

        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            chunks.append({
                "content": chunk_text,
                "metadata": {
                    "source": "txt",
                    "lines": f"{len(lines) - len(current_chunk)}-{len(lines)}"
                }
            })

        return chunks

    @staticmethod
    def process_markdown(content: str) -> List[Dict[str, Any]]:
        """处理 Markdown 文件"""
        # 按标题分割成不同部分
        sections = []
        current_section = []
        current_title = "未命名章节"

        lines = content.split("\n")
        for line in lines:
            # 检测标题
            if re.match(r"^#{1,6}\s+", line):
                if current_section:
                    sections.append({
                        "title": current_title,
                        "content": "\n".join(current_section)
                    })
                current_title = line.lstrip("#").strip()
                current_section = []
            else:
                current_section.append(line)

        if current_section:
            sections.append({
                "title": current_title,
                "content": "\n".join(current_section)
            })

        # 转换为 chunks
        chunks = []
        for section in sections:
            if section["content"].strip():
                chunks.append({
                    "content": f"# {section['title']}\n\n{section['content']}",
                    "metadata": {
                        "source": "markdown",
                        "title": section["title"]
                    }
                })

        return chunks

    @staticmethod
    def process_csv(content: str) -> List[Dict[str, Any]]:
        """处理 CSV 文件"""
        lines = content.split("\n")
        if not lines:
            return []

        headers = lines[0].split(",") if lines else []
        chunks = []

        # 按行处理，每10行一个chunk
        chunk_size = 10
        for i in range(1, len(lines), chunk_size):
            chunk_lines = lines[i:i + chunk_size]
            chunk_text = "\n".join(chunk_lines)
            if chunk_text.strip():
                chunks.append({
                    "content": chunk_text,
                    "metadata": {
                        "source": "csv",
                        "row_start": i,
                        "row_end": min(i + chunk_size, len(lines))
                    }
                })

        return chunks

    @staticmethod
    def process_json(content: str) -> List[Dict[str, Any]]:
        """处理 JSON 文件"""
        import json

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return [{
                "content": content[:10000],  # 截断处理
                "metadata": {"source": "json", "error": "parse_failed"}
            }]

        chunks = []

        def extract_items(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    extract_items(value, f"{path}.{key}")
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    extract_items(item, f"{path}[{i}]")

        # 简化处理：直接把整个JSON转字符串
        if isinstance(data, (dict, list)):
            chunks.append({
                "content": json.dumps(data, ensure_ascii=False, indent=2)[:10000],
                "metadata": {"source": "json", "type": "object"}
            })

        return chunks

    def process_content(
        self,
        content: str,
        file_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """根据文件类型处理内容"""
        file_type = file_type.lower().lstrip(".")

        processors = {
            "txt": self.process_txt,
            "md": self.process_markdown,
            "markdown": self.process_markdown,
            "csv": self.process_csv,
            "json": self.process_json,
        }

        processor = processors.get(file_type, self.process_txt)
        chunks = processor(content)

        # 添加额外元数据
        extra_meta = metadata or {}
        for chunk in chunks:
            chunk["metadata"].update(extra_meta)

        return chunks


class FileWatcher:
    """文件监控器 - 监控目录变化自动更新知识库"""

    def __init__(self):
        self._watchers: Dict[str, Dict[str, Any]] = {}  # collection_name -> watcher config
        self._file_hashes: Dict[str, str] = {}  # 文件路径 -> 文件hash
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def add_watch_path(
        self,
        path: str,
        collection_name: str,
        file_types: Optional[List[str]] = None,
        recursive: bool = True
    ) -> None:
        """添加监控路径

        Args:
            path: 要监控的目录路径
            collection_name: 对应的知识库名称
            file_types: 要处理的文件类型列表，如 [".txt", ".md", ".pdf"]
            recursive: 是否递归监控子目录
        """
        self._watchers[collection_name] = {
            "path": path,
            "file_types": file_types or [".txt", ".md", ".markdown", ".csv", ".json"],
            "recursive": recursive,
            "last_check": time.time()
        }
        logger.info(f"添加文件监控: {path} -> 知识库 [{collection_name}]")

    def remove_watch_path(self, collection_name: str) -> None:
        """移除监控路径"""
        if collection_name in self._watchers:
            del self._watchers[collection_name]
            logger.info(f"移除文件监控: {collection_name}")

    def _get_file_hash(self, file_path: str) -> str:
        """计算文件hash"""
        hasher = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _scan_directory(
        self,
        directory: str,
        file_types: List[str],
        recursive: bool
    ) -> List[Tuple[str, str]]:
        """扫描目录获取文件列表"""
        files = []
        path = Path(directory)

        if not path.exists():
            return files

        if recursive:
            for ext in file_types:
                files.extend(path.rglob(f"*{ext}"))
        else:
            for ext in file_types:
                files.extend(path.glob(f"*{ext}"))

        return [(str(f), ext) for f in files for ext in file_types if str(f).endswith(ext)]

    async def check_updates(self) -> Dict[str, List[str]]:
        """检查文件更新，返回有变化的知识库及其文件"""
        changes = {}

        for collection_name, config in self._watchers.items():
            changed_files = []

            files = self._scan_directory(
                config["path"],
                config["file_types"],
                config["recursive"]
            )

            for file_path, _ in files:
                try:
                    current_hash = self._get_file_hash(file_path)

                    if file_path not in self._file_hashes or self._file_hashes[file_path] != current_hash:
                        changed_files.append(file_path)
                        self._file_hashes[file_path] = current_hash

                except Exception as e:
                    logger.error(f"检查文件失败 {file_path}: {e}")

            if changed_files:
                changes[collection_name] = changed_files

        return changes

    async def start_watching(self, interval: int = 60) -> None:
        """启动文件监控循环

        Args:
            interval: 检查间隔（秒）
        """
        self._running = True
        logger.info("文件监控服务启动")

        while self._running:
            try:
                changes = await self.check_updates()

                for collection_name, files in changes.items():
                    logger.info(f"检测到 {len(files)} 个文件更新，知识库: [{collection_name}]")

                    for file_path in files:
                        await self._process_file(file_path, collection_name)

            except Exception as e:
                logger.error(f"文件监控循环异常: {e}")

            await asyncio.sleep(interval)

    def stop_watching(self) -> None:
        """停止文件监控"""
        self._running = False
        logger.info("文件监控服务停止")

    async def _process_file(self, file_path: str, collection_name: str) -> None:
        """处理单个文件"""
        try:
            processor = DocumentProcessor()
            path = Path(file_path)
            file_type = path.suffix

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            chunks = processor.process_content(content, file_type, {
                "source": path.name,
                "path": str(path.parent)
            })

            if chunks:
                await rag_service.add_documents(
                    documents=chunks,
                    collection_name=collection_name
                )
                logger.info(f"处理文件 {path.name}，添加 {len(chunks)} 个文档片段")

        except Exception as e:
            logger.error(f"处理文件失败 {file_path}: {e}")


class KnowledgeBaseManager:
    """知识库管理器 - 统一管理多知识库和文档上传"""

    _instance: Optional["KnowledgeBaseManager"] = None

    def __init__(self):
        self._processor = DocumentProcessor()
        self._file_watcher = FileWatcher()
        self._initialized = False

    @classmethod
    def get_instance(cls) -> "KnowledgeBaseManager":
        """获取单例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        """初始化知识库管理器"""
        self._initialized = True
        logger.info("知识库管理器初始化完成")

    async def upload_document(
        self,
        content: str,
        filename: str,
        collection_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """上传文档到知识库

        Args:
            content: 文档内容
            filename: 文件名
            collection_name: 知识库名称
            metadata: 额外元数据

        Returns:
            上传结果，包含添加的文档数量
        """
        if not self._initialized:
            raise RuntimeError("知识库管理器未初始化")

        # 从文件名获取文件类型
        file_type = filename.split(".")[-1] if "." in filename else "txt"

        chunks = self._processor.process_content(content, file_type, {
            "source": filename,
            **(metadata or {})
        })

        if not chunks:
            return {"success": False, "error": "未能提取有效内容"}

        doc_ids = await rag_service.add_documents(
            documents=chunks,
            collection_name=collection_name
        )

        return {
            "success": True,
            "count": len(doc_ids),
            "doc_ids": doc_ids,
            "filename": filename,
            "collection": collection_name or "default"
        }

    async def upload_file(
        self,
        file_path: str,
        collection_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """上传本地文件到知识库

        Args:
            file_path: 文件路径
            collection_name: 知识库名称
            metadata: 额外元数据

        Returns:
            上传结果
        """
        path = Path(file_path)

        if not path.exists():
            return {"success": False, "error": f"文件不存在: {file_path}"}

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        return await self.upload_document(
            content=content,
            filename=path.name,
            collection_name=collection_name,
            metadata=metadata
        )

    def add_watch_path(
        self,
        path: str,
        collection_name: str,
        file_types: Optional[List[str]] = None,
        recursive: bool = True
    ) -> None:
        """添加自动监控路径"""
        self._file_watcher.add_watch_path(
            path=path,
            collection_name=collection_name,
            file_types=file_types,
            recursive=recursive
        )

    async def start_file_watcher(self, interval: int = 60) -> None:
        """启动文件监控"""
        if self._file_watcher._running:
            return
        self._file_watcher._task = asyncio.create_task(
            self._file_watcher.start_watching(interval)
        )

    def stop_file_watcher(self) -> None:
        """停止文件监控"""
        self._file_watcher.stop_watching()

    def list_collections(self) -> List[str]:
        """列出所有知识库"""
        return rag_service.list_collections()

    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """获取知识库统计"""
        return {
            "name": collection_name,
            "document_count": rag_service.count(collection_name)
        }

    async def delete_collection(self, collection_name: str) -> bool:
        """删除知识库"""
        if not self._initialized:
            raise RuntimeError("知识库管理器未初始化")

        await rag_service.clear_collection(collection_name)
        return True

    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized


# 全局单例
kb_manager = KnowledgeBaseManager.get_instance()