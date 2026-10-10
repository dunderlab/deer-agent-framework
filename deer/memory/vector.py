from typing import Any, Optional, Union
from pathlib import Path
import hashlib
import logging
import json
import os

import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger(f"DEER.{__name__}")


class VectorMemory:

    def __init__(self, path: Path) -> None:
        """
        Initialize the VectorMemory system using ChromaDB.

        Parameters
        ----------
        path : Path
            The path where the persistent database will be stored.
        """
        self.path = path.resolve()
        self.client = chromadb.PersistentClient(path=path)
        self.emb_fn = embedding_functions.DefaultEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name="agent_memory", embedding_function=self.emb_fn
        )

    def add_document(
        self,
        doc_id: str,
        doc: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Add a document to the vector collection.

        Parameters
        ----------
        doc_id : str
            Unique identifier for the document.
        doc : str
            The content of the document to be embedded and stored.
        metadata : dict, optional
            Additional metadata associated with the document.
            If 'hit_count' is not provided, it will be initialized to 0.
        """
        if not doc:
            return

        # 1. Calculate the MD5 hash of the received document
        doc_hash = hashlib.md5(doc.encode("utf-8")).hexdigest()

        # 2. Query existing metadata for this ID
        existing = self.collection.get(ids=[doc_id], include=["metadatas"])
        existing_hash = None
        current_hit_count = 0

        if existing["ids"] and existing["metadatas"] and existing["metadatas"][0]:
            meta_existing = existing["metadatas"][0]
            existing_hash = meta_existing.get("content_hash")
            current_hit_count = meta_existing.get("hit_count", 0)

        # 3. If the document already exists and the hash matches, do nothing
        if existing_hash == doc_hash:
            return

        # 4. Prepare metadata preserving the hit_count and adding the hash
        meta = metadata.copy() if metadata else {}
        if "hit_count" not in meta:
            meta["hit_count"] = current_hit_count

        meta["content_hash"] = doc_hash

        # 5. Save only if it is new or has changed
        self.collection.upsert(documents=[doc], metadatas=[meta], ids=[doc_id])

    def read_document(
        self,
        doc_id: str,
        path: Path,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Read a document from the filesystem and add it to the collection.

        Parameters
        ----------
        doc_id : str
            The unique identifier to assign to the document.
        path : Path
            The filesystem path to the document file.
        metadata : dict of {str : Any}, optional
            Additional metadata to associate with the document. If None,
            an empty dictionary is used. Defaults to None.

        Notes
        -----
        The method ensures that the metadata contains a 'hit_count' key,
        initializing it to 0 if it is missing. The file is read using
        UTF-8 encoding.
        """
        if not path.exists():
            logging.warning("File does not exist: %s", path)
            return

        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError) as e:
            logging.warning("Could not read %s: %s", path.name, e)
            return

        # 1. Calculate the MD5 hash of the current content
        file_hash = hashlib.md5(content.encode("utf-8")).hexdigest()

        # 2. Query only the existing metadata for this ID
        existing = self.collection.get(ids=[doc_id], include=["metadatas"])
        existing_hash = None
        current_hit_count = 0

        if existing["ids"] and existing["metadatas"] and existing["metadatas"][0]:
            meta_existing = existing["metadatas"][0]
            existing_hash = meta_existing.get("content_hash")
            current_hit_count = meta_existing.get("hit_count", 0)

        # 3. If the file already exists and the hash matches, skip the write operation
        if existing_hash == file_hash:
            return

        # 4. Prepare metadata preserving the previous hit_count if it existed
        meta = metadata.copy() if metadata is not None else {}
        if "hit_count" not in meta:
            meta["hit_count"] = current_hit_count

        meta["content_hash"] = file_hash
        if "path" not in meta:
            meta["path"] = path.name

        # 5. Save only if it is new or has changed
        self.collection.upsert(documents=[content], metadatas=[meta], ids=[doc_id])

    def read_directory(
        self,
        doc_id_prefix: str,
        path: Path,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Recursively read all files in a directory and add them to the collection.

        Parameters
        ----------

        doc_id_prefix : str
        The prefix to use for generating unique document IDs.
        path : Path
        The root directory path to scan for files.
        metadata : dict of {str : Any}, optional
        Base metadata to associate with each document. If None,
        an empty dictionary is used. Defaults to None.

        Notes
        -----
        The method ensures that the metadata contains a 'hit_count' key,
        initializing it to 0 if missing. For each file found, the filename
        is added to the metadata under the 'path' key. Files that cannot
        be read due to encoding or permission issues are skipped and logged.
        """
        base_meta = metadata.copy() if metadata is not None else {}
        if "hit_count" not in base_meta:
            base_meta["hit_count"] = 0

        files_to_process = []
        doc_ids = []

        # 1. Read files and calculate their MD5 hash locally
        for file_path in path.rglob("*"):
            if not file_path.is_file():
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
                file_hash = hashlib.md5(content.encode("utf-8")).hexdigest()

                doc_id = f"{doc_id_prefix}-{file_path.name}"
                files_to_process.append((doc_id, file_path.name, content, file_hash))
                doc_ids.append(doc_id)
            except (UnicodeDecodeError, PermissionError) as e:
                logging.warning("Could not read %s: %s", file_path.name, e)

        if not doc_ids:
            return

        # 2. Retrieve only existing metadata from ChromaDB (much lighter)
        existing = self.collection.get(ids=doc_ids, include=["metadatas"])
        existing_hashes = {
            id_: meta.get("content_hash")
            for id_, meta in zip(existing["ids"], existing["metadatas"])
            if meta is not None
        }

        # 3. Filter and upsert only new files or those with different hashes
        for doc_id, file_name, content, file_hash in files_to_process:
            if existing_hashes.get(doc_id) == file_hash:
                # The file has not changed, skip writing to avoid inflating disk usage
                continue

            current_meta = base_meta.copy()
            current_meta["path"] = file_name
            current_meta["content_hash"] = file_hash  # Store the hash in the metadata

            self.collection.upsert(
                documents=[content],
                metadatas=[current_meta],
                ids=[doc_id],
            )

    def query(self, query_text: str, n_results: int = 3) -> list[dict[str, Any]]:
        """
        Search for the most similar fragments and automatically
        increment the query counter for the results.

        Parameters
        ----------
        query_text : str
            The text query to search for in the vector space.
        n_results : int, optional
            The number of top results to return. Defaults to 3.

        Returns
        -------
        list of dict
            A list of results where each element is a dictionary containing:
            'id', 'text', and 'metadata'.
        """
        # 1. Vector search
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
        )

        if not results["ids"] or not results["ids"][0]:
            return []

        ids = results["ids"][0]
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]

        # 2. Bulk update of hit_counts
        self._update_hit_counts(ids)

        # 3. Return structured results
        final_results = []
        for i, id_ in enumerate(ids):
            final_results.append(
                {"id": id_, "text": documents[i], "metadata": metadatas[i]}
            )
        return final_results

    def _update_hit_counts(self, ids: list[str]) -> None:
        """
        Internal method to increment the counters of a list of IDs
        as efficiently as possible.

        Parameters
        ----------
        ids : list of str
            The list of document IDs whose hit counts should be incremented.
        """
        if not ids:
            return

        # Get current metadata for all involved IDs in a single step
        current_data = self.collection.get(ids=ids)
        current_metadatas = current_data["metadatas"]

        updated_metadatas = []
        for meta in current_metadatas:
            # Increment current value
            count = meta.get("hit_count", 0) + 1
            meta["hit_count"] = count
            updated_metadatas.append(meta)

        # Update all documents in a single write operation
        self.collection.update(ids=ids, metadatas=updated_metadatas)

    def audit_full_memory(self, top_n: Optional[int] = None) -> list[dict[str, Any]]:
        """
        Extracts everything, calculates estimated disk weight,
        and sorts by popularity.

        Parameters
        ----------
        top_n : int, optional
            The maximum number of results to return.
            If None, all documents are returned. Defaults to None.

        Returns
        -------
        list of dict
            A list of audit records sorted by popularity (hit_count) descending.
            Each record includes 'id', 'hit_count', 'size_bytes', 'size_human',
            and 'text_preview'.
        """
        # 1. Total extraction (Including embeddings for weight calculation)
        all_data = self.collection.get(include=["documents", "metadatas", "embeddings"])

        ids = all_data["ids"]
        docs = all_data["documents"]
        metas = all_data["metadatas"]
        embs = all_data["embeddings"]

        # Vector weight calculation (float32 = 4 bytes)
        vector_size_bytes = 0
        if embs is not None and len(embs) > 0:
            vector_size_bytes = len(embs[0]) * 4

        audit_list = []

        for i, id_ in enumerate(ids):
            # A. Estimated space calculation
            text_bytes = len(docs[i].encode("utf-8")) if docs[i] else 0
            meta_bytes = len(json.dumps(metas[i]).encode("utf-8")) if metas[i] else 0
            current_vector_bytes = (
                vector_size_bytes if embs is not None and i < len(embs) else 0
            )
            total_bytes = text_bytes + meta_bytes + current_vector_bytes

            # B. Popularity extraction
            hit_count = metas[i].get("hit_count", 0) if metas[i] else 0

            audit_list.append(
                {
                    "id": id_,
                    "hit_count": hit_count,
                    "size_bytes": total_bytes,
                    "size_human": self.format_bytes(total_bytes),
                    "text_preview": docs[i][:50] + "..." if docs[i] else "",
                }
            )

        # 2. Descending sort by hit_count (Most popular first)
        audit_list.sort(key=lambda x: x["hit_count"], reverse=True)

        return audit_list[:top_n] if top_n else audit_list

    def format_bytes(self, size):
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size} bytes"

    def get_db_info(self) -> dict[str, int]:
        """
        Retrieve general information about the database,
        including total document count and estimated disk size.

        Returns
        -------
        dict
            A dictionary containing 'total_documents' (int)
            and 'disk_size_bytes' (int).
        """
        total_size = 0
        for dirpath, _, filenames in os.walk(self.path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
        return {
            "total_documents": self.collection.count(),
            "disk_size_bytes": total_size,
        }

    def _parse_size_to_bytes(self, size_str: Union[str, int]) -> float:
        """
        Convert human-readable size strings to bytes.

        Parameters
        ----------
        size_str : str or int
            The size representation (e.g., '10 MB', '1 GB', or integer bytes).

        Returns
        -------
        float
            The equivalent size in bytes.
        """
        if isinstance(size_str, int):
            return float(size_str)
        units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
        size_str = size_str.upper().strip()

        sorted_units = sorted(units.items(), key=lambda x: len(x[0]), reverse=True)
        for unit, value in sorted_units:
            if size_str.endswith(unit):
                return float(size_str.replace(unit, "").strip()) * value
        return float(size_str)

    def clear_unused_documents(self) -> int:
        """
        Delete all documents that have hit_count == 0.

        Returns
        -------
        int
            The number of documents deleted.
        """
        # 1. Get all IDs and their metadata
        all_data = self.collection.get()
        ids = all_data["ids"]
        metas = all_data["metadatas"]

        if not ids:
            logger.info("The database is already empty.")
            return 0

        # 2. Filter IDs that have hit_count = 0
        ids_to_delete = []
        for i, id_ in enumerate(ids):
            count = metas[i].get("hit_count", 0) if metas[i] else 0
            if count == 0:
                ids_to_delete.append(id_)

        # 3. Execute bulk deletion
        if ids_to_delete:
            self.collection.delete(ids=ids_to_delete)
            logger.info(
                "Cleanup completed. Deleted %i documents with no queries.",
                len(ids_to_delete),
            )
        else:
            logger.info("No documents with zero queries were found.")

        return len(ids_to_delete)

    def shrink_to_size(self, target_size_str: Union[str, int]) -> int:
        """
        Delete the least used documents until the target disk size is reached.

        Parameters
        ----------
        target_size_str : str or int
            The target maximum size of the database (e.g., '50 MB' or bytes as int).

        Returns
        -------
        int
            The number of documents deleted to reach the target size.
        """
        target_bytes = self._parse_size_to_bytes(target_size_str)

        # FIX: Use estimated document sizes instead of actual folder size
        # to avoid the "Infrastructure Overhead" problem.
        audit_list = self.audit_full_memory()
        current_estimated_total = sum(doc["size_bytes"] for doc in audit_list)

        if current_estimated_total <= target_bytes:
            logger.info(
                "Database data size is already below target (%i <= %i).",
                current_estimated_total,
                target_bytes,
            )
            return 0

        bytes_to_free = current_estimated_total - target_bytes
        logger.info("Estimated data to free: %s", self.format_bytes(bytes_to_free))

        least_popular_first = audit_list[::-1]
        ids_to_delete = []
        bytes_freed_so_far = 0

        for doc in least_popular_first:
            if bytes_freed_so_far >= bytes_to_free:
                break
            ids_to_delete.append(doc["id"])
            bytes_freed_so_far += doc["size_bytes"]

        if ids_to_delete:
            self.collection.delete(ids=ids_to_delete)
            logger.info(
                "Aggressive cleanup completed. Deleted %i documents.",
                len(ids_to_delete),
            )

        return len(ids_to_delete)

    def load_from_json(self, json_path: Path) -> None:
        """
        Load documents from a JSON file and add them to the collection.

        Parameters
        ----------
        json_path : Path
            The filesystem path to the JSON file containing a list of
            document data.

        Raises
        ------
        FileNotFoundError
            If the file at `json_path` does not exist.
        json.JSONDecodeError
            If the file content is not valid JSON.

        Notes
        -----
        The JSON file is expected to contain a list of dictionaries, where
        each dictionary represents a document and its associated metadata
        to be passed as keyword arguments to the `add_document` method.
        """
        if not json_path.exists():
            raise FileNotFoundError(
                f"The file does not exist at the following path: {json_path}"
            )

        with json_path.open("r", encoding="utf-8") as f:
            memories: list[dict[str, Any]] = json.load(f)

        for memory in memories:
            if isinstance(memory, dict):
                self.add_document(**memory)
            else:
                continue
