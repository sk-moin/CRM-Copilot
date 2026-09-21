"""
app/api/routes/document.py

Document upload endpoints for the RAG knowledge base.
"""

from __future__ import annotations

import logging
import ntpath
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)

from app.api.dependencies import (
    get_current_user,
    get_document_processing_service,
    get_document_repository,
)
from app.api.schemas.document import (
    DocumentEnqueuedResponse,
    DocumentStatusResponse,
)
from app.core import config
from app.jobs.queue import enqueue
from app.rag.document_processing_service import (
    DocumentProcessingService,
)
from app.rag.loaders.parser import DocumentParser
from packages.database.repositories.knowledge_document_repository import (
    KnowledgeDocumentRepository,
)
from app.rag.models.document_processing_request import (
    DocumentProcessingRequest,
)
from packages.database.models import User

logger = logging.getLogger(__name__)

# One megabyte at a time: large enough that a normal document is a couple of
# reads, small enough that nothing big is ever resident.
_UPLOAD_CHUNK_BYTES = 1024 * 1024


# The multipart filename is raw client input: unvalidated, unbounded, and
# it ends up on the document row, which the status endpoint serves back.
# Kept for the caller's benefit -- being told which of their files failed
# is the point -- but reduced to something safe to echo first.
_MAX_FILENAME = 120

# Nothing past this is examined. Multipart will hand over a filename of any
# size, and scanning a megabyte of it on the event loop costs a fifth of a
# second before the real work starts.
_MAX_RAW_FILENAME = 4096


def _safe_filename(raw: str | None) -> str:
    """A display name fit to store and serve back.

    Drops any directory part, caps the length so a long name cannot crowd
    the failure reason out of a truncated `error_message`, and removes
    control characters -- a newline would split a log line and an ESC would
    colour a terminal.
    """

    # `ntpath.basename` rather than `Path(...).name`, on purpose. `Path` is
    # platform-dependent: on Windows it strips backslashes, on Linux --
    # where compose runs this app -- a backslash is an ordinary filename
    # character and a Windows-style path survives whole. A suite running on
    # Windows can never observe that difference. ntpath treats both
    # separators the same everywhere.
    # Bounded from the end, not the start: the basename and the extension
    # are both at the tail, so trimming the front costs nothing real.
    name = ntpath.basename((raw or "")[-_MAX_RAW_FILENAME:])

    # Capped before the per-character filter below, which is O(n) on
    # whatever the client sent; this bounds that work to 120 characters.
    if len(name) > _MAX_FILENAME:
        stem, dot, suffix = name.rpartition(".")

        if dot and len(suffix) + 1 < _MAX_FILENAME:
            # Trim the stem and keep the extension. Truncating from the
            # front instead would drop it and turn a merely absurd name
            # into a misleading 415.
            name = stem[: _MAX_FILENAME - len(suffix) - 1] + "." + suffix
        else:
            # A "suffix" longer than the whole budget is not an extension.
            # Slicing the stem by the difference goes negative and trims
            # the wrong end: that returned 9001 characters for
            # `"a." + "b" * 9000`.
            name = name[:_MAX_FILENAME]

    name = "".join(ch for ch in name if ch.isprintable()).strip()

    # `..` is a traversal fragment, not a name to show anyone.
    if not name.strip("."):
        return "document"

    return name or "document"


class _TooLarge(Exception):
    """Internal signal, so the partial file is removed before the 413."""


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


