"""
RAG Caching Service for fast voice chat.

Provides in-memory caching for:
1. Query embeddings (query string → embedding vector)
2. Semantic result cache (similar queries → cached results)
3. Session context cache (pre-warmed knowledge for active sessions)

No Redis required - uses Python's built-in LRU cache and custom structures.
"""

import asyncio
import hashlib
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class CachedResult:
    """Cached RAG query result with metadata."""

    results: list[dict[str, Any]]
    embedding: list[float]
    timestamp: float = field(default_factory=time.time)
    hit_count: int = 0


@dataclass
class SessionContext:
    """Pre-warmed context for an active voice session."""

    dealership_id: int
    chunks: list[dict[str, Any]]
    embeddings: list[list[float]]  # Embeddings for each chunk
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)


class LRUCache:
    """Simple LRU cache with max size and TTL."""

    def __init__(self, maxsize: int = 1000, ttl_seconds: int = 3600):
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        """Get item from cache, returns None if not found or expired."""
        async with self._lock:
            if key not in self._cache:
                return None

            value, timestamp = self._cache[key]

            # Check TTL
            if time.time() - timestamp > self.ttl_seconds:
                del self._cache[key]
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return value

    async def set(self, key: str, value: Any) -> None:
        """Set item in cache, evicting oldest if at capacity."""
        async with self._lock:
            # Remove if exists (to update position)
            if key in self._cache:
                del self._cache[key]

            # Evict oldest if at capacity
            while len(self._cache) >= self.maxsize:
                self._cache.popitem(last=False)

            self._cache[key] = (value, time.time())

    async def clear(self) -> None:
        """Clear all items from cache."""
        async with self._lock:
            self._cache.clear()

    def size(self) -> int:
        """Return current cache size."""
        return len(self._cache)


class SemanticCache:
    """
    Cache that finds similar queries using cosine similarity.

    If a new query is semantically similar to a cached query (above threshold),
    returns the cached results instead of querying Pinecone again.
    """

    def __init__(
        self,
        maxsize: int = 500,
        similarity_threshold: float = 0.92,
        ttl_seconds: int = 1800,  # 30 minutes
    ):
        self.maxsize = maxsize
        self.similarity_threshold = similarity_threshold
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, CachedResult] = {}  # key: dealership_id
        self._embeddings: dict[
            str, list[tuple[str, list[float]]]
        ] = {}  # dealership_id -> [(cache_key, embedding)]
        self._lock = asyncio.Lock()

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        a_np = np.array(a)
        b_np = np.array(b)
        return float(np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np)))

    def _generate_key(self, query: str, dealership_id: int) -> str:
        """Generate cache key from query and dealership."""
        return hashlib.sha256(f"{dealership_id}:{query}".encode()).hexdigest()[:16]

    async def find_similar(
        self,
        query_embedding: list[float],
        dealership_id: int,
    ) -> CachedResult | None:
        """
        Find cached result for a semantically similar query.

        Returns cached result if similarity > threshold, None otherwise.
        """
        async with self._lock:
            dealer_key = str(dealership_id)

            if dealer_key not in self._embeddings:
                return None

            best_match = None
            best_similarity = 0.0
            expired_keys = []

            for cache_key, embedding in self._embeddings[dealer_key]:
                if cache_key not in self._cache:
                    expired_keys.append((cache_key, embedding))
                    continue

                cached = self._cache[cache_key]

                # Check TTL
                if time.time() - cached.timestamp > self.ttl_seconds:
                    expired_keys.append((cache_key, embedding))
                    del self._cache[cache_key]
                    continue

                similarity = self._cosine_similarity(query_embedding, embedding)

                if (
                    similarity > best_similarity
                    and similarity >= self.similarity_threshold
                ):
                    best_similarity = similarity
                    best_match = cached

            # Clean up expired embeddings
            for item in expired_keys:
                self._embeddings[dealer_key].remove(item)

            if best_match:
                best_match.hit_count += 1
                logger.info(
                    f"Semantic cache HIT for dealership {dealership_id}, "
                    f"similarity: {best_similarity:.3f}, hits: {best_match.hit_count}"
                )

            return best_match

    async def store(
        self,
        query: str,
        query_embedding: list[float],
        results: list[dict[str, Any]],
        dealership_id: int,
    ) -> None:
        """Store query results in semantic cache."""
        async with self._lock:
            dealer_key = str(dealership_id)
            cache_key = self._generate_key(query, dealership_id)

            # Initialize dealer embeddings list if needed
            if dealer_key not in self._embeddings:
                self._embeddings[dealer_key] = []

            # Evict oldest if at capacity (per dealership)
            while len(self._embeddings[dealer_key]) >= self.maxsize:
                old_key, _ = self._embeddings[dealer_key].pop(0)
                if old_key in self._cache:
                    del self._cache[old_key]

            # Store result
            self._cache[cache_key] = CachedResult(
                results=results,
                embedding=query_embedding,
            )
            self._embeddings[dealer_key].append((cache_key, query_embedding))

            logger.debug(
                f"Cached query for dealership {dealership_id}, key: {cache_key}"
            )

    async def clear_dealership(self, dealership_id: int) -> None:
        """Clear all cached results for a dealership."""
        async with self._lock:
            dealer_key = str(dealership_id)

            if dealer_key in self._embeddings:
                for cache_key, _ in self._embeddings[dealer_key]:
                    if cache_key in self._cache:
                        del self._cache[cache_key]
                del self._embeddings[dealer_key]

    def stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        total_entries = len(self._cache)
        total_hits = sum(c.hit_count for c in self._cache.values())
        return {
            "total_entries": total_entries,
            "total_hits": total_hits,
            "dealerships": len(self._embeddings),
        }


