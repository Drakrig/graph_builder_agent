# Graph Building Agent
## Nodes

Each node has a clone in vector database, so based on its description it's possible to find similar ones. The newlt created nodes goes to a separate tenant in the vector database, because they are not yet verified and might contain mistakes.

## The process

1. Use LLM to extract all possible nodes, their descriptions and types from the text. It also determine if one of the nodes represent the main topic/node.
2. For each extracted node:
    1) Determine if node with the same title exists
        - if exist - extract this node from database and add as relavant information.
        - search vecrtor database for relevant chunks.
    2) Use provided node node/chunks to:
        - if node exist - exnrich description
        - if node doesn't exists - use provided pieces of information to create new node and fix possible extrction mistakes.
    3) Update graph database
        - if node exist - update description and other properties
        - if node doesn't exists - create new node and create a new record in vector database.
3. Create a pairs of extracted node and check if any relationships between them exist.
4. Find existing relationships between node pairs.
5. Pass extracted nodes to LLM with existing relationships and the document content as context to:
    - find possible relationships between nodes
    - if relationship exist - decide if newly extracted relationship should:
        - be added as new relationship
        - replace existing relationship
        - enrich existing relationship
        - be discarded
    - if relationship doesn't exist - create a new relationship 
    * During this step, it's important to avoid information oversaturation. As example, if node_1-[:FRIEND]->node_2 already exist, and newly extracted relationship is node_2-[:FRIEND]->node_1, then it's better to discard it since the search process in the graph database allows to find the 1st relationship with (n1)-[r]-(n2) query.

### Why not to process all nodes at once?

Context window size. If we have too many nodes, we may exceed the context window size of the LLM. Also, as context window size increase, the ability of the LLM to reason about the information decrease and it might, for example, 'forget' to include one of the nodes in the final response or mess up description, type or title. So it's better to process nodes one by one, using as small context as possible. Even so it probably is less computationally efficient, but it will provide better results.

### Why not to process pair of nodes separately?

The relationship context is much smaller compare to node one, so it's possible to process all relationships at once. Also, processing relationships one by one will require much more calls to LLM (n*(n-1)/2 instead of 1), which will be much more computationally expensive. Still, the risk of LLM loosing the context exists, expecially if there are too many nodes or on later stages of the process when the graph already contains many nodes and relationships and some of them might be relevant to the newly extracted ones. It need to be considered.

#### Pair-wise processing of relationships

1. Take a pair of nodes
2. Find existing relationships between them
3. Find relevant chunks for each node
4. Based on provided context (document+chunks) determine if any relationship exist between them:
    - if exist:
        - based on provided existing relationships decide if newly extracted relationship should:
            - be added as new relationship
            - replace existing relationship
            - enrich existing relationship
            - be discarded
    - if doesn't exist - process next pair.

The process is very computationally expensive, but it might provide better results in some cases. The parallel processing of pairs is possible, but the memory consumption will skyrocket.