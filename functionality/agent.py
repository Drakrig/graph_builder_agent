
import os
from pathlib import Path
from typing import Literal
import json
from json_repair import repair_json
import logging

from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langchain_core.messages import SystemMessage, HumanMessage, RemoveMessage, AIMessage

from functionality.states import AgentState, MarkdownState, stage_chemas_verification, stages_schemas
from functionality.prompts import *
from functionality.cypher_queries import *
from functionality.graphs import *
from functionality.llm_calls import *
from functionality.vector_database import search_information_in_knowledge_base

logging.basicConfig(level=os.getenv("LOG_LEVEL", "DEBUG"))

def load_env():
    with open(".env", mode="r") as f:
        for line in f:
            if line.startswith("#") or "=" not in line:
                continue
            key, value = line.strip().split("=", 1)
            if key and value:
                os.environ[key] = value

def verify_json_schema(json_data: dict, stage_key:str):
    error_str = ""
    if not stage_chemas_verification[stage_key]["keys_presence_check"](json_data.keys()):
        error_str += "JSON keys presence check failed.\n"
        for k in json_data.keys():
            if k not in stages_schemas[stage_key]["keys"]:
                error_str += f"Unexpected key: {k}\n"
        for k in stages_schemas[stage_key]["keys"]:
            if k not in json_data.keys():
                error_str += f"Missing key: {k}\n"
    if stage_chemas_verification[stage_key].get("key_values_check", False):
        for key in stage_chemas_verification[stage_key]["key_values_check"]:
            if key not in json_data:
                continue
            func, error_msg = stage_chemas_verification[stage_key]["key_values_check"][key]
            if not func(json_data[key]):
                error_str += f"JSON key '{key}' check failed: {error_msg}\n"
    return error_str

def read_markdown_file(file_path: str) -> MarkdownState:
    """Read a markdown file and return its title and content.

    :param file_path: Path to the markdown file
    :type file_path: str
    :return: Dictionary with title and content of the markdown file
    :rtype: MarkdownState
    """
    path = Path(file_path)
    content = path.read_text()
    title = path.stem
    return {"title": title, "content": content}

def check_for_final_answer(last_message: AIMessage) -> bool:
    """Function to check if the last message is a final answer.

    :param state: Last message in the current message history.
    :type state: AIMessage
    :return: True if the last message is a final answer, False otherwise
    :rtype: bool
    """
    reasoning, cleaned_text = check_for_reasoning(last_message.content)
    logging.debug("Reasoning:", reasoning)
    logging.debug("Cleaned text:", cleaned_text)
    try:
        response = json.loads(cleaned_text)
        if not isinstance(response, list):
            raise ValueError("Output is not a list")
        return True
    except json.JSONDecodeError as e:
        logging.debug(f"JSON decode error: {e}")
        repaired_response = repair_json(cleaned_text)
        try:
            response = json.loads(repaired_response)
            logging.debug("JSON successfully repaired")
            if isinstance(response, list):
                return True
            else:
                logging.debug("Repaired JSON is not a list")
                logging.debug(f"Last message: {last_message}")
                return False
        except json.JSONDecodeError as e:
            return False

# State update functions

def stage_router(state:AgentState) -> AgentState:
    """Route the graph execution to the current stage. Needed so conditional edge works propely.

    :param state: Current agent state
    :type state: AgentState
    :return: Current state
    :rtype: AgentState
    """
    return state

# Node extraction loop
def agent_euristic_extract_nodes(state: AgentState) -> AgentState:
    """Function to extract nodes from a markdown document using an agent.

    :param state: Current state
    :type state: NodeExtractionAgentState
    :return: Updated state
    :rtype: NodeExtractionAgentState
    """
    #append_last_tool_message(state, "nodes_extraction_state")
    state["current_stage"] = "node_extraction_loop"
    agent = state["agent"]
    logging.debug("Message history: ", state["messages"])
    prompt = SystemMessage(node_extraction_prompt_euristic_agent)
    response = agent.invoke(
        [
            prompt, 
            HumanMessage(
                node_extraction_task_prompt.format(
                    title=state["markdown"]["title"], 
                    content=state["markdown"]["content"]
                    )
                )
        ] + state["messages"]
    )
    state["messages"].append(response)
    return state

