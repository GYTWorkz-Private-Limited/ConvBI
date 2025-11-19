from convBI.qdrant_service import QdrantService

def run(state):

    try:
        collection_name = state.get("collection_name", "semantics")
        
        qdrant_service = QdrantService(collection_name=collection_name)
        semantic_data = qdrant_service.get_all_semantic_data(state["question"])

        semantics = semantic_data.get('semantics', {})
        
        state["semantic_info"] = semantics
        
        selected = semantic_data.get("relevant_tables", [])
        state["selected_tables"] = selected
        
    except Exception as e:
        state["selected_tables"] = []
        state["semantic_info"] = {}

    return state

