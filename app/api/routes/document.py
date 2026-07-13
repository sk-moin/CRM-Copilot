"""
app/api/routes/document.py

Document upload endpoints for the RAG knowledge base.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

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
)
from app.api.schemas.document import (
    DocumentProcessingResponse,
)
from app.rag.document_processing_service import (
    DocumentProcessingService,
)
from app.rag.models.document_processing_request import (
    DocumentProcessingRequest,
)
from packages.database.models import User

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


@router.post(
    "/upload",
    response_model=DocumentProcessingResponse,
    status_code=status.HTTP_201_CREATED,
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
) -> DocumentProcessingResponse:
    """
    Upload and process a document for the RAG knowledge base.
    """

    suffix = Path(file.filename).suffix

    with NamedTemporaryFile(
        delete=False,
        suffix=suffix,
    ) as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_path = Path(temp_file.name)

    try:
        request = DocumentProcessingRequest(
            tenant_id=current_user.tenant_id,
            organization_id=current_user.organization_id,
            owner_id=current_user.id,
            title=title or Path(file.filename).stem,
            filename=file.filename,
            storage_path=str(temp_path),
            document_type=suffix.lstrip(".").lower(),
            source_type="upload",
            mime_type=file.content_type,
            file_size=len(content),
        )

        result = await service.process(request)

        return DocumentProcessingResponse(
            document_id=result.document_id,
            status=result.status,
            chunk_count=result.chunk_count,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)