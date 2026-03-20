import os
import logging
from neo4j import GraphDatabase, Result

from functionality.cypher_queries import *
from functionality.states import KnowledgeNodeState, RelationshipState
from functionality.vector_database import create_new_weaviate_record

logging.basicConfig(level=os.getenv("LOG_LEVEL", "DEBUG"))

def query_record_to_dict(record: Result) -> KnowledgeNodeState:
    """Convert a Neo4j query record to a dictionary representing a knowledge node.

    :param record: Record from Neo4j query
    :type record: Result
    :return: Dictionary representation of the knowledge node
    :rtype: KnowledgeNodeState
    """
    if record["n"]["description"] is None:
        description = ""
    else:
        description = record["n"]["description"]
    return {
        "title": record["n"]["title"],
        "description": description,
        "type": list(record["n"].labels)[0] if record["n"].labels else "Unknown" # Must be changed to list
    }

def properties_to_str(properties: dict) -> str:
    """Convert a dictionary of properties to a string representation.

    :param properties:  Dictionary of properties
    :type properties: dict
    :return: String representation of properties
    :rtype: str
    """
    string = ""
    for k, v in properties.items():
        if isinstance(v, list):
            # List to list of string with ''
            v = [f"'{item}'" for item in v]
        if isinstance(v, str):
            v = f"\"{v}\""
        string += f"{k}: {v}, "
    return string[:-2]  # Remove last comma and space

def find_node_in_graph(node: KnowledgeNodeState) -> tuple[bool, list]:
    """Check if a node already exists in the graph database.

    :param node: Node to check
    :type node: KnowledgeNodeState
    :return: True if node exists, False otherwise. Also returns the result from the database query.
    :rtype: tuple[bool, list]
    """
    query = cypher_query_check_node_exist.format(title=node["title"].replace("'", "\\'"))
    with GraphDatabase.driver(os.getenv("MEMGRAPH_URI"), auth=(os.getenv("MEMGRAPH_USER"),os.getenv("MEMGRAPH_PASSWORD"))) as client:
        records, summary, keys = client.execute_query(query)
    if len(records) > 0:
        records = [query_record_to_dict(record) for record in records]
    return len(records) > 0, records

def update_node_description(node: KnowledgeNodeState):
    """Update the description of an existing node in the graph database.

    :param node: Node to update
    :type node: KnowledgeNodeState
    """
    query = cypher_query_update_node_description.format(
        title=node["title"].replace("'", "\\'").replace("/", "\\/"),
        description=node["description"].replace("'", "\\'").replace('"', '\\"'),
        )
    logging.debug(f"Update node query: {query}")
    with GraphDatabase.driver(os.getenv("MEMGRAPH_URI"), auth=(os.getenv("MEMGRAPH_USER"),os.getenv("MEMGRAPH_PASSWORD"))) as client:
        records, summary, keys = client.execute_query(query)

def create_new_node(node: KnowledgeNodeState) -> None:
    """Create a new node in the graph database.

    :param node: Node to create
    :type node: KnowledgeNodeState
    """
    query = cypher_query_create_node.format(
        entity_type=node["type"],
        title=node["title"].replace("'", "\\'").replace("/", "\\/"),
        description=node["description"].replace("'", "\\'").replace("/", "\\/")
    )
    logging.debug(f"Create node query: {query}")
    with GraphDatabase.driver(os.getenv("MEMGRAPH_URI"), auth=(os.getenv("MEMGRAPH_USER"),os.getenv("MEMGRAPH_PASSWORD"))) as client:
        client.execute_query(query)
    # Add node to Weaviate 
    create_new_weaviate_record(node)

