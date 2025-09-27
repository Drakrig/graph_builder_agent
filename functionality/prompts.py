node_extraction_prompt_euristic_agent = """Enable deep thinking subroutine.
**Agent Instructions**

You are an expert information analyst and knowledge integrator. 

### Task Instructions
You will be given a markdown document.
Your task is to:

1. **Extract Nodes**

   * Identify all significant standalone entities (nodes) such as Characters, Locations, Organizations, Artifacts, Events, Enemies or Lore.
   * For each node, determine its title, type, and whether it is the main subject (usually, the main node is the one whose title matches or closely resembles the document title).
   * Node type **must** be exactly one word e.g., "Character", "Location", "Lore" etc. but not limited to these, and **must** consist only letters without other characters like '/', '-', '&' etc.
   * Node's description will be used later for searching relevant information in the vector database.
        
2. **Return final JSON**

   * The final response must be a JSON array of enriched nodes in the following format:

   ```json
   [
       {
           "title": "NodeTitle",
           "description": "Concise summary (1–3 sentences).",
           "type": "NodeType",
           "is_main": true
       },
       {
           "title": "NodeTitle",
           "description": "Concise summary (1–3 sentences).",
           "type": "NodeType",
           "is_main": false
       },
       ...
   ]
   ```

   * Output only JSON, no explanations."""
node_extraction_task_prompt = """Document title: {title}
Document content:
{content}"""

node_description_rewriting_prompt_euristic_agent = """Enable deep thinking subroutine.
**Agent Instructions**

You are an expert information analyst and knowledge integrator. 

### Task Instructions
You will be given: 
    1. A markdown document.
    2. An extracted node from the document.
    3. Verified information from one of two sources:
        - Information about the node with the same title from the knowledge graph.
        - Information probably related to the node extracted from the vector database.
Your task is to:

1. **Enrich Node Description**

    * Use the provided information to enrich the node's description.
    * If the information from the knowledge graph is present, use it to combine both descriptions to provide a more comprehensive description.
    * If the information from the knowledge graph is absent, use the information from the vector database as well as extracted from the document to create a comprehensive description of the node.
        
2. **Return final JSON**

   * The final response must be a JSON in the following format:

   ```json
   {
        "description": "Enriched concise summary (1–3 sentences)."
   }
   ```

   * Output only JSON, no explanations."""

node_description_rewriting_prompt_euristic_agent_task_prompt = """Document title: {title}
Document content:
{content}
Extracted node:
Title: {node_title}
Description: {node_description}
Verified information:
{verified_information}
"""

node_comparision_prompt_euristic_agent = """Enable deep thinking subroutine.
**Agent Instructions**

You are an expert information analyst and knowledge integrator. 

### Task Instructions
You will be given: 
    1. A markdown document.
    2. An extracted node from the document.
    3. Chunks of information about other nodes extracted from the vector database.
Your task is to:

1. **Compare Nodes**

   * Compare the extracted node with each chunk.
   * Determine whether the extracted node represents the **same entity** as the chunk:

     * **Same entity → `"merge"`**: combine information from both the extracted node and the chunk into a comprehensive description. Correct title/type if needed but make sure that type is exactly **one** word that represents the entity general characteristic like "Character", "Location", "Lore" etc.
     * **Not same entity but useful → `"enrich"`**: add relevant information from the chunk to the node’s description.
     * **Same entity but only title/type needs correction → `"fix"`**: correct without adding new descriptive content.
     * **Otherwise → `"none"`**: keep the original node.
   * Process all chunks in order, updating the node step by step.
        
2. **Return final JSON**

   * The final response must be a JSON in the following format:

   ```json
    {
          "title": "NodeTitle",
          "description": "Concise summary (1–3 sentences).",
          "type": "NodeType",
          "action_taken": "merge" | "fix" | "enrich" | "none",
    }
   ```

   * Output only JSON, no explanations."""
node_comparision_prompt_euristic_agent_task_prompt = """Document title: {title}
Document content:
{content}
Extracted node:
Title: {node_title}
Description: {node_description}
Type: {node_type}
Chunks of information about other nodes:
{chunks}"""

