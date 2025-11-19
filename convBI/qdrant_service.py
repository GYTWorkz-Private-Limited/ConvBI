import time
from typing import Dict, Any
from services.hybrid_retrieval import HybridRetrieval


class QdrantService:
    def __init__(self, collection_name: str = "semantics", use_reranking: bool = True):
        self.collection_name = collection_name
        self.use_reranking = use_reranking
        self.hybrid_retrieval = HybridRetrieval(collection_name, use_reranking=use_reranking)
    
    def get_all_semantic_data(self, question: str, top_k: int = 10) -> Dict[str, Any]:
        try:
            t0 = time.time()
            # Search for relevant tables using hybrid retrieval with reranking
            results = self.hybrid_retrieval.search_tables(question, k=top_k * 2, use_reranking=self.use_reranking)
            t1 = time.time()
            
            # Count reranked results
            reranked_count = sum(1 for r in results if r.get('reranking_applied', False))
            
            organized = self._organize_results(results, top_k)
            t2 = time.time()
            
            organized["timings"] = {
                "hybrid_search_ms": int((t1 - t0) * 1000),
                "organize_ms": int((t2 - t1) * 1000),
                "total_ms": int((t2 - t0) * 1000),
                "reranking_applied": reranked_count > 0,
                "reranked_results": reranked_count
            }
            return organized
        except Exception as e:
            return {"relevant_tables": [], "all_tables": [], "semantics": {}}
    
    def _organize_results(self, results, top_k):
        relevant_tables = []
        all_tables = set()
        semantics = {}
        
        # Limit to top_k tables after reranking
        limited_results = results[:top_k]
        
        for result in limited_results:
            table_name = result.get("table_name")
            if table_name:
                relevant_tables.append(table_name)
            all_tables.add(table_name)
            
            semantics[table_name] = {
                "table_name": table_name,
                "description": result.get("table_description", result.get("description", "")),
                "primary_key": result.get("primary_key", []),
                "foreign_keys": result.get("foreign_keys", []),
                "columns": result.get("columns_summary", result.get("columns", [])),
                "indexes": result.get("indexes", [])
            }
        
        #print("Semantics:", semantics)
        return {
            "relevant_tables": relevant_tables,
            "all_tables": list(all_tables),
            "semantics": semantics
        }
     