def agent_chech_relationships_exist(source_node_title:str, target_node_title:str) -> list[dict]:
    """Check if any relationships exists in the graph database between two nodes.

    :param relationship: Relationship with from_node and to_node titles
    :type relationship: RelationshipState
    :return: List of relationships if found, empty list if not found
    :rtype: list[dict]
    """
    query = cypher_query_find_nodes_relationships.format(
        node1_title=source_node_title.replace("'", "\\'"),
        node2_title=target_node_title.replace("'", "\\'")
    )
    with GraphDatabase.driver(
        os.getenv("MEMGRAPH_URI"), 
        auth=(
            os.getenv("MEMGRAPH_USER"),
            os.getenv("MEMGRAPH_PASSWORD")
            )
        ) as client:
        records, summary, keys = client.execute_query(query)
    result = [{
        "from_node": r["a.title"],
        "to_node": r["b.title"],
        "relationship_type": r["r"].type,
        "relationship_properties": dict(r["r"].items())
    } for r in records]
    return result

def check_relationship_exist(relationship: RelationshipState) -> tuple[bool, RelationshipState | None]:
    """Check if a specific relationship exists in the graph database between two nodes.

    :param relationship: Relationship with from_node and to_node titles
    :type relationship: RelationshipState
    :return: True if the relationship exists, False otherwise. Also returns the existing relationship if found.
    :rtype: tuple[bool, RelationshipState | None]
    """
    query = cypher_query_check_relationship_exist.format(
        node1_title=relationship["from_node"].replace("'", "\\'"),
        node2_title=relationship["to_node"].replace("'", "\\'"),
        relationship=relationship["relationship_type"]
    )
    with GraphDatabase.driver(os.getenv("MEMGRAPH_URI"), auth=(os.getenv("MEMGRAPH_USER"),os.getenv("MEMGRAPH_PASSWORD"))) as client:
        records, summary, keys = client.execute_query(query)
    if len(records) > 0:
        # Convert to RelationshipState
        existing_relationship = {
            "from_node": relationship["from_node"],
            "to_node": relationship["to_node"],
            "relationship_type": records[0]["r"].type,
            "relationship_properties": dict(records[0]["r"].items())
        }
    else:
        existing_relationship = None
    return len(records) > 0, existing_relationship


def create_relationship(relashionship:RelationshipState) -> None:
    """Creates relationship between two nodes in the graph database.

    :param relashionship: Relationship to create
    :type relashionship: RelationshipState
    """
    properties_str = properties_to_str(relashionship["properties"])
    query = cypher_query_create_relationship.format(
        node1_title=relashionship["from_node"].replace("'", "\\'"),
        node2_title=relashionship["to_node"].replace("'", "\\'"),
        relationship=relashionship["relationship"],
        properties=properties_str
    )
    logging.debug(f"Create relationship query: {query}")
    with GraphDatabase.driver(os.getenv("MEMGRAPH_URI"), auth=(os.getenv("MEMGRAPH_USER"),os.getenv("MEMGRAPH_PASSWORD"))) as client:
        client.execute_query(query)

def replace_relationship(new_relationship:RelationshipState, existing_relationship:RelationshipState) -> None:
    """Replace an existing relationship with a new relationship in the graph database by deleting the existing relationship and creating the new one.

    :param new_relationship: New relationship to replace with
    :type new_relationship: RelationshipState
    :param existing_relationship: Existing relationship to be replaced
    :type existing_relationship: RelationshipState
    """
    # Delete existing relationship
    with GraphDatabase.driver(os.getenv("MEMGRAPH_URI"), auth=(os.getenv("MEMGRAPH_USER"),os.getenv("MEMGRAPH_PASSWORD"))) as client:
        client.execute_query(cypher_query_delete_relationship.format(
            node1_title=existing_relationship["from_node"].replace("'", "\\'"),
            node2_title=existing_relationship["to_node"].replace("'", "\\'"),
            relationship_type=existing_relationship["target"]
        ))
    # Create new relationship
    create_relationship(new_relationship)
    
def merge_relationships(relationship:RelationshipState) -> None:
    """Merge two relationships by combining their properties, deleting the existing relationship, and creating a new merged relationship.

    :param relationship: Relationship to merge
    :type relationship: RelationshipState
    """
    existing_relationship = {
        "from_node": relationship["from_node"],
        "to_node": relationship["to_node"],
        "relationship_type": relationship["target"]
    }
    is_exist, existing_relationship = check_relationship_exist(existing_relationship)
    replace_relationship(relationship, existing_relationship)