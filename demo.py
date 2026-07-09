from uuid import uuid4

from packages.database.models.retrieval_trace import (
    RetrievalTrace,
    RetrievalTraceStatus,
)

trace = RetrievalTrace(
    tenant_id=uuid4(),
    query="test",
)

print(trace.status)
print(trace.retrieved_chunks)