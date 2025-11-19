import os
from typing import Dict, List, Optional
from langchain_openai import AzureOpenAIEmbeddings
from langchain_core.embeddings import Embeddings
from services.qdrant.client import get_qdrant_client
from services.cohere_reranker import CohereReranker, RerankConfig

class FastEmbedSparseWrapper(Embeddings):
    """Wrapper for FastEmbed sparse embeddings to work with LangChain"""
    def __init__(self):
        from fastembed import SparseTextEmbedding
        self.model = SparseTextEmbedding(model_name="Qdrant/bm42-all-minilm-l6-v2-attentions")
    
    def embed_documents(self, texts):
        return list(self.model.embed(texts))
    
    def embed_query(self, text):
        return list(self.model.embed([text]))[0]

class HybridRetrieval:
    def __init__(self, collection_name: str = "semantics", use_reranking: bool = True):
        self.collection_name = collection_name
        self.use_reranking = use_reranking
        
        # Dense embeddings
        self.dense_embeddings = AzureOpenAIEmbeddings(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            model="text-embedding-3-large"
        )
        
        # Sparse embeddings
        self.sparse_embeddings = FastEmbedSparseWrapper()
        
        # Reranker (optional)
        self.reranker = None
        if self.use_reranking:
            try:
                rerank_config = RerankConfig(
                    model=os.getenv("COHERE_RERANK_MODEL", "rerank-v3.5"),
                    top_k=int(os.getenv("COHERE_RERANK_TOP_K", "10")),
                    return_documents=True
                )
                self.reranker = CohereReranker(config=rerank_config)
                pass  # Reranking enabled
            except Exception as e:
                self.use_reranking = False
    
    def create_collection(self):
        """Create collection with hybrid support"""
        client = get_qdrant_client()
        if client.collection_exists(self.collection_name):
            client.delete_collection(self.collection_name)
        
        from qdrant_client.models import SparseVectorParams
        client.create_collection(
            collection_name=self.collection_name,
            vectors_config={
                'dense': {
                    'size': 3072,
                    'distance': 'Cosine'
                }
            },
            sparse_vectors_config={
                'sparse': SparseVectorParams()
            }
        )
    
    def index_tables(self, semantics_data: Dict):
        """Index tables - one point per table with all data as payload"""
        # Always recreate collection to ensure correct configuration
        client = get_qdrant_client()
        if client.collection_exists(self.collection_name):
            client.delete_collection(self.collection_name)
        self.create_collection()
        
        # Process the semantics data
        schemas = semantics_data.get('schemas', {})
        total_tables = sum(len(schema_data.get('tables', [])) for schema_data in schemas.values())
        
        # Handle the exact structure you showed
        # Check if this is a single table structure (has database_name but no schemas)
        if "database_name" in semantics_data and "schemas" not in semantics_data:
            # Single table structure - store as one point
            table = semantics_data
            table_name = table.get('table_name', '')
            
            # Create searchable text content
            searchable_content = f"""
            {table.get('database_name', '')} {table.get('database_type', '')} {table.get('schema_name', '')} {table_name}
            {table.get('table_description', '')}
            """
            
            # Add column information to searchable content
            columns_summary = table.get('columns_summary', [])
            for col in columns_summary:
                searchable_content += f" {col.get('column_name', '')} {col.get('data_type', '')} {col.get('description', '')}"
            
            # Add index information to searchable content
            for idx in table.get('indexes', []):
                index_name = idx.get('index_name', '')
                index_columns = idx.get('columns', [])
                index_type = idx.get('index_type', '')
                if index_name:
                    searchable_content += f" index {index_name} {index_type}"
                if index_columns:
                    searchable_content += f" {' '.join(index_columns)}"
            
            # Generate both dense and sparse embeddings for the searchable content
            dense_vector = self.dense_embeddings.embed_query(searchable_content)
            sparse_vector_obj = self.sparse_embeddings.embed_query(searchable_content)
            
            # Store as single point with all table data in payload
            import uuid
            from qdrant_client.models import SparseVector
            point_id = str(uuid.uuid4())
            client.upsert(
                collection_name=self.collection_name,
                points=[
                    {
                        "id": point_id,
                        "vector": {
                            "dense": dense_vector,
                            "sparse": SparseVector(
                                indices=sparse_vector_obj.indices.tolist(),
                                values=sparse_vector_obj.values.tolist()
                            )
                        },
                        "payload": {
                            "database_name": table.get('database_name', ''),
                            "database_type": table.get('database_type', ''),
                            "schema_name": table.get('schema_name', ''),
                            "table_name": table_name,
                            "table_description": table.get('table_description', ''),
                            "primary_key": table.get('primary_key', []),
                            "foreign_keys": table.get('foreign_keys', []),
                            "columns_summary": columns_summary,
                            "indexes": table.get('indexes', []),
                            "column_count": table.get('column_count', 0),
                            "idempotency_key": table.get('idempotency_key', '')
                        }
                    }
                ]
            )
        else:
            # Handle nested schemas structure with BATCH PROCESSING
            self._batch_index_tables(semantics_data)
    
    def _batch_index_tables(self, semantics_data: Dict):
        """Batch process tables for maximum performance with chunking for large datasets"""
        import uuid
        from qdrant_client.models import SparseVector
        
        # Collect all tables and their data
        all_tables = []
        for schema_name, schema_data in semantics_data.get("schemas", {}).items():
            for table in schema_data.get("tables", []):
                all_tables.append({
                    'schema_name': schema_name,
                    'table': table
                })
        
        # Batch 1: Generate all searchable content (vectorized)
        searchable_contents = []
        for table_data in all_tables:
            schema_name = table_data['schema_name']
            table = table_data['table']
            table_name = table['table_name']
            
            # Create searchable text content
            searchable_content = f"{schema_name} {table_name} {table.get('description', '')}"
            
            # Add column information to searchable content
            for col in table.get('columns', []):
                searchable_content += f" {col.get('column_name', '')} {col.get('data_type', '')} {col.get('description', '')}"
            
            # Add index information to searchable content
            for idx in table.get('indexes', []):
                index_name = idx.get('index_name', '')
                index_columns = idx.get('columns', [])
                index_type = idx.get('index_type', '')
                if index_name:
                    searchable_content += f" index {index_name} {index_type}"
                if index_columns:
                    searchable_content += f" {' '.join(index_columns)}"
            
            searchable_contents.append({
                'content': searchable_content,
                'schema_name': schema_name,
                'table': table
            })
        
        # Batch 2: Generate all embeddings in batch (MASSIVE performance gain!)
        texts = [item['content'] for item in searchable_contents]
        
        # Generate embeddings in batch - this is the key optimization!
        # Instead of 26 individual API calls, we make just 2 batch calls!
        dense_vectors = self.dense_embeddings.embed_documents(texts)
        sparse_vectors = self.sparse_embeddings.embed_documents(texts)
        
        # Batch 3: Prepare all points for batch upsert (vectorized)
        points = []
        for i, item in enumerate(searchable_contents):
            schema_name = item['schema_name']
            table = item['table']
            table_name = table['table_name']
            
            point_id = str(uuid.uuid4())
            points.append({
                "id": point_id,
                "vector": {
                    "dense": dense_vectors[i],
                    "sparse": SparseVector(
                        indices=sparse_vectors[i].indices.tolist(),
                        values=sparse_vectors[i].values.tolist()
                    )
                },
                "payload": {
                    "schema_name": schema_name,
                    "table_name": table_name,
                    "description": table.get('description', ''),
                    "primary_key": table.get('primary_key', []),
                    "foreign_keys": table.get('foreign_keys', []),
                    "columns": table.get('columns', []),
                    "indexes": table.get('indexes', [])
                }
            })
        
        # Batch 4: Single upsert call for all points (MASSIVE performance gain!)
        # Instead of 26 individual upsert calls, we make just 1 batch call!
        client = get_qdrant_client()
        client.upsert(
            collection_name=self.collection_name,
            points=points
        )
    
    def search_tables(self, query: str, k: int = 20, use_reranking: Optional[bool] = None) -> List[Dict]:
        """
        Search for relevant tables using HYBRID search (dense + sparse) with optional reranking
        
        Args:
            query: Search query
            k: Number of results to return
            use_reranking: Override reranking setting (None = use instance default)
        """
        client = get_qdrant_client()
        
        # Generate both dense and sparse embeddings for the query
        dense_vector = self.dense_embeddings.embed_query(query)
        sparse_vector = self.sparse_embeddings.embed_query(query)
        
        # Determine if we should use reranking
        should_rerank = use_reranking if use_reranking is not None else self.use_reranking
        
        # Adjust k for reranking (get more results to rerank)
        search_k = k * 3 if should_rerank else k
        
        # HYBRID SEARCH: Single call using Qdrant's Query API with fusion
        from qdrant_client.models import Prefetch, FusionQuery, Fusion, SparseVector
        
        search_results = client.query_points(
            collection_name=self.collection_name,
            prefetch=[
                Prefetch(
                    query=dense_vector,
                    using="dense",  # Dense vector field name
                    limit=search_k * 2,  # Get more results for fusion
                    score_threshold=0.2
                ),
                Prefetch(
                    query=SparseVector(
                        indices=sparse_vector.indices.tolist(),
                        values=sparse_vector.values.tolist()
                    ),
                    using="sparse",  # Sparse vector field name
                    limit=search_k * 2,  # Get more results for fusion
                    score_threshold=0.2
                )
            ],
            query=FusionQuery(
                fusion=Fusion.RRF  # Reciprocal Rank Fusion
            ),
            limit=search_k,
            with_payload=True
        )
        
        # Convert results to list of dictionaries
        results = []
        search_results = search_results.points
        
        for result in search_results:
            results.append({
                "table_name": result.payload.get("table_name", ""),
                "database_name": result.payload.get("database_name", ""),
                "database_type": result.payload.get("database_type", ""),
                "schema_name": result.payload.get("schema_name", ""),
                "table_description": result.payload.get("table_description", result.payload.get("description", "")),
                "primary_key": result.payload.get("primary_key", []),
                "foreign_keys": result.payload.get("foreign_keys", []),
                "columns_summary": result.payload.get("columns_summary", result.payload.get("columns", [])),
                "indexes": result.payload.get("indexes", []),
                "column_count": result.payload.get("column_count", 0),
                "idempotency_key": result.payload.get("idempotency_key", ""),
                "score": result.score
            })
        
        # Apply reranking if enabled and reranker is available
        if should_rerank and self.reranker and results:
            reranked_results = self.reranker.rerank_results(query, results, k)
            
            # Add reranking metadata
            for i, result in enumerate(reranked_results):
                result["final_rank"] = i + 1
                result["reranking_applied"] = True
            
            return reranked_results
        
        # Return original results
        final_results = results[:k]
        for result in final_results:
            result["reranking_applied"] = False
        
        return final_results

