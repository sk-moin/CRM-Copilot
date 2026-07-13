from __future__ import annotations

from langchain_core.embeddings import Embeddings


class MockEmbeddingProvider(Embeddings):
    DIMENSION = 384

    def embed_documents(self, texts):
        return [[0.1] * self.DIMENSION for _ in texts]

    def embed_query(self, text):
        return [0.1] * self.DIMENSION

    async def aembed_documents(self, texts):
        return self.embed_documents(texts)

    async def aembed_query(self, text):
        return self.embed_query(text)