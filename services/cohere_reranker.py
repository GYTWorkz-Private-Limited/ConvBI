"""
Cohere Reranker Service for improving search result relevance
Uses Cohere's rerank-v3.5 model for advanced reranking
"""
import os
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

try:
    import cohere
except ImportError:
    cohere = None

logger = logging.getLogger(__name__)

@dataclass
class RerankConfig:
    """Configuration for Cohere reranking"""
    model: str = "rerank-v3.5"
    top_k: int = 10
    max_chunks_per_doc: int = 10
    return_documents: bool = True

class CohereReranker:
    """
    Cohere Reranker service using rerank-v3.5 model
    Provides advanced reranking for hybrid search results
    """
    
    def __init__(self, api_key: Optional[str] = None, config: Optional[RerankConfig] = None):
        """
        Initialize Cohere reranker
        
        Args:
            api_key: Cohere API key (if None, uses COHERE_API_KEY env var)
            config: Reranking configuration
        """
        self.api_key = api_key or os.getenv("COHERE_API_KEY")
        self.config = config or RerankConfig()
        
        if not self.api_key:
            raise ValueError("Cohere API key is required. Set COHERE_API_KEY environment variable.")
        
        if not cohere:
            raise ImportError("Cohere package is not installed. Install with: pip install cohere")
        
        try:
            self.client = cohere.Client(api_key=self.api_key)
        except Exception as e:
            logger.error(f"Failed to initialize Cohere client: {e}")
            raise
    
    def rerank_results(
        self, 
        query: str, 
        documents: List[Dict[str, Any]], 
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Rerank search results using Cohere's rerank-v3.5 model
        
        Args:
            query: Original search query
            documents: List of document dictionaries from hybrid search
            top_k: Number of top results to return (defaults to config.top_k)
            
        Returns:
            List of reranked documents with updated scores
        """
        if not documents:
            return []
        
        top_k = top_k or self.config.top_k
        
        try:
            # Prepare documents for reranking
            rerank_documents = []
            for doc in documents:
                # Create searchable text from table information
                searchable_text = self._create_searchable_text(doc)
                rerank_documents.append({
                    "text": searchable_text,
                    "metadata": doc
                })
            
            # Extract text for reranking
            texts = [doc["text"] for doc in rerank_documents]
            
            # Perform reranking
            rerank_response = self.client.rerank(
                model=self.config.model,
                query=query,
                documents=texts,
                return_documents=self.config.return_documents
            )
            
            # Process reranked results
            reranked_results = []
            for result in rerank_response.results:
                original_doc = rerank_documents[result.index]["metadata"]
                
                # Update with reranked score and ranking
                reranked_doc = original_doc.copy()
                reranked_doc["rerank_score"] = result.relevance_score
                reranked_doc["rerank_rank"] = result.index
                reranked_doc["original_score"] = original_doc.get("score", 0.0)
                
                reranked_results.append(reranked_doc)
            
            # Apply top_k filtering
            final_results = reranked_results[:top_k]
            
            return final_results
            
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            raise
    
    def _create_searchable_text(self, doc: Dict[str, Any]) -> str:
        """
        Create searchable text from document metadata for reranking
        
        Args:
            doc: Document dictionary with table information
            
        Returns:
            Formatted text for reranking
        """
        # Extract key information
        table_name = doc.get("table_name", "")
        description = doc.get("table_description", "")
        database_name = doc.get("database_name", "")
        schema_name = doc.get("schema_name", "")
        
        # Create comprehensive searchable text
        searchable_parts = []
        
        # Table identification
        if table_name:
            searchable_parts.append(f"Table: {table_name}")
        
        if database_name:
            searchable_parts.append(f"Database: {database_name}")
        
        if schema_name:
            searchable_parts.append(f"Schema: {schema_name}")
        
        # Table description
        if description:
            searchable_parts.append(f"Description: {description}")
        
        # Column information
        columns = doc.get("columns_summary", [])
        if columns:
            column_info = []
            for col in columns[:10]:  # Limit to first 10 columns
                col_name = col.get("column_name", "")
                col_desc = col.get("description", "")
                col_type = col.get("data_type", "")
                
                if col_name:
                    col_text = f"{col_name} ({col_type})"
                    if col_desc:
                        col_text += f": {col_desc}"
                    column_info.append(col_text)
            
            if column_info:
                searchable_parts.append(f"Columns: {', '.join(column_info)}")
        
        # Primary and foreign keys
        primary_keys = doc.get("primary_key", [])
        if primary_keys:
            searchable_parts.append(f"Primary Keys: {', '.join(primary_keys)}")
        
        foreign_keys = doc.get("foreign_keys", [])
        if foreign_keys:
            fk_info = []
            for fk in foreign_keys[:5]:  # Limit foreign keys
                if isinstance(fk, dict) and "column" in fk:
                    fk_text = fk["column"]
                    if "references" in fk:
                        ref = fk["references"]
                        if isinstance(ref, dict) and "table" in ref:
                            fk_text += f" -> {ref['table']}"
                    fk_info.append(fk_text)
            
            if fk_info:
                searchable_parts.append(f"Foreign Keys: {', '.join(fk_info)}")
        
        return " | ".join(searchable_parts)
    
    def get_rerank_stats(self, original_results: List[Dict], reranked_results: List[Dict]) -> Dict[str, Any]:
        """
        Calculate statistics about reranking performance
        
        Args:
            original_results: Original search results
            reranked_results: Reranked search results
            
        Returns:
            Dictionary with reranking statistics
        """
        if not original_results or not reranked_results:
            return {}
        
        # Calculate score improvements
        score_changes = []
        rank_changes = []
        
        for i, reranked in enumerate(reranked_results):
            original_score = reranked.get("original_score", 0.0)
            rerank_score = reranked.get("rerank_score", 0.0)
            
            if original_score > 0:
                score_change = ((rerank_score - original_score) / original_score) * 100
                score_changes.append(score_change)
            
            # Find original rank
            table_name = reranked.get("table_name", "")
            original_rank = next(
                (j for j, orig in enumerate(original_results) 
                 if orig.get("table_name") == table_name), 
                len(original_results)
            )
            rank_change = original_rank - i
            rank_changes.append(rank_change)
        
        return {
            "total_documents": len(original_results),
            "reranked_documents": len(reranked_results),
            "avg_score_change": sum(score_changes) / len(score_changes) if score_changes else 0,
            "avg_rank_change": sum(rank_changes) / len(rank_changes) if rank_changes else 0,
            "score_improvements": len([s for s in score_changes if s > 0]),
            "rank_improvements": len([r for r in rank_changes if r > 0])
        }

def create_reranker(api_key: Optional[str] = None, config: Optional[RerankConfig] = None) -> CohereReranker:
    """
    Factory function to create CohereReranker instance
    
    Args:
        api_key: Cohere API key
        config: Reranking configuration
        
    Returns:
        CohereReranker instance
    """
    return CohereReranker(api_key=api_key, config=config)