def check_nodes_extraction_validity(state:AgentState) -> AgentState:
    """Check if the agent extraction stage produced valid output.

    :param state: Current agent state
    :type state: AgentState
    :return: Updated agent state
    :rtype: AgentState
    """
    message = ""
    for node in state["nodes"]:
        error_str = verify_json_schema(node, state["current_stage"])
        if len(error_str)>0:
            message += f"Node '{node.get('title', 'Unknown')}' schema validation errors:\n{error_str}\n"
    if len(message) > 0:
        logging.debug(message)
        state["messages"].append(
            HumanMessage(
                content=f"Please fix the following JSON schema errors and return only the corrected JSON:\n{message}"
                )
            )
        state["verification_status"] = "error"
    else: 
        state["verification_status"] = "valid"
    return state

def parse_nodes_from_response(state: AgentState) -> AgentState:
    """Function to parse the output of the node extraction agent.

    :param node: Output of the node extraction agent
    :type node: AgentState
    :return: Updated state
    :rtype: AgentState
    """
    last_message = state["messages"][-1].content
    try:
        nodes = json.loads(last_message)
        if not isinstance(nodes, list):
            raise ValueError("Output is not a list")
    except json.JSONDecodeError as e:
        logging.debug(f"JSON decode error: {e}")
        repaired_response = repair_json(last_message)
        try:
            nodes = json.loads(repaired_response)
            logging.debug("JSON successfully repaired")
        except json.JSONDecodeError as e:
            logging.debug(f"Error decoding repaired JSON: {e}")
            logging.debug(f"Original response: {response}")
            logging.debug(f"Repaired response: {repaired_response}")
    except ValueError as e:
        logging.debug(f"Value error: {e}")
    if isinstance(nodes[0], str):
        nodes = nodes[1:]
    if isinstance(nodes[0], list):
        nodes = nodes[0]
    state["nodes"] = nodes
    return state

# Searching for context stage

def agent_search_information_about_existing_nodes(state:AgentState) -> AgentState:
    """Function to search for existing nodes in the graph database.

    :param state: Current state
    :type state: AgentState
    :return: Updated state
    :rtype: AgentState
    """
    state["message_history"].extend(state["messages"])
    state["messages"] = [RemoveMessage(id=REMOVE_ALL_MESSAGES)]
    for node in state["nodes"]:
        is_exist, existing_node = find_node_in_graph(node)
        if not is_exist or existing_node[0]["description"] == "":
            similar_nodes = search_information_in_knowledge_base(node["title"], node["description"])
            if len(similar_nodes) > 0:
                node["verified_info"] = similar_nodes
                node["action"] = "compare" if not is_exist else "merge"
            else:
                node["action"] = "create"
        else:
            node["verified_info"] = existing_node[0]
            node["action"] = "merge"
    return state

# Update extracted nodes loop

def euristic_agent_update_extracted_nodes(state:AgentState) -> AgentState:
    """Function to choose next node to process in the extracted nodes list.

    :param state: Current state
    :type state: AgentState
    :return: Updated state
    :rtype: AgentState
    """
    logging.debug(f"Enetering update extracted nodes loop. Current iteration:{state["iteration"]+1} of {len(state["nodes"])}")
    state["current_stage"] = "update_extracted_nodes_loop"
    initial_iteration = state["iteration"]
    for node in state["nodes"][initial_iteration:]:
        if node["action"] == "create":
            state["iteration"] += 1
    return state

def euristic_agent_merge_descriptions_extracted_nodes(state:AgentState) -> AgentState:
    """Function to merge descriptions of extracted and existing nodes using an agent.

    :param state: Current state
    :type state: AgentState
    :return: Updated state
    :rtype: AgentState
    """
    logging.debug("Entering merge descriptions extracted nodes")
    state["current_stage"] = "merge_descriptions_extracted_nodes"
    node = state["nodes"][state["iteration"]]
    reasoning, step_result = merge_nodes_descriptions(state["agent"], state["markdown"], node, state["messages"])
    state["stage_step_result"]: dict = step_result
    return state

def compare_nodes(state:AgentState) -> AgentState:
    """Function to compare extracted node with existing information using an agent.

    :param state: Current state
    :type state: AgentState
    :return: Updated state
    :rtype: AgentState
    """
    logging.debug("Entering compare extracted nodes")
    state["current_stage"] = "compare_extracted_nodes"
    node = state["nodes"][state["iteration"]]
    reasoning, step_result = euristic_agent_compare_nodes(state["agent"], state["markdown"], node, state["messages"])
    state["stage_step_result"] = step_result
    return state

