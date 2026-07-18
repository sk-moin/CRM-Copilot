"""
app/api/dependencies.py

FastAPI dependency injection utilities.

This module wires together:

- Authentication
- Core CRM services
- Audit services
- Chat services
- Retrieval observability
- RAG services
"""

from __future__ import annotations

from fastapi import (
    Depends,
    HTTPException,
    status,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    JWTError,
    decode_jwt,
)
from app.core.config import Settings
from app.rag.embeddings.mock_embedding_provider import (
    MockEmbeddingProvider,
)
from packages.database.models import User

from packages.database.repositories.user_repository import (
    UserRepository,
)
from packages.database.repositories.knowledge_document_repository import (
    KnowledgeDocumentRepository,
)
from packages.database.repositories.document_chunk_repository import (
    DocumentChunkRepository,
)
from packages.database.repositories.retrieval_trace_repository import (
    RetrievalTraceRepository,
)
from packages.database.repositories.retrieved_chunk_repository import (
    RetrievedChunkRepository,
)

from app.services.company_service import CompanyService
from app.services.contact_service import ContactService
from app.services.opportunity_service import OpportunityService
from app.services.task_service import TaskService
from app.services.audit_service import AuditService
from app.services.chat_service import ChatService

from app.services.llm.base import LLMProvider

from app.services.retrieval_trace_service import (
    RetrievalTraceService,
)
from app.services.retrieved_chunk_service import (
    RetrievedChunkService,
)
from app.agent.factory import build_agent
from app.agent.service import AgentService
from app.agent.builders.prompt_builder import PromptBuilder

