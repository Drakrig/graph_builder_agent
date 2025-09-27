from langchain_ollama import ChatOllama
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage
from typing import TypedDict, Annotated

class MarkdownState(TypedDict):
    title: str
    content: str

class KnowledgeNodeState(TypedDict):
    title: str
    description: str
    type: str
    is_main: bool

class RelationshipState(TypedDict):
    from_node: str
    to_node: str
    relationship_type: str
    relationship_properties: dict

    def __eq__(self, other):
        if not isinstance(other, RelationshipState):
            return NotImplemented
        return (self.from_node == other.from_node and
                self.to_node == other.to_node and
                self.relationship_type == other.relationship_type and
                self.relationship_properties == other.relationship_properties)

class AgentState(TypedDict):
    agent: ChatOllama
    current_stage: str
    iteration: int
    stage_step_result: dict
    verification_status: str
    markdown: MarkdownState
    messages: Annotated[list[AnyMessage], add_messages]
    message_history: list[AnyMessage]
    nodes: list[KnowledgeNodeState]
    existing_relationships: list[RelationshipState]
    relationships: list[RelationshipState]

stages_schemas = {
    "node_extraction_loop": {
        "keys": {"title", "description", "type", "is_main"}
    },
    "compare_extracted_nodes": {
        "keys": {"title", "description", "type", "action_taken"}, 
    },
    "merge_descriptions_extracted_nodes": {
        "keys": {"description"}
    },
    "relationship_loop": {
        "keys": {
            "from_node", 
            "to_node", 
            "relationship",
            "properties",
            "action",
            "target_relationship"
            },
        "actions": {"create", "replace", "drop", "merge"}
    },
}

stage_chemas_verification = {
    "node_extraction_loop": {
        "keys_presence_check": lambda keys: set(keys) == stages_schemas["node_extraction_loop"]["keys"],
        "key_values_check": {
            "type" : ( 
                lambda value: len(value.split(" ")) == 1,
                "The 'type' field must be a single word without spaces.",
            )
        }

    },
    "compare_extracted_nodes": {
        "keys_presence_check": lambda keys: set(keys) == stages_schemas["compare_extracted_nodes"]["keys"],
        "key_values_check": {
            "type" : ( 
                lambda value: len(value.split(" ")) == 1,
                "The 'type' field must be a single word without spaces.",
            )
        }
    },
    "merge_descriptions_extracted_nodes": {
        "keys_presence_check": lambda keys: set(keys) == stages_schemas["merge_descriptions_extracted_nodes"]["keys"],
    },

    "relationship_loop": {
        "keys_presence_check": lambda keys: all([key in stages_schemas["relationship_loop"]["keys"] for key in keys]),
        "key_values_check": {
            "action": (lambda value:
                value in {"create", "replace", "drop", "merge"},
                "The 'action' field must be one of: create, replace, drop, merge."
                ),
        }
    }
}