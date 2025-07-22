"""
Embedding generation service for ERPFTS Phase1 MVP

Generates vector embeddings using sentence transformers model
and manages ChromaDB vector storage.
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from uuid import uuid4

import chromadb
import numpy as np
from loguru import logger
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.exceptions import EmbeddingError
from ..core.cache import get_cache_manager
from ..core.performance import measure_performance, get_performance_monitor
from ..db.session import get_db_session
from ..models.database import KnowledgeChunk


class EmbeddingService:
    """Service for generating and managing embeddings."""
    
    def __init__(self, db: Optional[Session] = None):
        """Initialize embedding service with performance components."""
        self.db = db or next(get_db_session())
        self.model = None
        self.chroma_client = None
        self.collection = None
        self.cache_manager = get_cache_manager()
        self.performance_monitor = get_performance_monitor()
        self._initialize_model()
        self._initialize_chroma()
    
    def _initialize_model(self):
        """Initialize the sentence transformer model."""
        try:
            logger.info(f"Loading embedding model: {settings.embedding_model}")
            self.model = SentenceTransformer(settings.embedding_model)
            logger.info("Embedding model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load embedding model: {str(e)}")
            raise EmbeddingError(f"Model initialization failed: {str(e)}")
    
    def _initialize_chroma(self):
        """Initialize ChromaDB client and collection."""
        try:
            # Create persistent client
            self.chroma_client = chromadb.PersistentClient(
                path=settings.chroma_persist_directory
            )
            
            # Get or create collection
            self.collection = self.chroma_client.get_or_create_collection(
                name=settings.chroma_collection_name,
                metadata={"description": "ERPFTS Knowledge Chunks"}
            )
            
            logger.info("ChromaDB initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {str(e)}")
            raise EmbeddingError(f"ChromaDB initialization failed: {str(e)}")
    
    async def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for a list of texts with caching and performance monitoring.
        
        Args:
            texts: List of text strings
            
        Returns:
            Array of embeddings
            
        Raises:
            EmbeddingError: If embedding generation fails
        """
        async with measure_performance("embedding_service.generate_embeddings", {"text_count": len(texts)}):
            try:
                if not texts:
                    return np.array([])
                
                logger.info(f"Generating embeddings for {len(texts)} texts")
                
                # Check cache for embeddings
                cached_embeddings = {}
                uncached_texts = []
                uncached_indices = []
                
                for i, text in enumerate(texts):
                    cached_embedding = await self.cache_manager.get_embedding(text)
                    if cached_embedding is not None:
                        cached_embeddings[i] = cached_embedding
                    else:
                        uncached_texts.append(text)
                        uncached_indices.append(i)
                
                # Generate embeddings for uncached texts in batches
                batch_size = settings.embedding_batch_size
                all_embeddings = [None] * len(texts)
                
                # Fill in cached embeddings
                for i, embedding in cached_embeddings.items():
                    all_embeddings[i] = np.array(embedding)
                
                # Generate new embeddings for uncached texts
                if uncached_texts:
                    new_embeddings = []
                    
                    for i in range(0, len(uncached_texts), batch_size):
                        batch_texts = uncached_texts[i:i + batch_size]
                        
                        # Run in executor to avoid blocking
                        loop = asyncio.get_event_loop()
                        batch_embeddings = await loop.run_in_executor(
                            None, self.model.encode, batch_texts
                        )
                        
                        new_embeddings.append(batch_embeddings)
                    
                    # Combine all new embeddings
                    if new_embeddings:
                        combined_embeddings = np.vstack(new_embeddings)
                        
                        # Fill in new embeddings and cache them
                        for i, embedding in enumerate(combined_embeddings):
                            original_index = uncached_indices[i]
                            all_embeddings[original_index] = embedding
                            
                            # Cache the embedding
                            await self.cache_manager.set_embedding(
                                uncached_texts[i], 
                                embedding.tolist(),
                                ttl=settings.cache_embedding_ttl
                            )
                
                # Combine all embeddings into final result
                embeddings = np.vstack(all_embeddings)
            
            logger.info(f"Generated {len(embeddings)} embeddings with dimension {embeddings.shape[1]}")
            return embeddings
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            raise EmbeddingError(f"Embedding generation failed: {str(e)}")
    
    async def process_chunks(self, document_id: str) -> int:
        """
        Process all chunks for a document and store embeddings.
        
        Args:
            document_id: Document ID
            
        Returns:
            Number of chunks processed
            
        Raises:
            EmbeddingError: If processing fails
        """
        try:
            # Get all chunks for the document
            chunks = self.db.query(KnowledgeChunk).filter(
                KnowledgeChunk.document_id == document_id
            ).all()
            
            if not chunks:
                logger.warning(f"No chunks found for document: {document_id}")
                return 0
            
            # Extract text content
            texts = [chunk.content for chunk in chunks]
            
            # Generate embeddings
            embeddings = await self.generate_embeddings(texts)
            
            # Prepare data for ChromaDB
            chunk_ids = [chunk.id for chunk in chunks]
            metadatas = []
            
            for chunk in chunks:
                metadata = {
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "language": chunk.language or "unknown",
                    "token_count": chunk.token_count,
                    "content_hash": chunk.content_hash
                }
                metadatas.append(metadata)
            
            # Store in ChromaDB
            await self._store_embeddings(
                ids=chunk_ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas
            )
            
            # Update chunks with embedding status
            for chunk in chunks:
                chunk.embedding_status = "completed"
            
            self.db.commit()
            
            logger.info(f"Processed {len(chunks)} chunks for document {document_id}")
            return len(chunks)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Chunk processing failed for document {document_id}: {str(e)}")
            raise EmbeddingError(f"Chunk processing failed: {str(e)}")
    
    async def _store_embeddings(
        self,
        ids: List[str],
        embeddings: np.ndarray,
        documents: List[str],
        metadatas: List[Dict[str, Any]]
    ):
        """
        Store embeddings in ChromaDB.
        
        Args:
            ids: List of chunk IDs
            embeddings: Array of embeddings
            documents: List of document texts
            metadatas: List of metadata dictionaries
        """
        try:
            # Convert embeddings to list format for ChromaDB
            embeddings_list = embeddings.tolist()
            
            # Store in ChromaDB
            self.collection.add(
                ids=ids,
                embeddings=embeddings_list,
                documents=documents,
                metadatas=metadatas
            )
            
            logger.info(f"Stored {len(ids)} embeddings in ChromaDB")
            
        except Exception as e:
            logger.error(f"Failed to store embeddings: {str(e)}")
            raise EmbeddingError(f"Embedding storage failed: {str(e)}")
    
    async def search_similar(
        self,
        query: str,
        top_k: int = 10,
        threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks using semantic similarity with performance monitoring.
        
        Args:
            query: Search query text
            top_k: Number of top results to return
            threshold: Minimum similarity threshold
            filters: Optional metadata filters
            
        Returns:
            List of similar chunks with metadata
            
        Raises:
            EmbeddingError: If search fails
        """
        async with measure_performance("embedding_service.search_similar", {"query": query[:50], "top_k": top_k}):
            try:
                # Generate embedding for query
                query_embeddings = await self.generate_embeddings([query])
                query_embedding = query_embeddings[0].tolist()
                
                # Search in ChromaDB
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k,
                    where=filters
                )
                
                # Process results
                similar_chunks = []
                
                if results['ids'] and results['ids'][0]:
                    for i, chunk_id in enumerate(results['ids'][0]):
                        distance = results['distances'][0][i]
                        similarity = 1 - distance  # Convert distance to similarity
                        
                        if similarity >= threshold:
                            chunk_data = {
                                "id": chunk_id,
                                "content": results['documents'][0][i],
                                "metadata": results['metadatas'][0][i],
                                "similarity": similarity,
                                "distance": distance
                            }
                            similar_chunks.append(chunk_data)
                
                logger.info(f"Found {len(similar_chunks)} similar chunks for query")
                return similar_chunks
            
        except Exception as e:
            logger.error(f"Similarity search failed: {str(e)}")
            raise EmbeddingError(f"Similarity search failed: {str(e)}")
    
    async def delete_document_embeddings(self, document_id: str) -> bool:
        """
        Delete all embeddings for a document.
        
        Args:
            document_id: Document ID
            
        Returns:
            True if successful
        """
        try:
            # Get chunk IDs for the document
            chunks = self.db.query(KnowledgeChunk).filter(
                KnowledgeChunk.document_id == document_id
            ).all()
            
            chunk_ids = [chunk.id for chunk in chunks]
            
            if chunk_ids:
                # Delete from ChromaDB
                self.collection.delete(ids=chunk_ids)
                logger.info(f"Deleted embeddings for document {document_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete embeddings for document {document_id}: {str(e)}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the embedding collection.
        
        Returns:
            Collection statistics
        """
        try:
            count = self.collection.count()
            
            stats = {
                "total_embeddings": count,
                "collection_name": settings.chroma_collection_name,
                "embedding_model": settings.embedding_model,
                "embedding_dimension": settings.embedding_dimension
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get collection stats: {str(e)}")
            return {
                "total_embeddings": 0,
                "error": str(e)
            }
    
    async def reindex_all_chunks(self) -> int:
        """
        Re-generate embeddings for all chunks in the database.
        
        Returns:
            Number of chunks reindexed
        """
        try:
            # Get all chunks
            chunks = self.db.query(KnowledgeChunk).all()
            
            if not chunks:
                logger.info("No chunks to reindex")
                return 0
            
            # Clear existing embeddings
            try:
                self.collection.delete()
            except:
                pass  # Collection might not exist
            
            # Recreate collection
            self.collection = self.chroma_client.get_or_create_collection(
                name=settings.chroma_collection_name,
                metadata={"description": "ERPFTS Knowledge Chunks"}
            )
            
            # Process in batches by document
            document_ids = list(set(chunk.document_id for chunk in chunks))
            total_processed = 0
            
            for doc_id in document_ids:
                try:
                    processed = await self.process_chunks(doc_id)
                    total_processed += processed
                except Exception as e:
                    logger.error(f"Failed to reindex document {doc_id}: {str(e)}")
                    continue
            
            logger.info(f"Reindexed {total_processed} chunks")
            return total_processed
            
        except Exception as e:
            logger.error(f"Reindexing failed: {str(e)}")
            raise EmbeddingError(f"Reindexing failed: {str(e)}")