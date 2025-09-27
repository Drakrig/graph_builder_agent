import os
import logging
import json
from json_repair import repair_json

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from functionality.states import MarkdownState, KnowledgeNodeState
from functionality.prompts import (
    node_comparision_prompt_euristic_agent,
    node_comparision_prompt_euristic_agent_task_prompt,
    node_description_rewriting_prompt_euristic_agent,
    node_description_rewriting_prompt_euristic_agent_task_prompt
)

logging.basicConfig(level=os.getenv("LOG_LEVEL", "DEBUG"))

def check_for_reasoning(text:str, token="</think>")->tuple[str|None, str]:
    """Function to check if the text contatins reasoning token.

    :param text: Input text
    :type text: str
    :param token: Reasoning token, default is "</think>"
    :type token: str
    :return: Reasoning if found, else None and response text
    :rtype: tuple[str|None, str]
    """
    reasoning_token = "</think>"
    if isinstance(text, str) and reasoning_token in text:
        # Remove reasoning content
        reasoning, response = text.split(reasoning_token)
        return reasoning, response
    return None, text

def merge_nodes_descriptions(
    agent: ChatOllama, 
    markdown: 
    MarkdownState, 
    node: KnowledgeNodeState, 
    messages:list) -> tuple[str, str]:
    """Merge the description of the extracted node with the verified information using LLM.

    :param agent: LLM agent to use for merging
    :type agent: ChatOllama
    :param markdown: Document from which the node was extracted
    :type markdown: MarkdownState
    :param node: Extracted node
    :type node: KnowledgeNodeState
    :return: Model reasoning and merged description
    :rtype: tuple[str, str]
    """
    if isinstance(node["verified_info"], dict):
        if node["verified_info"].get("description", "") == "":
            return "", node["description"]
    prompt = SystemMessage(node_description_rewriting_prompt_euristic_agent)
    verified_info = json.dumps(node["verified_info"])
    task = HumanMessage(
                node_description_rewriting_prompt_euristic_agent_task_prompt.format(
                    title=markdown["title"], 
                    content=markdown["content"],
                    node_title=node["title"],
                    node_description=node["description"],
                    verified_information=verified_info
                )
    )
    response = agent.invoke([prompt, task] + messages)
    reasoning, response = check_for_reasoning(response.content)
    try:
        json_response = json.loads(response)
    except json.JSONDecodeError as e:
        logging.debug("Error decoding JSON")
        repaired_response = repair_json(response)
        try:
            json_response = json.loads(repaired_response)
            logging.debug("JSON successfully repaired")
        except json.JSONDecodeError as e:
            logging.debug(f"Error decoding repaired JSON: {e}")
            logging.debug(f"Original response: {response}")
            logging.debug(f"Repaired response: {repaired_response}")
            return reasoning, json_response
    return reasoning, json_response

def euristic_agent_compare_nodes(
    agent: ChatOllama, 
    markdown:MarkdownState, 
    node:KnowledgeNodeState,
    messages:list) -> KnowledgeNodeState:
    """Compare the extracted node with existing information using LLM.

    :param agent: LLM agent to use for comparison
    :type agent: ChatOllama
    :param node: Extracted node
    :type node: KnowledgeNodeState
    :return: Comparison result with additional 'action_taken' filed or error message
    :rtype: KnowledgeNodeState
    """
    prompt = SystemMessage(node_comparision_prompt_euristic_agent)
    task = HumanMessage(
        node_comparision_prompt_euristic_agent_task_prompt.format(
            title=markdown["title"],
            content=markdown["content"],
            node_title=node["title"],
            node_description=node["description"],
            node_type=node["type"],
            chunks=json.dumps(node["verified_info"])
        )
    )
    response = agent.invoke([prompt, task] + messages)
    reasoning, response = check_for_reasoning(response.content)
    try:
        result = json.loads(response)
        if "action_taken" not in result:
            raise ValueError("Missing 'action_taken' in response")
        return reasoning, result
    except json.JSONDecodeError as e:
        logging.debug("Error decoding JSON")
        repaired_response = repair_json(response)
        try:
            result = json.loads(repaired_response)
            logging.debug("JSON successfully repaired")
            if "action_taken" not in result:
                raise ValueError("Missing 'action_taken' in repaired response")
            return reasoning, result
        except json.JSONDecodeError as e:
            logging.debug(f"Error decoding repaired JSON: {e}")
            logging.debug(f"Original response: {response}")
            logging.debug(f"Repaired response: {repaired_response}")
            return reasoning, response
    return reasoning, response