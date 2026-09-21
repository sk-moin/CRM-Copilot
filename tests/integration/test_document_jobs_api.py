"""Upload enqueueing and the status endpoint.

The point of the feature is that a caller gets an answer immediately and polls
for the rest. Both halves of that are checked here: upload must not do the
work, and the status route must tell the truth about a job in any state.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from sqlalchemy import select

import pytest

from app.api.routes import document as document_routes
from packages.database.models import KnowledgeDocument, Tenant
from packages.database.models.enums import DocumentProcessingStatus


async def _document(session, user, **overrides) -> KnowledgeDocument:
    document = KnowledgeDocument(
        tenant_id=user.tenant_id,
        org_id=user.org_id,
        owner_id=user.id,
        title="Acme notes",
        filename="notes.txt",
        storage_path="var/uploads/notes.txt",
        document_type="txt",
        source_type="upload",
        mime_type="text/plain",
        file_size=128,
        **{"processing_status": DocumentProcessingStatus.UPLOADED, **overrides},
    )

    session.add(document)
    await session.flush()

    return document


# --------------------------------------------------------------------------- #
# Upload
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_upload_returns_202_and_enqueues(authed_client, tmp_path):
    """202, not 201: the document is accepted, not finished."""

    with patch.object(
        document_routes,
        "enqueue",
        AsyncMock(return_value="job-123"),
    ) as enqueued, patch.object(
        document_routes.config,
        "UPLOAD_DIR",
        str(tmp_path),
    ):
        response = await authed_client.post(
            "/api/v1/documents/upload",
            files={"file": ("notes.txt", b"Acme renewal notes.", "text/plain")},
        )

    assert response.status_code == 202

    body = response.json()

    assert body["status"] == DocumentProcessingStatus.UPLOADED.value
    assert body["job_id"] == "job-123"

    enqueued.assert_awaited_once()

    task, document_id, tenant_id = enqueued.await_args.args

    assert task == "ingest_document"
    assert document_id == body["document_id"]

    # The worker is another process, so the file has to outlive the request.
    # A NamedTemporaryFile here would be gone by the time the job ran.
    written = list(Path(tmp_path).iterdir())

    assert len(written) == 1
    assert written[0].read_bytes() == b"Acme renewal notes."


@pytest.mark.asyncio
async def test_a_failed_enqueue_does_not_leave_the_file_behind(
    authed_client,
    _async_session,
    seeded_user,
    tmp_path,
):
    """A file nothing will ever read is litter; the route cleans up."""

    with patch.object(
        document_routes,
        "enqueue",
        AsyncMock(side_effect=RuntimeError("redis is down")),
    ), patch.object(
        document_routes.config,
        "UPLOAD_DIR",
        str(tmp_path),
    ):
        response = await authed_client.post(
            "/api/v1/documents/upload",
            files={"file": ("notes.txt", b"Acme renewal notes.", "text/plain")},
        )

    assert response.status_code == 500
    assert list(Path(tmp_path).iterdir()) == []

    # The row is committed before the job is queued. Leaving it at UPLOADED
    # would mean a document polled forever, pointing at a file just deleted.
    rows = await _async_session.execute(
        select(KnowledgeDocument).where(
            KnowledgeDocument.tenant_id == seeded_user.tenant_id
        )
    )
    created = list(rows.scalars().all())

    assert len(created) == 1
    assert created[0].processing_status == DocumentProcessingStatus.FAILED
    assert created[0].error_message


# --------------------------------------------------------------------------- #
# Status
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_status_of_a_queued_document(
    authed_client,
    _async_session,
    seeded_user,
):
    document = await _document(_async_session, seeded_user)

    response = await authed_client.get(
        f"/api/v1/documents/{document.id}/status"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == DocumentProcessingStatus.UPLOADED.value
    assert body["chunk_count"] == 0
    assert body["processed_at"] is None
    assert body["error_message"] is None


@pytest.mark.asyncio
async def test_status_of_a_ready_document(
    authed_client,
    _async_session,
    seeded_user,
):
    document = await _document(
        _async_session,
        seeded_user,
        processing_status=DocumentProcessingStatus.READY,
        processing_started_at=datetime(2026, 3, 1, 9, 0, 0),
        processed_at=datetime(2026, 3, 1, 9, 2, 0),
        chunk_count=7,
    )

    response = await authed_client.get(
        f"/api/v1/documents/{document.id}/status"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == DocumentProcessingStatus.READY.value
    assert body["chunk_count"] == 7
    assert body["processing_started_at"] is not None
    assert body["processed_at"] is not None
    assert body["error_message"] is None


@pytest.mark.asyncio
async def test_status_of_a_failed_document_carries_the_reason(
    authed_client,
    _async_session,
    seeded_user,
):
    """The route serialises the stored reason rather than dropping it.

    This seeds the column, so it proves the route returns the field and
    nothing about what gets written into it. That the written value is safe
    is proved in tests/unit/jobs/test_commit_visibility.py, by raising a
    real exception carrying a connection string.
    """

    document = await _document(
        _async_session,
        seeded_user,
        processing_status=DocumentProcessingStatus.FAILED,
        error_message="Unsupported document type: .xyz",
    )

    response = await authed_client.get(
        f"/api/v1/documents/{document.id}/status"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == DocumentProcessingStatus.FAILED.value
    assert body["error_message"] == "Unsupported document type: .xyz"


@pytest.mark.asyncio
async def test_another_tenants_document_is_not_found(
    authed_client,
    _async_session,
    seeded_user,
):
    """404, not 403: the existence of the id must not leak across tenants."""

    other_tenant = Tenant(name="Other Tenant", subdomain="other-tenant")

    _async_session.add(other_tenant)
    await _async_session.flush()

    foreign = KnowledgeDocument(
        tenant_id=other_tenant.id,
        org_id=seeded_user.org_id,
        owner_id=seeded_user.id,
        title="Their notes",
        filename="theirs.txt",
        storage_path="var/uploads/theirs.txt",
        document_type="txt",
        source_type="upload",
        mime_type="text/plain",
        file_size=64,
        processing_status=DocumentProcessingStatus.READY,
        chunk_count=3,
    )

    _async_session.add(foreign)
    await _async_session.flush()

    response = await authed_client.get(
        f"/api/v1/documents/{foreign.id}/status"
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_an_unknown_document_is_404(authed_client):
    response = await authed_client.get(
        f"/api/v1/documents/{uuid4()}/status"
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_status_requires_authentication(client, _async_session, seeded_user):
    """`client` has no user override, unlike `authed_client`."""

    document = await _document(_async_session, seeded_user)

    response = await client.get(f"/api/v1/documents/{document.id}/status")

    assert response.status_code in (401, 403)


# --------------------------------------------------------------------------- #
# Upload is a trust boundary
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_an_unsupported_type_is_rejected_at_the_boundary(
    authed_client,
    tmp_path,
):
    """415 now, rather than a 202 and three doomed attempts in the worker."""

    with patch.object(
        document_routes,
        "enqueue",
        AsyncMock(return_value="job-1"),
    ) as enqueued, patch.object(
        document_routes.config,
        "UPLOAD_DIR",
        str(tmp_path),
    ):
        response = await authed_client.post(
            "/api/v1/documents/upload",
            files={"file": ("payload.exe", b"not a document", "application/octet-stream")},
        )

    assert response.status_code == 415
    enqueued.assert_not_awaited()

    # Nothing unreadable reaches the shared upload directory.
    assert list(Path(tmp_path).iterdir()) == []


@pytest.mark.asyncio
async def test_an_oversized_document_is_rejected(authed_client, tmp_path):
    """Both processes share one directory and nothing else bounds it."""

    with patch.object(
        document_routes,
        "enqueue",
        AsyncMock(return_value="job-1"),
    ) as enqueued, patch.object(
        document_routes.config,
        "UPLOAD_DIR",
        str(tmp_path),
    ), patch.object(
        document_routes.config,
        "MAX_UPLOAD_BYTES",
        64,
    ):
        response = await authed_client.post(
            "/api/v1/documents/upload",
            files={"file": ("big.txt", b"x" * 65, "text/plain")},
        )

    assert response.status_code == 413
    enqueued.assert_not_awaited()
    assert list(Path(tmp_path).iterdir()) == []


@pytest.mark.asyncio
async def test_an_empty_document_is_rejected(authed_client, tmp_path):
    with patch.object(
        document_routes,
        "enqueue",
        AsyncMock(return_value="job-1"),
    ) as enqueued, patch.object(
        document_routes.config,
        "UPLOAD_DIR",
        str(tmp_path),
    ):
        response = await authed_client.post(
            "/api/v1/documents/upload",
            files={"file": ("empty.txt", b"", "text/plain")},
        )

    assert response.status_code == 400
    enqueued.assert_not_awaited()
