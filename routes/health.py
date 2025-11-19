"""
Health check and root endpoints
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Text2SQL API",
        "version": "1.0.0",
        "status": "running"
    }


@router.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}