@router.post(
    "/upload",
    response_model=DocumentEnqueuedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    service: DocumentProcessingService = Depends(
        get_document_processing_service,
    ),
    current_user: User = Depends(
        get_current_user,
    ),
) -> DocumentEnqueuedResponse:
    """Accept a document and queue it for ingestion.

    Returns 202, not 201: parsing, chunking and embedding happen in the worker
    afterwards. Embedding a large PDF on CPU takes minutes, and doing it here
    held the connection open for the whole time and lost the work if it
    dropped. Poll `GET /documents/{id}/status`.
    """

    # Rejected here rather than in the worker. A type the parser cannot read
    # would otherwise take a 202, occupy the queue for three doomed attempts,
    # and only then tell the caller what was wrong with their request.
    display_name = _safe_filename(file.filename)
    suffix = Path(display_name).suffix.lower()

    if suffix not in DocumentParser.SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                "Unsupported document type "
                f"{suffix or '(none)'}. Supported: "
                + ", ".join(sorted(DocumentParser.SUPPORTED_EXTENSIONS))
            ),
        )

    # Written to a configured directory rather than NamedTemporaryFile: the
    # worker is a different process and cannot read a handle from this one.
    # The task deletes it when the document is safely indexed.
    upload_dir = Path(config.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    stored_path = upload_dir / f"{uuid4().hex}{suffix}"

    # Streamed in chunks with the cap enforced as it goes, rather than
    # `await file.read()` into one bytes object. A Content-Length check
    # would not help here: Starlette has already parsed the multipart body
    # by the time this handler runs, and the header is client-supplied
    # anyway. This bounds both what is held in memory and what lands on the
    # shared upload directory, using the bytes actually received.
    size = 0

    try:
        with stored_path.open("wb") as sink:
            while chunk := await file.read(_UPLOAD_CHUNK_BYTES):
                size += len(chunk)

                if size > config.MAX_UPLOAD_BYTES:
                    raise _TooLarge()

                sink.write(chunk)

    except _TooLarge:
        stored_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                "Document exceeds the maximum upload size of "
                f"{config.MAX_UPLOAD_BYTES} bytes."
            ),
        )

    except Exception:
        # A full disk or a client that disconnects mid-upload would
        # otherwise leave the partial file behind with no row referring to
        # it, so nothing would ever clean it up.
        stored_path.unlink(missing_ok=True)

        logger.exception("documents.upload.write_failed")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store the uploaded document.",
        )

    if size == 0:
        stored_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded document is empty.",
        )

    document_id: UUID | None = None

    try:
        request = DocumentProcessingRequest(
            tenant_id=current_user.tenant_id,
            org_id=current_user.org_id,
            owner_id=current_user.id,
            title=title or Path(display_name).stem,
            filename=display_name,
            storage_path=str(stored_path),
            document_type=suffix.lstrip(".").lower(),
            source_type="upload",
            mime_type=file.content_type,
            file_size=size,
        )

        document = await service.create_document(request)
        document_id = document.id

        job_id = await enqueue(
            "ingest_document",
            str(document.id),
            str(current_user.tenant_id),
        )

        return DocumentEnqueuedResponse(
            document_id=document.id,
            status=document.processing_status.value
            if hasattr(document.processing_status, "value")
            else str(document.processing_status),
            job_id=job_id,
        )

    except Exception as exc:
        # The file is only useful to a job that exists; drop it if enqueuing
        # or persistence failed, so a failed upload does not leave litter.
        stored_path.unlink(missing_ok=True)

        logger.exception("documents.upload.failed")

        # The row commits before the job is queued, so a failed enqueue would
        # otherwise leave a document sitting at UPLOADED forever, pointing at
        # the file just deleted. Record the truth instead: nothing is coming.
        await _mark_unqueued(service, document_id)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to accept the document.",
        ) from exc



async def _mark_unqueued(
    service: DocumentProcessingService,
    document_id: UUID | None,
) -> None:
    """Settle a document whose job never made it onto the queue.

    Best effort: the caller is already failing, and turning a cleanup error
    into a different 500 would only hide the original cause.
    """

    if document_id is None:
        return

    try:
        await service.document_repository.mark_failed(
            document_id,
            error_message=(
                "The document could not be queued for processing. "
                "Please upload it again."
            ),
        )
        await service.document_repository.session.commit()
    except Exception:
        logger.exception("documents.upload.cleanup_failed")


@router.get(
    "/{document_id}/status",
    response_model=DocumentStatusResponse,
)
async def get_document_status(
    document_id: UUID,
    repository: KnowledgeDocumentRepository = Depends(
        get_document_repository,
    ),
    current_user: User = Depends(
        get_current_user,
    ),
) -> DocumentStatusResponse:
    """Progress of a queued ingestion. Tenant-scoped by the repository."""

    document = await repository.get_by_id(document_id)

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    return DocumentStatusResponse(
        document_id=document.id,
        status=document.processing_status.value
        if hasattr(document.processing_status, "value")
        else str(document.processing_status),
        processing_started_at=document.processing_started_at,
        processed_at=document.processed_at,
        chunk_count=document.chunk_count or 0,
        error_message=document.error_message,
    )