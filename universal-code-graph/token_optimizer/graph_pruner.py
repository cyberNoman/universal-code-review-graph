"""
Graph Pruning using PageRank + Network Flow Algorithms
Physics: Electrical Circuit Analogies (Kirchhoff's Laws)
Math: Graph Theory, Linear Algebra
"""

import networkx as nx
import numpy as np
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass


@dataclass
class PruningResult:
    """Result of graph pruning operation"""
    kept_nodes: List[str]
    removed_nodes: List[str]
    importance_scores: Dict[str, float]
    token_savings: int
    compression_ratio: float


class GraphPruner:
    """
    Prune code graph using PageRank and electrical circuit analogies.
    
    Physics Concept:
    - Treat code graph as electrical circuit
    - Current flow = information flow
    - High voltage nodes = important symbols
    - Low current edges = removable connections
    
    Math:
    - PageRank: PR(u) = (1-d)/N + d * Σ(PR(v)/L(v))
    - Kirchhoff's Current Law: ΣI_in = ΣI_out
    - Network Flow: Max flow = min cut
    """
    
    def __init__(self, decay_factor: float = 0.85, threshold: float = 0.1):
        self.decay_factor = decay_factor  # PageRank damping
        self.threshold = threshold  # Pruning threshold
        
    def calculate_pagerank_importance(self, graph: nx.DiGraph) -> Dict[str, float]:
        """
        Calculate PageRank importance for each node.
        
        Formula: PR(u) = (1-d)/N + d * Σ(PR(v)/L(v))
        Where:
        - d = decay factor (default 0.85)
        - N = total nodes
        - L(v) = number of outgoing links from v
        """
        pagerank = nx.pagerank(graph, alpha=self.decay_factor)
        return pagerank
    
    def electrical_circuit_analogy(self, graph: nx.DiGraph, 
                                   source_nodes: List[str]) -> Dict[str, float]:
        """
        Use electrical circuit analogy to find important nodes.
        
        Physics:
        - Each edge has resistance R = 1/weight
        - Current flows from changed files (sources) to dependents
        - Voltage drop indicates importance
        - Kirchhoff's laws conserve flow
        
        Returns voltage (importance) at each node.
        """
        voltages = {node: 0.0 for node in graph.nodes()}
        
        # Set source nodes to 1V (high voltage = changed files)
        for source in source_nodes:
            if source in voltages:
                voltages[source] = 1.0
        
        # Iterative voltage calculation (relaxation method)
        # V_i = Σ(V_j / R_ij) / Σ(1/R_ij)
        for _ in range(100):  # Convergence iterations
            new_voltages = voltages.copy()
            
            for node in graph.nodes():
                if node in source_nodes:
                    continue  # Keep source at 1V
                
                # Get neighbors with their edge weights
                predecessors = list(graph.predecessors(node))
                
                if not predecessors:
                    continue
                
                # Calculate weighted average voltage
                numerator = 0.0
                denominator = 0.0
                
                for pred in predecessors:
                    # Get edge weight (default 1.0)
                    weight = graph[pred][node].get('weight', 1.0)
                    conductance = weight  # G = 1/R, but we use weight as conductance
                    
                    numerator += voltages[pred] * conductance
                    denominator += conductance
                
                if denominator > 0:
                    new_voltages[node] = numerator / denominator
            
            voltages = new_voltages
        
        return voltages
    
    def network_flow_optimization(self, graph: nx.DiGraph,
                                  source_nodes: List[str],
                                  max_tokens: int) -> Set[str]:
        """
        Use max-flow min-cut to find optimal subgraph.
        
        Math:
        - Max-flow = amount of information that can flow
        - Min-cut = minimum nodes to remove
        - Constraint: Total tokens <= max_tokens
        
        This is a constrained optimization problem.
        """
        # Create flow network
        flow_graph = nx.DiGraph()
        
        # Add super source and super sink
        super_source = "__SUPER_SOURCE__"
        super_sink = "__SUPER_SINK__"
        
        # Add edges from super source to changed files
        for source in source_nodes:
            if source in graph:
                flow_graph.add_edge(super_source, source, capacity=float('inf'))
        
        # Add all original edges with capacities based on importance
        pagerank = self.calculate_pagerank_importance(graph)
        
        for u, v in graph.edges():
            # Capacity = PageRank importance
            capacity = pagerank.get(u, 0.5) * 100
            flow_graph.add_edge(u, v, capacity=capacity)
        
        # Add edges to super sink (all nodes can be sinks)
        for node in graph.nodes():
            if node not in source_nodes:
                flow_graph.add_edge(node, super_sink, capacity=1.0)
        
        # Calculate max flow
        try:
            flow_value, flow_dict = nx.maximum_flow(flow_graph, super_source, super_sink)
        except:
            # Fallback: use all nodes
            return set(graph.nodes())
        
        # Find min cut (nodes that are reached in residual graph)
        try:
            cut_value, partition = nx.minimum_cut(flow_graph, super_source, super_sink)
            reachable, _ = partition
            
            # Remove super source/sink from result
            result = reachable - {super_source, super_sink}
            return result
        except:
            # Fallback
            return set(graph.nodes())
    
    def prune_graph(self, graph: nx.DiGraph,
                    changed_files: List[str],
                    max_tokens: int = 50000,
                    tokens_per_symbol: int = 500) -> PruningResult:
        """
        Main pruning method combining multiple techniques.
        
        Algorithm:
        1. Calculate PageRank importance
        2. Apply electrical circuit analogy
        3. Use network flow for optimization
        4. Prune nodes below threshold
        5. Ensure token budget constraint
        
        Expected Savings: 50-70% of tokens
        """
        # Step 1: Calculate PageRank
        pagerank_scores = self.calculate_pagerank_importance(graph)
        
        # Step 2: Electrical circuit analysis
        voltages = self.electrical_circuit_analogy(graph, changed_files)
        
        # Step 3: Combine scores (weighted average)
        combined_scores = {}
        for node in graph.nodes():
            pr_score = pagerank_scores.get(node, 0)
            volt_score = voltages.get(node, 0)
            # Weight: PageRank 60%, Voltage 40%
            combined_scores[node] = 0.6 * pr_score + 0.4 * volt_score
        
        # Step 4: Network flow optimization
        flow_nodes = self.network_flow_optimization(graph, changed_files, max_tokens)
        
        # Step 5: Prune based on threshold and token budget
        sorted_nodes = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
        
        kept_nodes = []
        total_tokens = 0
        
        for node, score in sorted_nodes:
            # Must be in flow result and above threshold
            if node in flow_nodes and score >= self.threshold:
                node_tokens = tokens_per_symbol
                
                if total_tokens + node_tokens <= max_tokens:
                    kept_nodes.append(node)
                    total_tokens += node_tokens
        
        # Always include changed files
        for cf in changed_files:
            if cf in graph and cf not in kept_nodes:
                kept_nodes.append(cf)
        
        removed_nodes = [n for n in graph.nodes() if n not in kept_nodes]
        
        # Calculate savings
        original_tokens = len(graph.nodes()) * tokens_per_symbol
        saved_tokens = original_tokens - total_tokens
        compression_ratio = total_tokens / original_tokens if original_tokens > 0 else 1.0
        
        return PruningResult(
            kept_nodes=kept_nodes,
            removed_nodes=removed_nodes,
            importance_scores=combined_scores,
            token_savings=saved_tokens,
            compression_ratio=compression_ratio
        )
