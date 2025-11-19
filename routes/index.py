"""
Index semantics endpoint
"""

from fastapi import APIRouter, HTTPException, Form
from pathlib import Path
import json
import os

from services.hybrid_retrieval import HybridRetrieval

router = APIRouter(prefix="/api/v1", tags=["index"])


@router.post("/index")
async def index_template_endpoint(
    collection_name: str = Form(default="semantics"),
    template_path: str = Form(...)
):
    """
    Index semantics data from a template file to Qdrant.
    
    Parameters:
    - collection_name: Name of the Qdrant collection (default: "semantics")
    - template_path: Path to the template JSON file (relative to project root or absolute)
    
    The template file should contain:
    {
        "schemas": {
            "schema_name": {
                "tables": [
                    {
                        "table_name": "...",
                        "description": "...",
                        "primary_key": [...],
                        "foreign_keys": [...],
                        "columns": [...],
                        "indexes": [...]
                    }
                ]
            }
        }
    }
    """
    try:
        # Resolve template path
        template_file = Path(template_path)
        
        # If relative path, try relative to project root
        if not template_file.is_absolute():
            # Get project root (parent of routes folder)
            project_root = Path(__file__).parent.parent
            template_file = project_root / template_path
        
        # Check if file exists
        if not template_file.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Template file not found: {template_path}"
            )
        
        # Load template JSON
        try:
            with open(template_file, "r") as f:
                template_data = json.load(f)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid JSON in template file: {str(e)}"
            )
        
        # Validate semantics data structure
        if "schemas" not in template_data:
            raise HTTPException(
                status_code=400,
                detail="Template must contain a 'schemas' key with schema definitions"
            )
        
        # Initialize HybridRetrieval with collection name
        hybrid_retrieval = HybridRetrieval(
            collection_name=collection_name,
            use_reranking=bool(os.getenv("COHERE_API_KEY"))
        )
        
        # Index the tables
        hybrid_retrieval.index_tables(template_data)
        
        # Count total tables and indexes
        total_tables = 0
        total_indexes = 0
        for schema_data in template_data.get("schemas", {}).values():
            for table in schema_data.get("tables", []):
                total_tables += 1
                total_indexes += len(table.get("indexes", []))
        
        return {
            "status": "success",
            "message": f"Successfully indexed {total_tables} tables to Qdrant",
            "collection_name": collection_name,
            "template_path": str(template_file),
            "total_tables": total_tables,
            "total_indexes": total_indexes,
            "total_schemas": len(template_data.get("schemas", {}))
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # Log the full error for debugging
        import traceback
        print(f"Error in index endpoint: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}",
        )

