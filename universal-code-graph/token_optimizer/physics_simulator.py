"""
Physics-Based Optimization using Force-Directed Graphs
Physics: Spring-Mass Systems, Energy Minimization, Coulomb's Law
Math: Differential Equations, Gradient Descent, Hamiltonian Mechanics
"""

import numpy as np
import networkx as nx
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class PhysicsResult:
    """Result of physics-based optimization"""
    selected_nodes: List[str]
    positions: Dict[str, np.ndarray]
    energy: float
    token_savings: int


class PhysicsSimulator:
    """
    Use physics simulation to find optimal context selection.
    
    Physics Concepts:
    1. Spring-Mass System: Connected nodes attract (Hooke's Law)
    2. Coulomb Repulsion: All nodes repel (electrostatics)
    3. Gravity: Pulls nodes toward changed files
    4. Energy Minimization: System settles to optimal state
    5. Damping: Friction stops oscillation
    
    Math:
    - Hooke's Law: F = -k * (distance - rest_length)
    - Coulomb's Law: F = k * q1 * q2 / r^2
    - Newton's 2nd Law: F = ma
    - Energy: E = kinetic + potential
    """
    
    def __init__(self, 
                 spring_constant: float = 0.1,
                 repulsion_constant: float = 100.0,
                 gravity_constant: float = 0.5,
                 damping: float = 0.8,
                 time_step: float = 0.1):
        self.spring_constant = spring_constant
        self.repulsion_constant = repulsion_constant
        self.gravity_constant = gravity_constant
        self.damping = damping
        self.time_step = time_step
        
    def initialize_positions(self, graph: nx.DiGraph,
                            source_nodes: List[str],
                            dim: int = 2) -> Dict[str, np.ndarray]:
        """Initialize random positions for all nodes."""
        positions = {}
        for node in graph.nodes():
            if node in source_nodes:
                # Source nodes start at origin
                positions[node] = np.zeros(dim)
            else:
                # Random position in unit square
                positions[node] = np.random.randn(dim) * 10
        return positions
    
    def calculate_spring_forces(self, graph: nx.DiGraph,
                                positions: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """
        Calculate spring forces between connected nodes.
        
        Hooke's Law: F = -k * (current_length - rest_length)
        
        Connected nodes attract each other.
        """
        forces = {node: np.zeros_like(pos) for node, pos in positions.items()}
        
        for u, v in graph.edges():
            if u not in positions or v not in positions:
                continue
            
            pos_u = positions[u]
            pos_v = positions[v]
            
            # Vector from u to v
            delta = pos_v - pos_u
            distance = np.linalg.norm(delta)
            
            if distance > 0:
                # Spring force (Hooke's Law)
                rest_length = 1.0
                force_magnitude = -self.spring_constant * (distance - rest_length)
                force_direction = delta / distance
                force = force_magnitude * force_direction
                
                forces[u] += force
                forces[v] -= force
        
        return forces
    
    def calculate_repulsion_forces(self, graph: nx.DiGraph,
                                   positions: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """
        Calculate Coulomb repulsion forces between all node pairs.
        
        Coulomb's Law: F = k * q1 * q2 / r^2
        
        All nodes repel each other (like charges).
        """
        forces = {node: np.zeros_like(pos) for node, pos in positions.items()}
        nodes = list(positions.keys())
        
        for i, u in enumerate(nodes):
            for v in nodes[i+1:]:
                pos_u = positions[u]
                pos_v = positions[v]
                
                delta = pos_v - pos_u
                distance = np.linalg.norm(delta)
                
                if distance > 0 and distance < 50:  # Cutoff for efficiency
                    # Coulomb repulsion
                    force_magnitude = self.repulsion_constant / (distance ** 2)
                    force_direction = delta / distance
                    force = force_magnitude * force_direction
                    
                    forces[u] -= force
                    forces[v] += force
        
        return forces
    
    def calculate_gravity_forces(self, graph: nx.DiGraph,
                                 positions: Dict[str, np.ndarray],
                                 source_nodes: List[str]) -> Dict[str, np.ndarray]:
        """
        Calculate gravity forces pulling nodes toward source nodes.
        
        F = G * m1 * m2 / r^2
        
        Source nodes (changed files) have high "mass" and pull other nodes.
        """
        forces = {node: np.zeros_like(pos) for node, pos in positions.items()}
        
        # Calculate center of mass of source nodes
        center = np.mean([positions[s] for s in source_nodes if s in positions], axis=0)
        
        for node, pos in positions.items():
            if node in source_nodes:
                continue
            
            delta = center - pos
            distance = np.linalg.norm(delta)
            
            if distance > 0:
                # Gravity force
                force_magnitude = self.gravity_constant / (distance ** 0.5)  # Sqrt for stability
                force_direction = delta / distance
                forces[node] += force_magnitude * force_direction
        
        return forces
    
    def calculate_total_energy(self, graph: nx.DiGraph,
                               positions: Dict[str, np.ndarray],
                               velocities: Dict[str, np.ndarray]) -> float:
        """
        Calculate total energy of the system.
        
        E_total = E_kinetic + E_potential
        
        Used to check convergence.
        """
        # Kinetic energy: E_k = 0.5 * m * v^2
        kinetic = sum(0.5 * np.linalg.norm(v)**2 for v in velocities.values())
        
        # Potential energy (from springs)
        potential = 0.0
        for u, v in graph.edges():
            if u in positions and v in positions:
                distance = np.linalg.norm(positions[v] - positions[u])
                potential += 0.5 * self.spring_constant * (distance - 1.0)**2
        
        return kinetic + potential
    
    def simulate(self, graph: nx.DiGraph,
                 source_nodes: List[str],
                 max_iterations: int = 1000,
                 convergence_threshold: float = 1e-6) -> PhysicsResult:
        """
        Run physics simulation to find optimal layout.
        
        Algorithm:
        1. Initialize random positions
        2. Calculate all forces (spring, repulsion, gravity)
        3. Update velocities and positions
        4. Apply damping
        5. Repeat until convergence
        
        Nodes that end up close to source nodes are more important.
        """
        # Initialize
        positions = self.initialize_positions(graph, source_nodes)
        velocities = {node: np.zeros_like(pos) for node, pos in positions.items()}
        
        prev_energy = float('inf')
        
        for iteration in range(max_iterations):
            # Calculate forces
            spring_forces = self.calculate_spring_forces(graph, positions)
            repulsion_forces = self.calculate_repulsion_forces(graph, positions)
            gravity_forces = self.calculate_gravity_forces(graph, positions, source_nodes)
            
            # Total force
            total_forces = {}
            for node in positions:
                total_forces[node] = (spring_forces.get(node, 0) + 
                                     repulsion_forces.get(node, 0) + 
                                     gravity_forces.get(node, 0))
            
            # Update velocities and positions (Euler integration)
            for node in positions:
                # F = ma, so a = F/m (assume m=1)
                acceleration = total_forces[node]
                
                # Update velocity: v = v + a * dt
                velocities[node] += acceleration * self.time_step
                
                # Apply damping
                velocities[node] *= self.damping
                
                # Update position: x = x + v * dt
                positions[node] += velocities[node] * self.time_step
            
            # Check convergence
            energy = self.calculate_total_energy(graph, positions, velocities)
            energy_change = abs(prev_energy - energy)
            
            if energy_change < convergence_threshold:
                break
            
            prev_energy = energy
        
        # Select nodes based on distance to source
        source_center = np.mean([positions[s] for s in source_nodes if s in positions], axis=0)
        
        distances = {}
        for node, pos in positions.items():
            distances[node] = np.linalg.norm(pos - source_center)
        
        # Sort by distance (closer = more important)
        sorted_nodes = sorted(distances.items(), key=lambda x: x[1])
        
        # Select closest 60% of nodes
        num_to_select = int(len(sorted_nodes) * 0.6)
        selected = [node for node, _ in sorted_nodes[:num_to_select]]
        
        # Calculate savings
        original = len(graph.nodes()) * 500
        saved = original - len(selected) * 500
        
        return PhysicsResult(
            selected_nodes=selected,
            positions=positions,
            energy=energy,
            token_savings=saved
        )
    
    def force_directed_layout(self, graph: nx.DiGraph,
                              source_nodes: List[str]) -> Dict[str, np.ndarray]:
        """
        Compute force-directed layout.
        
        Wrapper for NetworkX's spring layout with custom parameters.
        """
        # Use networkx's implementation (faster)
        pos = nx.spring_layout(
            graph,
            k=1.0,  # Optimal distance
            iterations=100,
            seed=42
        )
        
        # Shift so source nodes are at origin
        center = np.mean([pos[s] for s in source_nodes if s in pos], axis=0)
        for node in pos:
            pos[node] -= center
        
        return pos
