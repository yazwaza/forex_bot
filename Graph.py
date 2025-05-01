# Graph.py
def edge_exists(graph, u, v):
    """Checks if an edge exists between two nodes in the graph."""
    if u not in graph or v not in graph:
        return False
    return v in graph[u] and u in graph[v]
    # For undirected graph, check both directions

def remove_edge(graph, u, v):
    """Removes an edge from the graph."""
    if u in graph and v in graph[u]:
        graph[u].remove(v)
    if v in graph and u in graph[v]:
        graph[v].remove(u)  # For undirected graph
    return graph

def create_graph():
    """Creates an empty graph."""
    return {}

def add_node(graph, node):
    """Adds a node to the graph."""
    if node not in graph:
        graph[node] = []
    return graph

def add_edge(graph, u, v):
    """Adds an edge to the graph."""
    if u not in graph:
        graph[u] = []
    if v not in graph:
        graph[v] = []
    graph[u].append(v)
    graph[v].append(u)  # For undirected graph
    return graph

def remove_node(graph, node):
    """Removes a node from the graph."""
    if node in graph:
        del graph[node]
        for u in graph:
            if node in graph[u]:
                graph[u].remove(node)
    return graph
def get_edges(graph):
    """Returns all edges in the graph."""
    edges = []
    for u in graph:
        for v in graph[u]:
            if (v, u) not in edges:  # Avoid duplicates for undirected graph
                edges.append((u, v))
    return edges
    # Return a list of all edges in the graph
def get_degree(graph, node):
    """Returns the degree of a node."""
    if node in graph:
        return len(graph[node])
    return 0
    # Return the degree of the node

def get_edge(graph, u, v):
    """Returns the edge between two nodes."""
    if u in graph and v in graph[u]:
        return (u, v)
    return None
    # Return the edge if it exists, otherwise return None


def get_neighbors(graph, node):
    """Returns the neighbors of a node."""
    if node in graph:
        return graph[node]
    return []
    # Return empty list if node not found
def get_nodes(graph):
    """Returns all nodes in the graph."""
    return list(graph.keys())
    # Return a list of all nodes in the graph
def graph_size(graph):
    """Returns the number of nodes in the graph."""
    return len(graph)
    # Return the number of nodes in the graph
def graph_edges(graph):
    """Returns the number of edges in the graph."""
    count = 0
    for node in graph:
        count += len(graph[node])
    return count // 2  # For undirected graph, divide by 2
    # Return the number of edges in the graph
def is_connected(graph):
    """Checks if the graph is connected."""
    visited = set()
    def dfs(node):
        visited.add(node)
        for neighbor in graph[node]:
            if neighbor not in visited:
                dfs(neighbor)

    if not graph:
        return True  # An empty graph is considered connected
    start_node = next(iter(graph))
    dfs(start_node)
    return len(visited) == len(graph)
    # Return True if the graph is connected, False otherwise

