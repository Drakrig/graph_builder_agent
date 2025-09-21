# Graph Building Agent
## Motivation
Graph database building is a complecated process that can becharacterized as:

1. Multi-step
2. Repetative
3. Require reasoning
4. Require verification

### Multistepping

The process of creating knowledge graph from textual description will be file based

## Process

The process of creating knowledge graph from textual description will be file based. Each file represent a single node in the future graph.

For each file:

1. Determine if file actually represent a node:
    - there are some files that work more as a cumulative knowledge block, like they are descript a storyline of certain character. Such thing can't be treatead as node, but might be a source of information for creating new nodes.
2. Extract additional node properties (type, label, short description or other useful information).
2. Determine if similar node exists. The way to do so explied in Nodes section.
    - if exist we need to merge new information into existing node and work with it directly 
    - create a new node otherwise
3. Extract other possible nodes from the text (location, events, people etc.) and its propeties
4. Determine if similar nodes are exists (repeat step 2 for them). The way to do so explied in Nodes section.
5. Determine connection and its properties between current node (file based) and newly extracted. All connection is one-way, but it must be considered that reverse connection are possible, for example, family one like from father to son an et versa.
6. Check if connection already exist
    - if exist - update properties if nessesary
    - create new connection and its reversed variation otherwise


For each newly extracted node, check if node already exists in the graph.

If it exists then enrich node properties with additional information based on current text. Otherwise create new node based on avaliable information.

On this stage, each the nodes property should be treatead as array of description

## Nodes

Each node has a clone in vector database, so based on its description it's possible to find similar ones. To enchanve the process, it may be beneficial to track if node exsists with boolean flag or even better - index.