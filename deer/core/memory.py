import chromadb
from chromadb.utils import embedding_functions
import json
import os
import logging
from typing import Any, Optional, Union

logger = logging.getLogger(__name__)

class VectorMemory:

    def __init__(self, path: str) -> None:
        """
        Initialize the VectorMemory system using ChromaDB.

        Parameters
        ----------
        path : str, optional
            The path where the persistent database will be stored. 
            Defaults to "./vector_db".
        """
        self.path = path
        self.client = chromadb.PersistentClient(path=path)
        self.emb_fn = embedding_functions.DefaultEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name="agent_memory", 
            embedding_function=self.emb_fn
        )

    def add_document(self, doc_id: str, text: str, metadata: Optional[dict[str, Any]] = None) -> None:
        """
        Add a document to the vector collection.

        Parameters
        ----------
        doc_id : str
            Unique identifier for the document.
        text : str
            The content of the document to be embedded and stored.
        metadata : dict, optional
            Additional metadata associated with the document. 
            If 'hit_count' is not provided, it will be initialized to 0.
        """
        meta = metadata if metadata else {}
        if "hit_count" not in meta:
            meta["hit_count"] = 0

        self.collection.add(documents=[text], metadatas=[meta], ids=[doc_id])

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
        results = self.collection.query(query_texts=[query_text], n_results=n_results)

        ids = results["ids"][0]
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]

        # 2. Bulk update of hit_counts
        self._update_hit_counts(ids)

        # 3. Return structured results
        final_results = []
        for i in range(len(ids)):
            final_results.append(
                {"id": ids[i], "text": documents[i], "metadata": metadatas[i]}
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

        for i in range(len(ids)):
            # A. Estimated space calculation
            text_bytes = len(docs[i].encode("utf-8")) if docs[i] else 0
            meta_bytes = len(json.dumps(metas[i]).encode("utf-8")) if metas[i] else 0
            current_vector_bytes = vector_size_bytes if embs is not None and i < len(embs) else 0
            total_bytes = text_bytes + meta_bytes + current_vector_bytes

            # B. Popularity extraction
            hit_count = metas[i].get("hit_count", 0) if metas[i] else 0

            audit_list.append(
                {
                    "id": ids[i],
                    "hit_count": hit_count,
                    "size_bytes": total_bytes,
                    "size_human": self._format_size(total_bytes),
                    "text_preview": docs[i][:50] + "..." if docs[i] else "",
                }
            )

        # 2. Descending sort by hit_count (Most popular first)
        audit_list.sort(key=lambda x: x["hit_count"], reverse=True)

        return audit_list[:top_n] if top_n else audit_list

    def _format_size(self, bytes: Union[float, int]) -> str:
        """
        Convert a number of bytes into a human-readable string format.

        Parameters
        ----------
        bytes : float or int
            The size in bytes to be formatted.

        Returns
        -------
        str
            The formatted size string (e.g., '1.23 MB').
        """
        for unit in ["B", "KB", "MB", "GB"]:
            if bytes < 1024.0:
                return f"{bytes:.2f} {unit}"
            bytes /= 1024.0

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
                if not os.path.islink(fp): total_size += os.path.getsize(fp)
        return {"total_documents": self.collection.count(), "disk_size_bytes": total_size}

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
        if isinstance(size_str, int): return float(size_str)
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
        ids = all_data['ids']
        metas = all_data['metadatas']

        if not ids:
            logger.info("The database is already empty.")
            return 0

        # 2. Filter IDs that have hit_count = 0
        ids_to_delete = []
        for i in range(len(ids)):
            count = metas[i].get("hit_count", 0) if metas[i] else 0
            if count == 0:
                ids_to_delete.append(ids[i])

        # 3. Execute bulk deletion
        if ids_to_delete:
            self.collection.delete(ids=ids_to_delete)
            logger.info(f"Cleanup completed. Deleted {len(ids_to_delete)} documents with no queries.")
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
                f"Database data size is already below target ({current_estimated_total} <= {target_bytes})."
            )
            return 0

        bytes_to_free = current_estimated_total - target_bytes
        logger.info(f"Estimated data to free: {self._format_size(bytes_to_free)}")

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
                f"Aggressive cleanup completed. Deleted {len(ids_to_delete)} documents."
            )

        return len(ids_to_delete)
