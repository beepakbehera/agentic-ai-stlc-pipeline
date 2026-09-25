"""
Stage 1: RAG Retrieval & Ingestion Node.

Responsible for retrieving relevant context from vector database
and ingesting new documents for the pipeline.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

from src.state import AgenticSTLCState, RAGDocument, create_initial_state
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RAGRetrievalNode:
    """Node for RAG retrieval and document ingestion."""
    
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(
            model_name=settings.embedding_model,
            model_kwargs={"device": "cpu"},
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        self.vector_store = None
        self._init_vector_store()
    
    def _init_vector_store(self):
        """Initialize ChromaDB vector store."""
        try:
            self.vector_store = Chroma(
                persist_directory=settings.vector_db_path,
                embedding_function=self.embeddings,
            )
            logger.info(f"Vector store initialized at {settings.vector_db_path}")
        except Exception as e:
            logger.warning(f"Could not initialize vector store: {e}")
            self.vector_store = None
    
    def ingest_documents(self, documents: List[Dict[str, Any]]) -> int:
        """
        Ingest documents into vector store.
        
        Args:
            documents: List of dicts with 'content' and 'metadata' keys
            
        Returns:
            Number of chunks ingested
        """
        if not self.vector_store:
            self._init_vector_store()
            if not self.vector_store:
                logger.error("Vector store not available for ingestion")
                return 0
        
        langchain_docs = []
        for doc in documents:
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            chunks = self.text_splitter.split_text(content)
            for chunk in chunks:
                langchain_docs.append(Document(page_content=chunk, metadata=metadata))
        
        if langchain_docs:
            self.vector_store.add_documents(langchain_docs)
            self.vector_store.persist()
            logger.info(f"Ingested {len(langchain_docs)} document chunks")
            return len(langchain_docs)
        
        return 0
    
    def retrieve(self, query: str, top_k: int = None) -> List[RAGDocument]:
        """
        Retrieve relevant documents for a query.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of RAGDocument objects
        """
        if not self.vector_store:
            logger.warning("Vector store not available for retrieval")
            return []
        
        top_k = top_k or settings.top_k_retrieval
        results = self.vector_store.similarity_search_with_score(query, k=top_k)
        
        rag_docs = []
        for doc, score in results:
            rag_docs.append(RAGDocument(
                content=doc.page_content,
                metadata=doc.metadata,
                score=float(score),
            ))
        
        logger.info(f"Retrieved {len(rag_docs)} documents for query: {query[:100]}")
        return rag_docs


# Global node instance
rag_node = RAGRetrievalNode()


async def rag_retrieval_node(state: AgenticSTLCState) -> AgenticSTLCState:
    """
    LangGraph node for RAG retrieval stage.
    
    Retrieves relevant context from vector database based on requirements
    and acceptance criteria to inform test case generation.
    """
    logger.info(f"[{state['run_id']}] Starting Stage 1: RAG Retrieval")
    start_time = datetime.utcnow()
    
    try:
        # Build retrieval query from requirements and acceptance criteria
        query = f"{state['requirements']}\n\n{state['acceptance_criteria']}"
        state["rag_query"] = query
        
        # Retrieve relevant documents
        rag_docs = rag_node.retrieve(query)
        state["rag_documents"] = rag_docs
        
        # Categorize retrieved documents
        for doc in rag_docs:
            metadata = doc.metadata
            doc_type = metadata.get("type", "general")
            
            if doc_type == "feature":
                state["similar_features"].append(doc.content[:500])
            elif doc_type == "defect":
                state["past_defects"].append(doc.content[:500])
            elif doc_type == "domain":
                state["domain_knowledge"].append(doc.content[:500])
        
        # Update state
        state["current_stage"] = "rag_retrieval"
        state["updated_at"] = datetime.utcnow()
        state["stages_completed"].append("rag_retrieval")
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"[{state['run_id']}] RAG Retrieval completed in {duration:.2f}s, found {len(rag_docs)} documents")
        
    except Exception as e:
        logger.error(f"[{state['run_id']}] RAG Retrieval failed: {e}")
        state["errors"].append({
            "stage": "rag_retrieval",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        })
        state["stages_failed"].append("rag_retrieval")
        state["status"] = "failed"
    
    return state


async def ingest_documents_node(state: AgenticSTLCState, documents: List[Dict[str, Any]]) -> AgenticSTLCState:
    """
    Optional node to ingest new documents into the vector store.
    
    Can be called separately to populate the knowledge base.
    """
    logger.info(f"[{state['run_id']}] Ingesting {len(documents)} documents")
    
    try:
        count = rag_node.ingest_documents(documents)
        logger.info(f"[{state['run_id']}] Ingested {count} document chunks")
    except Exception as e:
        logger.error(f"[{state['run_id']}] Document ingestion failed: {e}")
        state["errors"].append({
            "stage": "document_ingestion",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        })
    
    return state