class RAGCache:
    """
    Main RAG caching service.

    Provides three levels of caching:
    1. Embedding cache: Avoid recomputing embeddings for same queries
    2. Semantic cache: Return results for similar queries
    3. Session cache: Pre-warmed context for active voice sessions
    """

    def __init__(self):
        # Embedding cache: query string -> embedding vector
        self.embedding_cache = LRUCache(maxsize=2000, ttl_seconds=3600)

        # Semantic result cache: similar queries -> results
        self.semantic_cache = SemanticCache(
            maxsize=500,
            similarity_threshold=0.92,
            ttl_seconds=1800,
        )

        # Session context cache: session_id -> pre-warmed chunks
        self._session_contexts: dict[str, SessionContext] = {}
        self._session_lock = asyncio.Lock()

        # Stats
        self._embedding_hits = 0
        self._embedding_misses = 0
        self._semantic_hits = 0
        self._semantic_misses = 0

    async def get_cached_embedding(self, query: str) -> list[float] | None:
        """Get cached embedding for a query string."""
        embedding = await self.embedding_cache.get(query)
        if embedding:
            self._embedding_hits += 1
        else:
            self._embedding_misses += 1
        return embedding

    async def cache_embedding(self, query: str, embedding: list[float]) -> None:
        """Cache an embedding for a query string."""
        await self.embedding_cache.set(query, embedding)

    async def get_cached_results(
        self,
        query_embedding: list[float],
        dealership_id: int,
    ) -> list[dict[str, Any]] | None:
        """Get cached results for a semantically similar query."""
        result = await self.semantic_cache.find_similar(query_embedding, dealership_id)
        if result:
            self._semantic_hits += 1
            return result.results
        self._semantic_misses += 1
        return None

    async def cache_results(
        self,
        query: str,
        query_embedding: list[float],
        results: list[dict[str, Any]],
        dealership_id: int,
    ) -> None:
        """Cache query results."""
        await self.semantic_cache.store(query, query_embedding, results, dealership_id)

    async def get_session_context(self, session_id: str) -> SessionContext | None:
        """Get pre-warmed context for a session."""
        async with self._session_lock:
            ctx = self._session_contexts.get(session_id)
            if ctx:
                ctx.last_accessed = time.time()
            return ctx

    async def set_session_context(
        self,
        session_id: str,
        dealership_id: int,
        chunks: list[dict[str, Any]],
        embeddings: list[list[float]],
    ) -> None:
        """Store pre-warmed context for a session."""
        async with self._session_lock:
            # Clean up old sessions (older than 1 hour)
            now = time.time()
            expired = [
                sid
                for sid, ctx in self._session_contexts.items()
                if now - ctx.last_accessed > 3600
            ]
            for sid in expired:
                del self._session_contexts[sid]

            self._session_contexts[session_id] = SessionContext(
                dealership_id=dealership_id,
                chunks=chunks,
                embeddings=embeddings,
            )
            logger.info(f"Pre-warmed session {session_id} with {len(chunks)} chunks")

    async def clear_session_context(self, session_id: str) -> None:
        """Clear session context when call ends."""
        async with self._session_lock:
            if session_id in self._session_contexts:
                del self._session_contexts[session_id]

    async def search_session_context(
        self,
        session_id: str,
        query_embedding: list[float],
        top_k: int = 5,
        threshold: float = 0.7,
    ) -> list[dict[str, Any]]:
        """
        Search pre-warmed session context for relevant chunks.

        Returns top_k chunks above similarity threshold.
        """
        ctx = await self.get_session_context(session_id)
        if not ctx or not ctx.chunks:
            return []

        # Compute similarities
        query_np = np.array(query_embedding)
        similarities = []

        for i, emb in enumerate(ctx.embeddings):
            emb_np = np.array(emb)
            sim = float(
                np.dot(query_np, emb_np)
                / (np.linalg.norm(query_np) * np.linalg.norm(emb_np))
            )
            if sim >= threshold:
                similarities.append((sim, ctx.chunks[i]))

        # Sort by similarity and return top_k
        similarities.sort(key=lambda x: x[0], reverse=True)
        return [chunk for _, chunk in similarities[:top_k]]

    def stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        embedding_total = self._embedding_hits + self._embedding_misses
        semantic_total = self._semantic_hits + self._semantic_misses

        return {
            "embedding_cache": {
                "size": self.embedding_cache.size(),
                "hits": self._embedding_hits,
                "misses": self._embedding_misses,
                "hit_rate": self._embedding_hits / embedding_total
                if embedding_total > 0
                else 0,
            },
            "semantic_cache": {
                **self.semantic_cache.stats(),
                "hits": self._semantic_hits,
                "misses": self._semantic_misses,
                "hit_rate": self._semantic_hits / semantic_total
                if semantic_total > 0
                else 0,
            },
            "session_contexts": len(self._session_contexts),
        }


# Singleton instance
_rag_cache: RAGCache | None = None


def get_rag_cache() -> RAGCache:
    """Get or create RAG cache instance."""
    global _rag_cache
    if _rag_cache is None:
        _rag_cache = RAGCache()
    return _rag_cache