def update_extracted_nodes(state:AgentState) -> AgentState:
    """Function to update extracted nodes based on the comparison results.

    :param state: Current state
    :type state: AgentState
    :return: Updated state
    :rtype: AgentState
    """
    logging.debug("Updating extracted nodes")
    node = state["nodes"][state["iteration"]]
    if node["action"] == "merge":
        node["description"] = state["stage_step_result"]["description"]
    elif node["action"] == "compare":
        # Compare logic later
        comparison_result = state["stage_step_result"]
        if comparison_result["action_taken"] == "merge":
            node["title"] = comparison_result.get("title", node["title"])
            node["description"] = comparison_result.get("description", node["description"])
            node["type"] = comparison_result.get("type", node["type"])
        elif comparison_result["action_taken"] ==  "fix":
            node["title"] = comparison_result.get("title", node["title"])
            node["type"] = comparison_result.get("type", node["type"])
        elif comparison_result["action_taken"] ==  "enrich":# create
            node["description"] = comparison_result.get("description", node["description"])
            if node["title"] != comparison_result.get("title", node["title"]):
                node["title"] = comparison_result.get("title", node["title"])
            if node["type"] != comparison_result.get("type", node["type"]):
                node["type"] = comparison_result.get("type", node["type"])
    state["nodes"][state["iteration"]] = node
    state["current_stage"] = "update_extracted_nodes_loop"
    return state

def next_iterator_step(state: AgentState) -> AgentState:
    """Move to the next step in the current iterator.

    :param state: Current agent state
    :type state: AgentState
    :return: Updated agent state
    :rtype: AgentState
    """
    state["iteration"] += 1
    logging.debug(f"Moving to the next iteration step {state['iteration']}")
    return state

def update_message_history(state: AgentState) -> AgentState:
    """Update the message history in the agent state by moving current messages to history and clearing current messages.

    :param state: Current agent state
    :type state: AgentState
    :return: Updated agent state
    :rtype: AgentState
    """
    state["message_history"].extend(state["messages"])
    state["messages"] = [RemoveMessage(id=REMOVE_ALL_MESSAGES)]
    return state

# Update nodes in graph database

def agent_update_knowledge_graph_nodes(state: AgentState) -> AgentState:
    """Updates description for all nodes 

    :param state: Current state
    :type state: markdown
    :return: Updated state
    :rtype: markdown
    """
    for node in state["nodes"]:
        is_exist , _ = find_node_in_graph(node)
        if is_exist:
            update_node_description(node)
        else:
            create_new_node(node)
    return state

# Looking for existing relationships

def euristic_agent_find_relationships_for_nodes(state: AgentState) -> AgentState:
    """Function to find relationships between the nodes in the agent state.

    :param state: Current state
    :type state: RelationshipAgentState
    :return: Updated state
    :rtype: RelationshipAgentState
    """
    state["existing_relationships"] = []
    state["iteration"] = 0
    for i, node in enumerate(state["nodes"]):
        for other_node in state["nodes"][i:]:
            if node == other_node:
                continue
            existing_relationships = agent_chech_relationships_exist(node["title"], other_node["title"])
            if len(existing_relationships) > 0:
                state["existing_relationships"].extend(existing_relationships)
            else:
                logging.debug(f"No existing relationships found between {node['title']} and {other_node['title']}.")
    state["current_stage"] = "relationship_loop"
    return state

# Relationships loop

def euristic_agent_extract_relationships(state: AgentState) -> AgentState:
    """Function to relationships between the previously extracteed from the markdown document nodes using an LLM.

    :param state: Current state
    :type state: NodeExtAgentStateractionAgentState
    :return: Updated state
    :rtype: AgentState
    """
    state["current_stage"] = "relationship_loop"
    agent = state["agent"]
    prompt = SystemMessage(euristic_agent_node_relation_extraction_prompt)
    response = agent.invoke(
        [
            prompt, 
            HumanMessage(
                euristic_agent_node_relation_extraction_task_prompt.format(
                    nodes=json.dumps(state["nodes"]),
                    content=state["markdown"]["content"],
                    existing_relationships=state["existing_relationships"]
                    )
                )
        ] + state["messages"]
    )
    state["messages"].append(response)
    return state

