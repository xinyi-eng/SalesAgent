"""
Knowledge Base API v1
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional
import os
from pathlib import Path

from app.schemas.knowledge import (
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeSearchResult,
    KnowledgeIngestRequest,
    KnowledgeIngestResponse,
    KnowledgeStats,
    SPINQuestionRequest,
    SPINQuestionResponse,
    ConversationContextRequest,
    ConversationContextResponse
)
from app.services.rag import PDFParser, TextChunker, EmbeddingService, VectorStore
from app.services.rag.embedding import EmbeddingService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

# Initialize services (singleton pattern)
_pdf_parser = PDFParser()
_text_chunker = TextChunker(chunk_size=500, overlap=50)
_embedding_service = EmbeddingService()
_vector_store = VectorStore(use_milvus=False)  # Use in-memory for now, can switch to Milvus

# Document store (in-memory for now, should use database in production)
_documents = {}
_chunk_counter = 0


async def ingest_document(file_path: str, category: str) -> dict:
    """Background task to ingest a document."""
    global _chunk_counter

    try:
        # Parse PDF
        doc_result = _pdf_parser.parse_file(file_path)

        # Extract sections
        sections = _pdf_parser.extract_sections(doc_result["full_text"])

        # Chunk by paragraph
        chunks = _text_chunker.chunk_by_paragraph(
            doc_result["full_text"],
            source=doc_result["file_name"],
            metadata={
                "category": category,
                "page_count": doc_result["page_count"]
            }
        )

        # Add embeddings
        embedded_chunks = await _embedding_service.embed_with_metadata(
            chunks,
            source_name=doc_result["file_name"]
        )

        # Update chunk IDs
        for chunk in embedded_chunks:
            _chunk_counter += 1
            chunk["id"] = f"chunk_{_chunk_counter}"
            chunk["document_id"] = file_path

        # Store in vector database
        _vector_store.add_chunks(embedded_chunks)

        return {
            "status": "completed",
            "chunk_count": len(embedded_chunks)
        }

    except Exception as e:
        return {
            "status": "failed",
            "error": str(e)
        }


@router.post("/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(request: KnowledgeSearchRequest):
    """
    Search the knowledge base for relevant information.

    This endpoint takes a query and returns the most relevant knowledge chunks.
    """
    try:
        # Generate query embedding
        query_embedding = await _embedding_service.embed_text(request.query)

        # Search vector store
        results = _vector_store.search(
            query_embedding=query_embedding,
            top_k=request.top_k,
            source_filter=request.source_filter
        )

        # Convert to response format
        search_results = [
            KnowledgeSearchResult(
                id=r["id"],
                text=r["text"],
                source=r["source"],
                score=r["score"],
                metadata=r.get("metadata", {})
            )
            for r in results
        ]

        return KnowledgeSearchResponse(
            results=search_results,
            query=request.query,
            total=len(search_results)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest", response_model=KnowledgeIngestResponse)
async def ingest_document_endpoint(
    request: KnowledgeIngestRequest,
    background_tasks: BackgroundTasks
):
    """
    Ingest a new document into the knowledge base.

    Supports PDF files. The document is processed in the background.
    """
    # Validate file exists
    if not os.path.exists(request.file_path):
        raise HTTPException(status_code=404, detail=f"File not found: {request.file_path}")

    # Validate file extension
    if not request.file_path.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Create document record
    doc_id = f"doc_{len(_documents) + 1}"
    _documents[doc_id] = {
        "id": doc_id,
        "name": os.path.basename(request.file_path),
        "source_type": "pdf",
        "category": request.category,
        "file_path": request.file_path,
        "status": "processing"
    }

    # Start background processing
    background_tasks.add_task(ingest_document, request.file_path, request.category)

    return KnowledgeIngestResponse(
        document_id=doc_id,
        status="processing",
        chunk_count=0,
        message="Document queued for processing"
    )


@router.get("/documents", response_model=list)
async def list_documents():
    """List all documents in the knowledge base."""
    return list(_documents.values())


@router.get("/documents/{doc_id}", response_model=dict)
async def get_document(doc_id: str):
    """Get details of a specific document."""
    if doc_id not in _documents:
        raise HTTPException(status_code=404, detail="Document not found")
    return _documents[doc_id]


@router.get("/stats", response_model=KnowledgeStats)
async def get_knowledge_stats():
    """Get knowledge base statistics."""
    counts = _vector_store.count()

    # Count documents by category
    docs_by_category = {}
    for doc in _documents.values():
        cat = doc.get("category", "unknown")
        docs_by_category[cat] = docs_by_category.get(cat, 0) + 1

    return KnowledgeStats(
        total_documents=len(_documents),
        total_chunks=counts.get("total", 0),
        documents_by_category=docs_by_category,
        chunks_by_source=counts
    )


@router.post("/spin/questions", response_model=SPINQuestionResponse)
async def generate_spin_questions(request: SPINQuestionRequest):
    """
    Generate SPIN questions based on customer context.

    Uses the knowledge base to find relevant SPIN model content
    and generates personalized questions.
    """
    # Build search query from customer info
    query = f"{request.customer_industry} {request.customer_scale} "
    query += " ".join(request.pain_points)

    # Search for relevant SPIN content
    query_embedding = await _embedding_service.embed_text(query)
    results = _vector_store.search(
        query_embedding=query_embedding,
        top_k=5,
        source_filter=None
    )

    # For demo, return structured SPIN questions
    # In production, would use LLM to generate based on retrieved context
    spin_questions = {
        "situation_questions": [
            f"请描述一下{request.customer_industry}行业当前的发展状况？",
            f"贵公司目前的业务规模有多大？",
            "你们目前有多少销售团队成员？"
        ],
        "problem_questions": [
            f"在{request.customer_industry}行业，您遇到最大的挑战是什么？",
            f"目前销售团队在{request.pain_points[0] if request.pain_points else '客户开发'}方面表现如何？",
            "您认为现有销售流程中有哪些地方可以改进？"
        ],
        "implication_questions": [
            "这个问题如果不解决，对您的业务会有什么影响？",
            "市场竞争日益激烈，这给您带来了哪些压力？",
            "如果成单周期继续延长，会影响哪些关键指标？"
        ],
        "need_payoff_questions": [
            "如果有一种方法能帮您缩短成单周期，您想了解吗？",
            "您希望通过这次合作实现什么具体目标？",
            "对我们来说，最重要的是帮您解决什么问题？"
        ],
        "context_used": [r["text"][:100] + "..." for r in results[:3]]
    }

    return SPINQuestionResponse(**spin_questions)


@router.post("/conversation/context", response_model=ConversationContextResponse)
async def get_conversation_context(request: ConversationContextRequest):
    """
    Get relevant knowledge for conversation context.

    Used during practice sessions to retrieve relevant knowledge
    based on scenario type and customer profile.
    """
    # Build search query
    query = f"{request.scenario_type} "
    query += f"{request.customer_profile.get('industry', '')} "
    query += f"{request.customer_profile.get('role', '')} "
    if request.topic_focus:
        query += f" {request.topic_focus}"

    # Search knowledge base
    query_embedding = await _embedding_service.embed_text(query)
    results = _vector_store.search(
        query_embedding=query_embedding,
        top_k=5
    )

    # Extract talking points from results
    talking_points = []
    if results:
        # Extract key phrases from top results
        for r in results[:3]:
            text = r["text"]
            if len(text) > 50:
                talking_points.append(text[:200] + "...")

    return ConversationContextResponse(
        relevant_knowledge=[
            KnowledgeSearchResult(
                id=r["id"],
                text=r["text"],
                source=r["source"],
                score=r["score"],
                metadata=r.get("metadata", {})
            )
            for r in results
        ],
        suggested_topics=[request.scenario_type, request.customer_profile.get("industry", "")],
        talking_points=talking_points
    )


@router.post("/ingest-all", response_model=dict)
async def ingest_all_documents():
    """
    Ingest all PDF documents from the raw data directory.

    This is a convenience endpoint to quickly populate the knowledge base.
    """
    raw_data_dir = Path("C:/Users/zsndz/Desktop/SalesAgent/原始数据")

    if not raw_data_dir.exists():
        raise HTTPException(status_code=404, detail="Raw data directory not found")

    results = []

    for pdf_file in raw_data_dir.glob("*.pdf"):
        try:
            # Determine category from filename
            filename_lower = pdf_file.name.lower()
            if "spin" in filename_lower:
                category = "spin"
            elif "战略营销" in filename_lower or "新战略营销" in filename_lower:
                category = "strategic_marketing"
            elif "解决方案销售" in filename_lower or "solution" in filename_lower:
                category = "solution_selling"
            else:
                category = "general"

            # Ingest document
            result = await ingest_document(str(pdf_file), category)
            results.append({
                "file": pdf_file.name,
                "status": result["status"],
                "chunks": result.get("chunk_count", 0)
            })

            # Update document record
            doc_id = f"doc_{len(_documents) + 1}"
            _documents[doc_id] = {
                "id": doc_id,
                "name": pdf_file.name,
                "source_type": "pdf",
                "category": category,
                "file_path": str(pdf_file),
                "status": result["status"]
            }

        except Exception as e:
            results.append({
                "file": pdf_file.name,
                "status": "failed",
                "error": str(e)
            })

    return {
        "total": len(results),
        "results": results
    }