# --------------------------------------------------------------------------- #
# Authentication
# --------------------------------------------------------------------------- #

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(
        HTTPBearer(),
    ),
) -> User:
    """
    Return the authenticated user.
    """

    try:
        payload = decode_jwt(
            credentials.credentials,
        )

    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        ) from exc

    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")

    if user_id is None or tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    repository = UserRepository(
        db,
        tenant_id,
    )

    user = await repository.get_by_id(
        user_id,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


# --------------------------------------------------------------------------- #
# CRM Services
# --------------------------------------------------------------------------- #

def get_company_service(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyService:
    return CompanyService(
        session=db,
        current_user=current_user,
    )


def get_contact_service(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContactService:
    return ContactService(
        session=db,
        current_user=current_user,
    )


def get_opportunity_service(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OpportunityService:
    return OpportunityService(
        session=db,
        current_user=current_user,
    )


def get_task_service(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskService:
    return TaskService(
        session=db,
        current_user=current_user,
    )


def get_audit_service(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AuditService:
    return AuditService(
        session=db,
        tenant_id=current_user.tenant_id,
        current_user=current_user,
    )


# --------------------------------------------------------------------------- #
# Chat
# --------------------------------------------------------------------------- #

def get_llm_provider() -> LLMProvider:
    """
    Return the configured LLM provider.
    """

    from app.core.config import Settings
    from app.services.llm.providers.mock_provider import (
        MockProvider,
    )

    settings = Settings()

    return MockProvider(
        settings,
    )



# --------------------------------------------------------------------------- #
# Retrieval Observability
# --------------------------------------------------------------------------- #

def get_retrieval_trace_service(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RetrievalTraceService:
    """
    Factory for RetrievalTraceService.
    """
    repository = RetrievalTraceRepository(
        db,
        current_user.tenant_id,
    )

    return RetrievalTraceService(
        repository,
    )


def get_retrieved_chunk_service(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RetrievedChunkService:
    """
    Factory for RetrievedChunkService.
    """
    repository = RetrievedChunkRepository(
        db,
        current_user.tenant_id,
    )

    return RetrievedChunkService(
        repository,
    )


# --------------------------------------------------------------------------- #
# RAG Components
# --------------------------------------------------------------------------- #

from app.rag.loaders.parser import (
    DocumentParser,
    create_document_parser,
)

from app.rag.splitters.text_splitter import (
    TextSplitter,
    create_text_splitter,
)

from app.rag.embeddings.embedding_provider import (
    EmbeddingProvider,
    create_embedding_provider,
)

from packages.database.repositories.knowledge_document_repository import (
    KnowledgeDocumentRepository,
)

from packages.database.repositories.document_chunk_repository import (
    DocumentChunkRepository,
)


def get_document_parser() -> DocumentParser:
    """
    Return the configured document parser.
    """
    return create_document_parser()


def get_text_splitter() -> TextSplitter:
    """
    Return the configured text splitter.
    """
    return create_text_splitter()


def get_embedding_provider():

    return create_embedding_provider()


def get_document_repository(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeDocumentRepository:
    """
    Repository for KnowledgeDocument.
    """
    return KnowledgeDocumentRepository(
        session=db,
        tenant_id=current_user.tenant_id,
    )


def get_chunk_repository(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentChunkRepository:
    """
    Repository for DocumentChunk.
    """
    return DocumentChunkRepository(
        session=db,
        tenant_id=current_user.tenant_id,
    )

# --------------------------------------------------------------------------- #
# Retrieval Repositories
# --------------------------------------------------------------------------- #

def get_retrieval_trace_repository(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RetrievalTraceRepository:
    """
    Repository for RetrievalTrace.
    """
    return RetrievalTraceRepository(
        session=db,
        tenant_id=current_user.tenant_id,
    )


def get_retrieved_chunk_repository(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RetrievedChunkRepository:
    """
    Repository for RetrievedChunk.
    """
    return RetrievedChunkRepository(
        session=db,
        tenant_id=current_user.tenant_id,
    )

# --------------------------------------------------------------------------- #
# Vector Store
# --------------------------------------------------------------------------- #

from app.rag.vectorstores.pgvector_store import PGVectorStore


def get_vector_store(
    chunk_repository: DocumentChunkRepository = Depends(
        get_chunk_repository,
    ),
    embedding_provider: EmbeddingProvider = Depends(
        get_embedding_provider,
    ),
) -> PGVectorStore:
    """
    Create the tenant-aware PGVector store.
    """
    return PGVectorStore(
        repository=chunk_repository,
        embedding_provider=embedding_provider,
    )


# --------------------------------------------------------------------------- #
# Retriever
# --------------------------------------------------------------------------- #

from app.rag.retrievers.retriever import Retriever


def get_retriever(
    vector_store: PGVectorStore = Depends(
        get_vector_store,
    ),
) -> Retriever:
    """
    Create the semantic retriever.
    """
    return Retriever(
        vector_store=vector_store,
    )


# --------------------------------------------------------------------------- #
# Retrieval Service
# --------------------------------------------------------------------------- #

from app.rag.retrieval_service import RetrievalService


def get_retrieval_service(
    retriever: Retriever = Depends(
        get_retriever,
    ),
    retrieval_trace_repository: RetrievalTraceRepository = Depends(
        get_retrieval_trace_repository,
    ),
    retrieved_chunk_repository: RetrievedChunkRepository = Depends(
        get_retrieved_chunk_repository,
    ),
) -> RetrievalService:
    """
    Create the RetrievalService.
    """
    return RetrievalService(
        retriever=retriever,
        retrieval_trace_repository=retrieval_trace_repository,
        retrieved_chunk_repository=retrieved_chunk_repository,
    )


# --------------------------------------------------------------------------- #
# Document Processing Service
# --------------------------------------------------------------------------- #

from app.rag.document_processing_service import (
    DocumentProcessingService,
)


def get_document_processing_service(
    parser: DocumentParser = Depends(
        get_document_parser,
    ),
    splitter: TextSplitter = Depends(
        get_text_splitter,
    ),
    document_repository: KnowledgeDocumentRepository = Depends(
        get_document_repository,
    ),
    chunk_repository: DocumentChunkRepository = Depends(
        get_chunk_repository,
    ),
    vector_store: PGVectorStore = Depends(
        get_vector_store,
    ),
) -> DocumentProcessingService:
    """
    Create the DocumentProcessingService.
    """
    return DocumentProcessingService(
        parser=parser,
        splitter=splitter,
        document_repository=document_repository,
        chunk_repository=chunk_repository,
        vector_store=vector_store,
    )


# --------------------------------------------------------------------------- #
# RAG Chain
# --------------------------------------------------------------------------- #

from app.rag.chains.rag_chain import (
    RAGChain,
    build_rag_chain,
)


def get_rag_chain(
    
    llm: LLMProvider = Depends(
        get_llm_provider,
    ),
) -> RAGChain:
    """
    Create the RAGChain.
    """
    return build_rag_chain(
        provider=llm,
    )


# --------------------------------------------------------------------------- #
# RAG Service
# --------------------------------------------------------------------------- #

from app.rag.rag_service import (
    RAGService,
)


def get_rag_service(
    retrieval_service: RetrievalService = Depends(
        get_retrieval_service,
    ),
    rag_chain: RAGChain = Depends(
        get_rag_chain,
    ),
) -> RAGService:
    """
    Create the high-level RAG service.
    """
    return RAGService(
        retrieval_service=retrieval_service,
        rag_chain=rag_chain,
    )

# --------------------------------------------------------------------------- #
# AI Agent
# --------------------------------------------------------------------------- #


def get_agent_service(
    retrieval_service: RetrievalService = Depends(
        get_retrieval_service,
    ),
    rag_chain: RAGChain = Depends(
        get_rag_chain,
    ),
) -> AgentService:
    """
    Create the AI Agent.
    """

    prompt_builder = PromptBuilder()

    return build_agent(
        retrieval_service=retrieval_service,
        rag_chain=rag_chain,
        prompt_builder=prompt_builder,
    )


def get_chat_service(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    agent_service: AgentService = Depends(get_agent_service),
) -> ChatService:
    return ChatService(
        session=db,
        current_user=current_user,
        agent_service=agent_service,
    )

# --------------------------------------------------------------------------- #
# Public exports
# --------------------------------------------------------------------------- #

__all__ = [
    # Authentication
    "get_current_user",

    # CRM Services
    "get_company_service",
    "get_contact_service",
    "get_opportunity_service",
    "get_task_service",
    "get_audit_service",

    # Chat
    "get_llm_provider",
    "get_chat_service",

    # Retrieval Observability
    "get_retrieval_trace_service",
    "get_retrieved_chunk_service",

    # Low-level RAG Components
    "get_document_parser",
    "get_text_splitter",
    "get_embedding_provider",

    # Repositories
    "get_document_repository",
    "get_chunk_repository",
    "get_retrieval_trace_repository",
    "get_retrieved_chunk_repository",

    # Vector Search
    "get_vector_store",
    "get_retriever",

    # RAG Services
    "get_document_processing_service",
    "get_retrieval_service",
    "get_rag_chain",
    "get_rag_service",

    # AI Agent
    "get_agent_service",
]