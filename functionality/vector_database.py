import os
import weaviate
from weaviate.classes.query import MetadataQuery, Filter, Rerank, BM25Operator

from functionality.states import KnowledgeNodeState

def create_new_weaviate_record(node: KnowledgeNodeState) -> None:
    """Create a new record in Weaviate for the provided node.

    :param node: Node to create a record for
    :type node: KnowledgeNodeState
    """
    with weaviate.connect_to_custom(
    http_host=os.getenv("WEAVIATE_HTTP_HOST", "localhost"),
    http_port=int(os.getenv("WEAVIATE_HTTP_PORT", "8080")),
    http_secure=os.getenv("WEAVIATE_HTTP_SECURE", "false").lower() == "true",
    grpc_host=os.getenv("WEAVIATE_GRPC_HOST", "localhost"),
    grpc_port=int(os.getenv("WEAVIATE_GRPC_PORT", "8081")),
    grpc_secure=os.getenv("WEAVIATE_GRPC_SECURE", "false").lower() == "true") as client:
        nodes_collection = client.collections.get("Nodes")
        graph_nodes = nodes_collection.with_tenant("graph_nodes")
        graph_nodes.data.insert(
            {
                "title": node["title"],
                "text": node["description"],
                "category": node["type"]
            }
        )

def search_information_about_node_in_weaviate(node_title:str, node_description:str) -> list:
    """Function to search for a node in Weaviate database.

    :param node_title: Title of the node to search for
    :type node_title: str
    :param node_description: Description of the node to search for
    :type node_description: str
    :param node_type: Type of the node to search for
    :type node_type: str
    :return: List of matching records
    :rtype: list
    """
    with weaviate.connect_to_custom(
    http_host=os.getenv("WEAVIATE_HTTP_HOST", "localhost"),
    http_port=int(os.getenv("WEAVIATE_HTTP_PORT", "8080")),
    http_secure=os.getenv("WEAVIATE_HTTP_SECURE", "false").lower() == "true",
    grpc_host=os.getenv("WEAVIATE_GRPC_HOST", "localhost"),
    grpc_port=int(os.getenv("WEAVIATE_GRPC_PORT", "8081")),
    grpc_secure=os.getenv("WEAVIATE_GRPC_SECURE", "false").lower() == "true") as client:
        chunks_collection = client.collections.get("Chunks")
        response = chunks_collection.query.hybrid(
            alpha=0.5,
            query=node_title,
            query_properties=["title"],
            #bm25_operator=BM25Operator.or_(minimum_match=max([1,node["title"].split(" ").__len__()//2])),
            bm25_operator=BM25Operator.and_(),
            limit=3,
            #filters=(
            #    Filter.by_property("category").equal(node_type) |
            #    Filter.by_property("title").equal(node_title)
            #    ),
            rerank=Rerank(
                prop="text",
                query=node_description,
            ),
            return_metadata=MetadataQuery(score=True)
    )
    return response

def search_information_in_knowledge_base(node_title:str, node_description:str) -> list[dict]:
    """Find information about node in Weaviate based on node's title and description.

    :param node_title: Title of the node to search for
    :type node_title: str
    :param node_description: Description of the node to search for
    :type node_description: str
    :return: List of close matching nodes, empty list if no matches found
    :rtype: list[dict]
    """
    response = search_information_about_node_in_weaviate(node_title, node_description)
    # Filter out low scores
    response.objects = [o for o in response.objects[:3] if o.metadata.score >= 0.25] # Had to be checked!
    nodes = [
        {
            "title": o.properties["title"], 
            "description": o.properties["text"], 
            "type": o.properties["category"]
        } for o in response.objects
    ]
    return nodes