"""RAG Service using Pinecone and LangChain with intelligent caching."""

import hashlib
import logging
import time
import uuid
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone, ServerlessSpec
from pinecone.exceptions import NotFoundException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_maker
from app.models.document import Document, DocumentChunk
from app.services.rag_cache import get_rag_cache

logger = logging.getLogger(__name__)


class RAGService:
    """Service for RAG operations using Pinecone and LangChain."""

    def __init__(self):
        """Initialize embeddings, text splitter, and Pinecone client."""
        self.embeddings = OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.RAG_CHUNK_SIZE,
            chunk_overlap=settings.RAG_CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        # Initialize Pinecone client
        self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        self.index_name = settings.PINECONE_INDEX_NAME
        self._index = None

    def _get_index(self):
        """Get or create Pinecone index."""
        if self._index is None:
            # Check if index exists, create if not
            existing_indexes = [idx.name for idx in self.pc.list_indexes()]

            if self.index_name not in existing_indexes:
                self.pc.create_index(
                    name=self.index_name,
                    dimension=settings.EMBEDDING_DIMENSIONS,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud=settings.PINECONE_CLOUD,
                        region=settings.PINECONE_REGION,
                    ),
                )

            self._index = self.pc.Index(self.index_name)

        return self._index

    def _generate_content_hash(self, text: str) -> str:
        """Generate a SHA-256 hash for document content."""
        return hashlib.sha256(text.encode()).hexdigest()

    def _get_namespace(self, dealership_id: int) -> str:
        """Get Pinecone namespace for a dealership."""
        return f"dealership_{dealership_id}"

    async def initialize_namespace(
        self,
        dealership_id: int,
        dealership_name: str,
    ) -> dict[str, Any]:
        """
        Initialize RAG for a dealership.

        Args:
            dealership_id: Dealership ID
            dealership_name: Dealership name

        Returns:
            RAG configuration dict
        """
        # Ensure Pinecone index exists
        self._get_index()

        # Create configuration
        rag_config = {
            "embedding_model": settings.EMBEDDING_MODEL,
            "embedding_dimensions": settings.EMBEDDING_DIMENSIONS,
            "chunk_size": settings.RAG_CHUNK_SIZE,
            "chunk_overlap": settings.RAG_CHUNK_OVERLAP,
            "vector_db": "pinecone",
            "index_name": self.index_name,
            "namespace": self._get_namespace(dealership_id),
            "topics": [
                "books",
                "objection_handling",
                "playbooks",
                "videos",
                "compliance",
                "product_knowledge",
            ],
            "metadata": {
                "dealership_id": dealership_id,
                "dealership_name": dealership_name,
            },
            "status": "initialized",
            "document_counts": {
                "books": 0,
                "objection_handling": 0,
                "playbooks": 0,
                "videos": 0,
                "compliance": 0,
                "product_knowledge": 0,
            },
        }

        return rag_config

    async def upload_documents(
        self,
        texts: list[str],
        dealership_id: int,
        topic: str,
        filenames: list[str] | None = None,
        db: AsyncSession | None = None,
    ) -> int:
        """
        Upload documents to Pinecone.

        Args:
            texts: List of document texts
            dealership_id: Dealership ID
            topic: Topic category
            filenames: Optional list of filenames
            db: Optional database session

        Returns:
            Number of chunks uploaded
        """
        should_close = db is None
        if db is None:
            db = async_session_maker()
            await db.__aenter__()

        try:
            total_chunks = 0
            index = self._get_index()
            namespace = self._get_namespace(dealership_id)

            for i, text_content in enumerate(texts):
                filename = (
                    filenames[i]
                    if filenames and i < len(filenames)
                    else f"document_{i}"
                )
                content_hash = self._generate_content_hash(text_content)

                # Check if document already exists in PostgreSQL
                existing = await db.execute(
                    select(Document).where(
                        Document.dealership_id == dealership_id,
                        Document.filename == filename,
                        Document.content_hash == content_hash,
                    )
                )
                if existing.scalar_one_or_none():
                    continue  # Skip duplicate

                # Split text into chunks
                chunks = self.text_splitter.split_text(text_content)

                if not chunks:
                    continue

                # Create document record in PostgreSQL (for metadata tracking)
                document = Document(
                    dealership_id=dealership_id,
                    filename=filename,
                    topic=topic,
                    content_hash=content_hash,
                    chunk_count=len(chunks),
                )
                db.add(document)
                await db.flush()  # Get document ID

                # Generate embeddings for all chunks
                embeddings = await self.embeddings.aembed_documents(chunks)

                # Prepare vectors for Pinecone upsert
                vectors_to_upsert = []
                for j, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                    # Generate unique ID for the vector
                    vector_id = f"doc_{document.id}_chunk_{j}_{uuid.uuid4().hex[:8]}"

                    # Create chunk record in PostgreSQL (without embedding)
                    document_chunk = DocumentChunk(
                        document_id=document.id,
                        dealership_id=dealership_id,
                        chunk_index=j,
                        content=chunk,
                        topic=topic,
                        pinecone_id=vector_id,  # Store Pinecone vector ID
                    )
                    db.add(document_chunk)

                    # Prepare vector for Pinecone
                    vectors_to_upsert.append(
                        {
                            "id": vector_id,
                            "values": embedding,
                            "metadata": {
                                "document_id": document.id,
                                "dealership_id": dealership_id,
                                "chunk_index": j,
                                "topic": topic,
                                "filename": filename,
                                "content": chunk[
                                    :1000
                                ],  # Store truncated content in metadata
                            },
                        }
                    )

                # Upsert vectors to Pinecone in batches
                batch_size = 100
                for batch_start in range(0, len(vectors_to_upsert), batch_size):
                    batch = vectors_to_upsert[batch_start : batch_start + batch_size]
                    index.upsert(vectors=batch, namespace=namespace)

                total_chunks += len(chunks)

            await db.commit()
            return total_chunks

        except Exception:
            await db.rollback()
            raise
        finally:
            if should_close:
                await db.__aexit__(None, None, None)

    async def query(
        self,
        query: str,
        dealership_id: int,
        topics: list[str] | None = None,
        top_k: int | None = None,
        db: AsyncSession | None = None,
        use_cache: bool = True,
        session_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Query the RAG knowledge base using Pinecone vector similarity search.

        OPTIMIZED with multi-level caching:
        1. Check session context (pre-warmed chunks) if session_id provided
        2. Check embedding cache (avoid recomputing same embeddings)
        3. Check semantic cache (similar queries return cached results)
        4. Fall back to Pinecone query

        Args:
            query: Search query
            dealership_id: Dealership ID
            topics: Optional list of topics to filter by
            top_k: Number of results to return
            db: Optional database session
            use_cache: Whether to use caching (default True)
            session_id: Optional session ID for session context lookup

        Returns:
            List of relevant documents with scores
        """
        start_time = time.time()
        top_k = top_k or settings.RAG_TOP_K
        cache = get_rag_cache()

        logger.info(
            f"RAG Query - dealership_id: {dealership_id}, query: {query[:50]}..."
        )

        # Step 1: Try to get cached embedding
        query_embedding = None
        if use_cache:
            query_embedding = await cache.get_cached_embedding(query)
            if query_embedding:
                logger.info("RAG Query - embedding cache HIT")

        # Step 2: Generate embedding if not cached
        if query_embedding is None:
            query_embedding = await self.embeddings.aembed_query(query)
            if use_cache:
                await cache.cache_embedding(query, query_embedding)
            logger.info(
                f"RAG Query - embedding generated, length: {len(query_embedding)}"
            )

        # Step 3: Check session context first (fastest)
        if use_cache and session_id:
            session_results = await cache.search_session_context(
                session_id=session_id,
                query_embedding=query_embedding,
                top_k=top_k,
                threshold=0.7,
            )
            if session_results:
                elapsed = (time.time() - start_time) * 1000
                logger.info(
                    f"RAG Query - session context HIT, {len(session_results)} results in {elapsed:.1f}ms"
                )
                return session_results

        # Step 4: Check semantic cache for similar queries
        if (
            use_cache and topics is None
        ):  # Only use semantic cache when not filtering by topics
            cached_results = await cache.get_cached_results(
                query_embedding, dealership_id
            )
            if cached_results:
                elapsed = (time.time() - start_time) * 1000
                logger.info(
                    f"RAG Query - semantic cache HIT, {len(cached_results)} results in {elapsed:.1f}ms"
                )
                return cached_results

        # Step 5: Query Pinecone (cache miss)
        index = self._get_index()
        namespace = self._get_namespace(dealership_id)

        # Build filter for Pinecone query
        filter_dict = {"dealership_id": dealership_id}
        if topics:
            filter_dict["topic"] = {"$in": topics}

        # Query Pinecone
        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            namespace=namespace,
            filter=filter_dict,
            include_metadata=True,
        )

        logger.info(
            f"RAG Query - Pinecone returned {len(results.matches) if results.matches else 0} results"
        )

        # Format results
        documents = []
        for match in results.matches:
            metadata = match.metadata or {}
            documents.append(
                {
                    "content": metadata.get("content", ""),
                    "topic": metadata.get("topic", ""),
                    "filename": metadata.get("filename", ""),
                    "score": float(match.score),
                }
            )

        # Step 6: Cache results for future queries
        if use_cache and documents and topics is None:
            await cache.cache_results(query, query_embedding, documents, dealership_id)

        elapsed = (time.time() - start_time) * 1000
        logger.info(f"RAG Query - completed in {elapsed:.1f}ms (Pinecone query)")

        return documents

    async def delete_namespace(
        self,
        dealership_id: int,
        db: AsyncSession | None = None,
    ) -> bool:
        """
        Delete all documents and chunks for a dealership.

        Args:
            dealership_id: Dealership ID

        Returns:
            True if successful
        """
        should_close = db is None
        if db is None:
            db = async_session_maker()
            await db.__aenter__()

        try:
            index = self._get_index()
            namespace = self._get_namespace(dealership_id)

            # Delete all vectors in the namespace from Pinecone
            # Handle case where namespace doesn't exist yet
            try:
                index.delete(delete_all=True, namespace=namespace)
            except NotFoundException:
                # Namespace doesn't exist, nothing to delete in Pinecone
                pass

            # Delete all chunks from PostgreSQL
            await db.execute(
                delete(DocumentChunk).where(
                    DocumentChunk.dealership_id == dealership_id
                )
            )

            # Delete all documents from PostgreSQL
            await db.execute(
                delete(Document).where(Document.dealership_id == dealership_id)
            )

            await db.commit()
            return True

        except Exception:
            await db.rollback()
            raise
        finally:
            if should_close:
                await db.__aexit__(None, None, None)

    async def delete_document(
        self,
        document_id: int,
        dealership_id: int,
        db: AsyncSession | None = None,
    ) -> bool:
        """
        Delete a specific document and its chunks.

        Args:
            document_id: Document ID
            dealership_id: Dealership ID (for security check)

        Returns:
            True if successful
        """
        should_close = db is None
        if db is None:
            db = async_session_maker()
            await db.__aenter__()

        try:
            index = self._get_index()
            namespace = self._get_namespace(dealership_id)

            # Get all chunk Pinecone IDs for this document
            chunks_result = await db.execute(
                select(DocumentChunk.pinecone_id).where(
                    DocumentChunk.document_id == document_id,
                    DocumentChunk.dealership_id == dealership_id,
                )
            )
            pinecone_ids = [row[0] for row in chunks_result.all() if row[0]]

            # Delete vectors from Pinecone
            if pinecone_ids:
                try:
                    index.delete(ids=pinecone_ids, namespace=namespace)
                except NotFoundException:
                    # Namespace or vectors don't exist, nothing to delete
                    pass

            # Delete document from PostgreSQL (cascade will delete chunks)
            result = await db.execute(
                delete(Document).where(
                    Document.id == document_id,
                    Document.dealership_id == dealership_id,
                )
            )

            await db.commit()
            return result.rowcount > 0

        except Exception:
            await db.rollback()
            raise
        finally:
            if should_close:
                await db.__aexit__(None, None, None)

    async def get_stats(
        self,
        dealership_id: int,
        db: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """
        Get statistics for a dealership's documents.

        Args:
            dealership_id: Dealership ID

        Returns:
            Statistics dict
        """
        should_close = db is None
        if db is None:
            db = async_session_maker()
            await db.__aenter__()

        try:
            # Get total chunk count from PostgreSQL
            chunk_count_result = await db.execute(
                select(func.count(DocumentChunk.id)).where(
                    DocumentChunk.dealership_id == dealership_id
                )
            )
            total_chunks = chunk_count_result.scalar() or 0

            # Get document count
            doc_count_result = await db.execute(
                select(func.count(Document.id)).where(
                    Document.dealership_id == dealership_id
                )
            )
            total_documents = doc_count_result.scalar() or 0

            # Get counts by topic
            topic_counts_result = await db.execute(
                select(Document.topic, func.count(Document.id))
                .where(Document.dealership_id == dealership_id)
                .group_by(Document.topic)
            )
            topic_counts = {row[0]: row[1] for row in topic_counts_result.all()}

            # Get Pinecone index stats
            index = self._get_index()
            namespace = self._get_namespace(dealership_id)

            try:
                index_stats = index.describe_index_stats()
                # Access namespaces dict - it may be an object or dict depending on SDK version
                namespaces = (
                    index_stats.namespaces if hasattr(index_stats, "namespaces") else {}
                )
                if hasattr(namespaces, "get"):
                    ns_stats = namespaces.get(namespace, {})
                else:
                    ns_stats = getattr(namespaces, namespace, {}) if namespaces else {}

                # Get vector count from namespace stats
                if hasattr(ns_stats, "vector_count"):
                    pinecone_vector_count = ns_stats.vector_count
                elif isinstance(ns_stats, dict):
                    pinecone_vector_count = ns_stats.get("vector_count", 0)
                else:
                    pinecone_vector_count = 0
            except Exception as e:
                pinecone_vector_count = f"unavailable: {str(e)}"

            return {
                "total_chunks": total_chunks,
                "total_documents": total_documents,
                "documents_by_topic": topic_counts,
                "dealership_id": dealership_id,
                "vector_db": "pinecone",
                "pinecone_vector_count": pinecone_vector_count,
            }

        finally:
            if should_close:
                await db.__aexit__(None, None, None)

    async def list_documents(
        self,
        dealership_id: int,
        topic: str | None = None,
        db: AsyncSession | None = None,
    ) -> list[dict[str, Any]]:
        """
        List all documents for a dealership.

        Args:
            dealership_id: Dealership ID
            topic: Optional topic filter

        Returns:
            List of document metadata
        """
        should_close = db is None
        if db is None:
            db = async_session_maker()
            await db.__aenter__()

        try:
            stmt = select(Document).where(Document.dealership_id == dealership_id)

            if topic:
                stmt = stmt.where(Document.topic == topic)

            stmt = stmt.order_by(Document.created_at.desc())

            result = await db.execute(stmt)
            documents = result.scalars().all()

            return [
                {
                    "id": doc.id,
                    "filename": doc.filename,
                    "topic": doc.topic,
                    "chunk_count": doc.chunk_count,
                    "created_at": doc.created_at.isoformat(),
                }
                for doc in documents
            ]

        finally:
            if should_close:
                await db.__aexit__(None, None, None)

    async def prewarm_session(
        self,
        session_id: str,
        dealership_id: int,
        top_k_per_query: int = 3,
    ) -> dict[str, Any]:
        """
        Pre-warm a voice session by fetching common F&I knowledge.

        This is called when a voice call starts to reduce latency on first queries.
        Fetches relevant chunks for common F&I topics and stores them in session cache.

        Args:
            session_id: Session ID for the voice call
            dealership_id: Dealership ID
            top_k_per_query: Number of chunks to fetch per warmup query

        Returns:
            Dict with stats about pre-warmed content
        """
        start_time = time.time()
        cache = get_rag_cache()

        # Common F&I queries to pre-warm the cache
        warmup_queries = [
            "What F&I products and services do we offer?",
            "How do I handle customer objections about price?",
            "What are the benefits of extended warranty coverage?",
            "GAP insurance coverage and benefits",
            "How to present finance options to customers",
            "Common customer concerns and how to address them",
            "Vehicle service contract features",
            "Compliance requirements for F&I",
        ]

        all_chunks = []
        all_embeddings = []
        seen_content = set()  # Deduplicate chunks

        for query in warmup_queries:
            try:
                # Get embedding (will be cached)
                embedding = await cache.get_cached_embedding(query)
                if not embedding:
                    embedding = await self.embeddings.aembed_query(query)
                    await cache.cache_embedding(query, embedding)

                # Query Pinecone
                index = self._get_index()
                namespace = self._get_namespace(dealership_id)

                results = index.query(
                    vector=embedding,
                    top_k=top_k_per_query,
                    namespace=namespace,
                    filter={"dealership_id": dealership_id},
                    include_metadata=True,
                )

                # Collect unique chunks
                for match in results.matches:
                    metadata = match.metadata or {}
                    content = metadata.get("content", "")

                    # Skip duplicates
                    content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
                    if content_hash in seen_content:
                        continue
                    seen_content.add(content_hash)

                    chunk = {
                        "content": content,
                        "topic": metadata.get("topic", ""),
                        "filename": metadata.get("filename", ""),
                        "score": float(match.score),
                    }
                    all_chunks.append(chunk)
                    all_embeddings.append(
                        list(match.values)
                    )  # Store embedding for similarity search

            except Exception as e:
                logger.warning(f"Pre-warm query failed: {query[:30]}... - {e}")
                continue

        # Store in session cache
        if all_chunks:
            await cache.set_session_context(
                session_id=session_id,
                dealership_id=dealership_id,
                chunks=all_chunks,
                embeddings=all_embeddings,
            )

        elapsed = (time.time() - start_time) * 1000

        stats = {
            "session_id": session_id,
            "dealership_id": dealership_id,
            "chunks_prewarmed": len(all_chunks),
            "queries_run": len(warmup_queries),
            "elapsed_ms": round(elapsed, 1),
        }

        logger.info(
            f"Pre-warmed session {session_id}: {len(all_chunks)} chunks in {elapsed:.1f}ms"
        )
        return stats

    async def clear_session(self, session_id: str) -> None:
        """Clear session context when a voice call ends."""
        cache = get_rag_cache()
        await cache.clear_session_context(session_id)
        logger.info(f"Cleared session context for {session_id}")


# Singleton instance
_rag_service: RAGService | None = None


def get_rag_service() -> RAGService:
    """Get or create RAG service instance."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