def check_relationship_extraction_validity(state:AgentState) -> AgentState:
    """Check if the agent extraction stage produced valid output.

    :param state: Current agent state
    :type state: AgentState
    :return: Updated agent state
    :rtype: AgentState
    """
    message = ""
    for relationship in state["relationships"]:
        logging.debug(f"Checking relationship: {relationship}")
        error_str = verify_json_schema(relationship, state["current_stage"])
        if len(error_str)>0:
            message += f"Relationship '{relationship.get('from_node', 'Unknown')} - {relationship.get('to_node', 'Unknown')}' schema validation errors:\n{error_str}\n"
    if len(message) > 0:
        logging.debug(message)
        state["messages"].append(HumanMessage(content=f"Please fix the following JSON schema errors and return only the corrected JSON:\n{message}"))
        state["verification_status"] = "error"
    else: 
        state["verification_status"] = "valid"
    return state

def parse_relationship_extraction_result(state: AgentState) -> AgentState:
    """Parse the output of the relationship extraction agent.

    :param state: Current state
    :type state: AgentState
    :return: Updated state
    :rtype: AgentState
    """
    last_message = state["messages"][-1].content
    try:
        relationships = json.loads(last_message)
        if not isinstance(relationships, list):
            raise ValueError(f"Output is not a list {relationships}")
    except json.JSONDecodeError as e:
        logging.debug(f"JSON decode error: {e}")
        repaired_response = repair_json(last_message)
        try:
            relationships = json.loads(repaired_response)
            logging.debug("JSON successfully repaired")
        except json.JSONDecodeError as e:
            logging.debug(f"Error decoding repaired JSON: {e}")
            logging.debug(f"Original response: {last_message}")
            logging.debug(f"Repaired response: {repaired_response}")
    except ValueError as e:
        logging.debug(f"Value error: {e}")
    if isinstance(relationships[0], str):
        relationships = relationships[1:]
    if isinstance(relationships[0], list):
        relationships = relationships[0]
    state["relationships"] = relationships
    return state

def agent_update_knowledge_graph_relationships(state: AgentState) -> AgentState:
    """Updates relationships between nodes in the knowledge graph.

    :param state: Current state of the agent
    :type state: AgentState
    :return: Updated state
    :rtype: AgentState
    """
    for relationship in state["relationships"]:
        if relationship["action"] == "create":
            create_relationship(relationship)
        elif relationship["action"] == "merge" or relationship["action"] == "replace":
            merge_relationships(relationship)
        else:
            logging.debug(f"Ivalid action {relationship['action']} for relationship {relationship}")
    return state

###### Utility functions for edges ######

def return_current_stage(state:AgentState) -> str:
    """Return the current stage from the agent state.

    :param state: Current agent state
    :type state: AgentState
    :return: Current stage
    :rtype: str
    """
    return state["current_stage"]

def determine_action_nodes_extraction(state: AgentState) -> Literal["retry", "parse"]:
    """Function to determine the next action for the agent based on the current state.

    :param state: Current state
    :type state: AgentState
    :return: Next action
    :rtype: Literal["retry", "parse"]
    """
    if not check_for_final_answer(state["messages"][-1]):
        return "retry"
    else:
        logging.debug("Leaving loop.")
        return "parse"

def check_verification_status(state:AgentState) -> Literal["valid", "error"]:
    """Return the verification status of parsing last LLM response.

    :param state: Current agent state
    :type state: AgentState
    :return: Verification status ("valid" or "error")
    :rtype: Literal["valid", "error"]
    """
    return state["verification_status"]

def select_action_for_update_extracted_nodes(state:AgentState) -> Literal["done", "merge", "compare"]:
    """Function to control update extracted nodes loop.

    :param state: Current agent state
    :type state: AgentState
    :return: Next action
    :rtype: Literal["done", "merge", "compare"]
    """
    if state["iteration"] >= len(state["nodes"]):
        return "done"
    node = state["nodes"][state["iteration"]]
    if node["action"] == "merge":
        return "merge"
    else:
        return "compare"

def check_step_validity(state:AgentState)-> Literal["valid", "error"]:
    """Check if the agent step produced valid output.

    :param state: Current agent state
    :type state: AgentState
    :return: "valid" if valid, "error" otherwise
    :rtype: Literal["valid", "error"]
    """
    message = ""
    error_str = verify_json_schema(state["stage_step_result"], state["current_stage"])
    if len(error_str)>0:
        message += f"Step output schema validation errors:\n{error_str}\n"
    if len(message) > 0:
        logging.debug(message)
        state["messages"].append(HumanMessage(content=f"Please fix the following JSON schema errors and return only the corrected JSON:\n{message}"))
        state["verification_status"] = "error"
        return state
    state["verification_status"] = "valid"
    return state