euristic_agent_node_relation_extraction_prompt = """Enable deep thinking subroutine.
**Agent Instructions**

You are an expert information analyst and knowledge integrator. 

### Task Instructions
You will be given:
    1. A list of nodes with its properties (title, type, description) from the knowledge graph.
    2. A markdown document that describes nodes marked as "Main" in the list.
    3. A list of relationships between nodes that already exist in the graph database.
    
Your task is to:

1. **Identify Relationships Between Nodes**

   * Identify **all** possible relationships between **all** pairs of provided nodes based on the content of the document.
   * Use a simple and clear definitions for relationship types like `FRIEND`, `WORKS_AT`, `LOCATED_IN`, `PARTICIPATED_IN` etc. but not limited to these examples.
   * Add properties only if explicitly supported by the document (e.g., `since: 2020`, `role: speaker`).
   * Properties must reflect only the relationships characteristics, not the nodes metadata like node description.
   * Prefer general relationship types (e.g., `FRIEND` over `BEST_FRIEND`), keeping extra details as properties.
   * If no useful properties are available, return an empty object `{}`.

2. **Verify Relationships**

    * Analyze identified relationships:
        - If any relationship already exists between the nodes pair → compare them with the relationships that already exist in the graph database using the **Comparison of Relationships Guidelines** below.
        - If no relationships exist → include it in the final JSON.
    * Make sure that you processed **all** relationships you found initially.
    * Only after resolving all relationships, return the final JSON.

***Comparison of Relationships Guidelines**

    * Relationship that extracted from the document is considered as new relationship.

    * When comparing the new relationship with the existing relationships, the final decision must be one of the following:
        - "create" - the new relationship is unique and should be added to the graph. 
        - "merge" - the new relationship is similar to one of the existing relationships and should be merged with it, combining their properties. 
        - "replace" - the new relationship is more accurate or relevant than one of the existing relationships and should replace it. 
        - "drop - the new relationship doesn't provide any additional value and should be discarded.
    
    * The simplified decision tree is as follows:
        - If the new relationship is more general → merge.
        - If the new relationship is more relevant → replace.
        - If the new relationship is duplicate or redundant → drop.
        - If the new relationship is unique → create.
    
    * "target_relationship" must be included only for merge and replace actions.
    * Avoid informational oversaturation. The examples below provide guidance on how to handle such situations. 
    
    **Examples:**

    You have the following relationships:
    New relationship:
    {
        "from_node": Node1Title,
        "to_node": Node1Title,
        "new_relationship": "FAMILY_MEMBER"
        "properties": {}
    }
    Existing relationships:
    [
        {
            "from_node": Node1Title,
            "to_node": Node1Title,
            "relationship": "SISTER",
            "properties": {}
        },
        {
            "from_node": Node1Title,
            "to_node": Node1Title,
            "relationship": "FRIEND", 
            "properties": {"closeness": "best"}
        }
    ]
    In this case, the new relationship "FAMILY_MEMBER" is similar to "SISTER", but it is more general. But since "SISTER" is also an important detail, you must preserve it as a property of the merged relationship. Therefore, the action should be "merge" and the result will be:
    {
        "relationship": "FAMILY_MEMBER", 
        "properties": {"type": "sister"},
        "action": "merge",
        "target_relationship": "SISTER"
    }

    You have the following relationships:
    New relationship:
    {
        "from_node": Node1Title,
        "to_node": Node1Title,
        "new_relationship": "MENTOR",
        "properties": {}
    }
    Existing relationships:
    [   
        {
            "from_node": Node1Title,
            "to_node": Node1Title,
            "relationship": "TEACHER"
            "properties": {}
        }
    ]
    In this case, the new relationship "MENTOR" is similar to "TEACHER" and doen't provide any additional value. Therefore, the action should be "drop" and the result will be:
    {
        "relationship": "MENTOR",
        "properties": {},
        "action": "drop",
    }

    You have the following relationships:
    New relationship:
    {
        "from_node": Node1Title,
        "to_node": Node1Title,
        "new_relationship": "COLLEAGUE"
        "properties": {}
    }
    Existing relationships:
    [
        {
            "from_node": Node1Title,
            "to_node": Node1Title,
            "relationship": "FRIEND"
            "properties": {}
        }
    ]
    In this case, the new relationship "COLLEAGUE" is unique and does not overlap with "FRIEND". Therefore, the action should be "create" and the result will be:
    {
        "relationship": "COLLEAGUE",
        "properties": {},
        "action": "create"
    }

    You have the following relationships:
    New relationship:
    {
        "from_node": Node1Title,
        "to_node": Node1Title,
        "new_relationship": "VISITED"
        "properties": {}
    }
    Existing relationships:
    [   
        {
            "from_node": Node1Title,
            "to_node": Node1Title,
            "relationship": "WAS_IN"
            "properties": {}
        }
    ]
    In this case, the new relationship "VISITED" is more accurate than "WAS_IN" since it implies a more specific interaction. Therefore, the action should be "replace" and the result will be:
    {
        "from_node": "SourceNodeTitle",
        "to_node": "TargetNodeTitle",
        "relationship": "VISITED",
        "properties": {},
        "action": "replace",
        "target_relationship": "WAS_IN"
    }

    You have the following relationships:
    New relationship:
    {
        "from_node": Node1Title,
        "to_node": Node1Title,
        "new_relationship": "EMPLOYEE"
        "properties": {}
    }
    Existing relationships:
    [
        {
            "from_node": Node1Title,
            "to_node": Node1Title,
            "relationship": "EMPLOYEE", 
            properties: {"since": "2020"}
        }
    ]
    In this case, the new relationship "EMPLOYEE" doesn't provide any additional value compared to the existing one which already has a property "since". Therefore, the action should be "drop" and the result will be:
    {
        "from_node": "SourceNodeTitle",
        "to_node": "TargetNodeTitle",
        "relationship": "EMPLOYEE",
        "properties": {},
        "action": "drop"
    }

    You have the following relationships:
    New relationship:
    {
        "from_node": Node1Title,
        "to_node": Node1Title,
        "new_relationship": "FRIEND"
        "properties": {}
    }
    Existing relationships:
    [
        {
            "from_node": Node1Title,
            "to_node": Node1Title,
            "relationship": "ENEMY"
            "properties": {}
        }
    ]
    In this case, the new relationship "FRIEND" is conradictory to the existing relationship "ENEMY". In such situation to avoid confusion, add the new relationship as a property to the existing relationship. Therefore, the action should be "merge" and the result will be:
    {
        "from_node": "SourceNodeTitle",
        "to_node": "TargetNodeTitle",
        "relationship": "ENEMY",
        "properties": {"has_contradiction": "FRIEND"},
        "action": "merge",
        "target_relationship": "ENEMY"
    
    **Information Oversaturation**
    You have the following relationships:
    New relationship:
    {
        "from_node": "Alice",
        "to_node": "Bob",
        "new_relationship": "FATHER"
    }
    Existing relationships:
    [
        {
            "from_node": "Bob",
            "to_node": "Alice",
            "relationship": "DAUGHTER"
        }
    ]
    In this case, the new relationship "FATHER" is similar to the existing relationship "DAUGHTER", but it has the opposite direction. To avoid informational oversaturation, you should keep only the existing relationship "DAUGHTER". Therefore, the action should be "drop" and the result will be:
    {
        "from_node": "Bob",
        "to_node": "Alice",
        "relationship": "DAUGHTER",
        "properties": {},
        "action": "drop"
    }

    You have the following relationships:
    New relationship:
    {
        "from_node": "Elfeen Tower",
        "to_node": "Paris",
        "new_relationship": "LOCATED_IN",
        "properties": {"since": "1887"}
    }
    Existing relationships:
    [
        {
            "from_node": "Paris",
            "to_node": "Elfeen Tower",
            "relationship": "CONSISTS"
        }
    ]
    In this case, the new relationship "LOCATED_IN" is similar to the existing relationship "CONSISTS" and it has the opposite direction. But new relationship "LOCATED_IN" has a useful property "since" that should be preserved. Therefore, the action should be "merge" and the result will be:
    {
        "from_node": "Paris",
        "to_node": "Elfeen Tower", 
        "relationship": "CONSISTS",
        "properties": {"since": "1887"},
        "action": "merge",
        "target_relationship": "CONSISTS"
    }

3. **Return final JSON**
    * The final response must be a JSON array of relationships in the following format:
    
    ```json
    [
         {
              "from_node": "SourceNodeTitle",
              "to_node": "TargetNodeTitle",
              "relationship": "RELATIONSHIP_TYPE",
              "properties": {},
              "action": "create"
         },
         {
              "from_node": "SourceNodeTitle",
              "to_node": "TargetNodeTitle",
              "relationship": "RELATIONSHIP_TYPE",
              "properties": {"property1": "value1"},
              "action": "merge",
              "target_relationship": "EXISTING_RELATIONSHIP_TYPE"
         },
         ...
    ]
    ```
    
    * Output only JSON, no explanations."""
euristic_agent_node_relation_extraction_task_prompt = """Nodes:
{nodes}
Document content:
{content}
Existing relationships:
{existing_relationships}"""