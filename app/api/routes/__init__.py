# app/api/routes/__init__.py
from fastapi import APIRouter

from app.api.routes.retrieval_observability import router as retrieval_observability_router

api_router = APIRouter()
api_router.include_router(retrieval_observability_router)