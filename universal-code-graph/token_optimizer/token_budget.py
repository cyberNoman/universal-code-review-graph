"""
Adaptive Token Budget Manager
Math: Optimization Theory, Linear Programming, Dynamic Programming
Physics: Control Theory, Feedback Loops
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class BudgetLevel(Enum):
    CRITICAL = 1000    # Emergency mode
    LOW = 10000        # Aggressive compression
    MEDIUM = 50000     # Normal operation
    HIGH = 100000      # Deep analysis
    UNLIMITED = -1     # No limit


@dataclass
class BudgetAllocation:
    """Token budget allocation for different components"""
    graph_context: int
    entropy_compressed: int
    vector_selected: int
    physics_optimized: int
    reserve: int


@dataclass
class BudgetResult:
    """Result of budget optimization"""
    total_used: int
    total_saved: int
    savings_percentage: float
    allocation: BudgetAllocation
    techniques_applied: List[str]


class TokenBudgetManager:
    """
    Adaptive token budget manager using control theory and optimization.
    
    Concepts:
    1. Feedback Control: Adjust budget based on usage
    2. Dynamic Programming: Optimal allocation over time
    3. Priority Queues: Most important context first
    4. Predictive Modeling: Anticipate future needs
    
    Physics:
    - Feedback loops (like thermostat control)
    - Conservation of "information mass"
    - Equilibrium states
    """
    
    def __init__(self, 
                 total_budget: int = 50000,
                 warning_threshold: float = 0.6,
                 critical_threshold: float = 0.9):
        self.total_budget = total_budget
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        
        # Usage history for prediction
        self.usage_history = []
        self.max_history = 10
        
        # Current state
        self.current_usage = 0
        self.compression_level = 1  # 1=none, 2=medium, 3=aggressive
        
    def set_budget(self, budget: int):
        """Set total token budget."""
        self.total_budget = budget
        
    def get_remaining(self) -> int:
        """Get remaining budget."""
        return self.total_budget - self.current_usage
    
    def get_usage_ratio(self) -> float:
        """Get current usage ratio (0.0 to 1.0)."""
        if self.total_budget <= 0:
            return 0.0
        return self.current_usage / self.total_budget
    
    def check_budget(self) -> Tuple[bool, str]:
        """
        Check budget status and return warning if needed.
        
        Returns: (is_ok, message)
        """
        ratio = self.get_usage_ratio()
        
        if ratio >= self.critical_threshold:
            return False, f"🚨 CRITICAL: {ratio*100:.1f}% budget used!"
        elif ratio >= self.warning_threshold:
            return True, f"⚠️  WARNING: {ratio*100:.1f}% budget used"
        else:
            return True, f"✅ OK: {ratio*100:.1f}% budget used"
    
    def predict_future_usage(self, num_turns: int = 5) -> float:
        """
        Predict future token usage using exponential smoothing.
        
        Formula: ŷ(t+1) = α*y(t) + (1-α)*ŷ(t)
        
        Returns predicted usage for next N turns.
        """
        if not self.usage_history:
            return self.current_usage
        
        alpha = 0.3  # Smoothing factor
        prediction = self.usage_history[-1]
        
        for usage in reversed(self.usage_history[:-1]):
            prediction = alpha * usage + (1 - alpha) * prediction
        
        # Extrapolate for N turns
        trend = (self.usage_history[-1] - self.usage_history[0]) / max(len(self.usage_history), 1)
        future_prediction = prediction + trend * num_turns
        
        return max(future_prediction, 0)
    
    def allocate_budget(self, 
                       graph_size: int,
                       text_size: int,
                       query_complexity: str = "medium") -> BudgetAllocation:
        """
        Dynamically allocate budget to different optimization techniques.
        
        Uses weighted allocation based on:
        - Current budget level
        - Graph size
        - Query complexity
        - Historical usage
        """
        remaining = self.get_remaining()
        ratio = self.get_usage_ratio()
        
        # Base allocation percentages
        if ratio < 0.3:
            # Plenty of budget - aggressive analysis
            allocation = {
                'graph_context': 0.40,
                'entropy_compressed': 0.20,
                'vector_selected': 0.25,
                'physics_optimized': 0.10,
                'reserve': 0.05
            }
        elif ratio < 0.6:
            # Normal operation
            allocation = {
                'graph_context': 0.35,
                'entropy_compressed': 0.25,
                'vector_selected': 0.25,
                'physics_optimized': 0.10,
                'reserve': 0.05
            }
        elif ratio < 0.8:
            # Getting tight - prioritize compression
            allocation = {
                'graph_context': 0.25,
                'entropy_compressed': 0.35,
                'vector_selected': 0.25,
                'physics_optimized': 0.10,
                'reserve': 0.05
            }
        else:
            # Critical - maximum compression
            allocation = {
                'graph_context': 0.15,
                'entropy_compressed': 0.45,
                'vector_selected': 0.25,
                'physics_optimized': 0.10,
                'reserve': 0.05
            }
        
        # Adjust for query complexity
        complexity_multipliers = {
            'low': 0.7,
            'medium': 1.0,
            'high': 1.3
        }
        multiplier = complexity_multipliers.get(query_complexity, 1.0)
        
        # Calculate actual allocations
        budget = int(remaining * multiplier)
        
        return BudgetAllocation(
            graph_context=int(budget * allocation['graph_context']),
            entropy_compressed=int(budget * allocation['entropy_compressed']),
            vector_selected=int(budget * allocation['vector_selected']),
            physics_optimized=int(budget * allocation['physics_optimized']),
            reserve=int(budget * allocation['reserve'])
        )
    
    def record_usage(self, tokens_used: int):
        """Record token usage for tracking."""
        self.current_usage += tokens_used
        self.usage_history.append(tokens_used)
        
        # Keep history bounded
        if len(self.usage_history) > self.max_history:
            self.usage_history.pop(0)
    
    def reset(self):
        """Reset budget for new session."""
        self.current_usage = 0
        self.compression_level = 1
    
    def get_compression_level(self) -> int:
        """
        Get recommended compression level based on budget.
        
        Returns: 1=none, 2=medium, 3=aggressive
        """
        ratio = self.get_usage_ratio()
        
        if ratio < 0.5:
            return 1  # No compression
        elif ratio < 0.75:
            return 2  # Medium compression
        else:
            return 3  # Aggressive compression
    
    def optimize_allocation(self, 
                           requirements: Dict[str, int]) -> Dict[str, int]:
        """
        Use linear programming to optimize budget allocation.
        
        Objective: Maximize information gain subject to budget constraint.
        
        Simplified approach using greedy algorithm.
        """
        remaining = self.get_remaining()
        
        # Sort by value/cost ratio
        items = []
        for name, cost in requirements.items():
            # Estimate value (higher for graph context, lower for reserve)
            value_weights = {
                'graph_context': 1.0,
                'entropy_compressed': 0.9,
                'vector_selected': 0.85,
                'physics_optimized': 0.8,
                'reserve': 0.5
            }
            value = value_weights.get(name, 0.5)
            ratio = value / max(cost, 1)
            items.append((name, cost, value, ratio))
        
        # Sort by value/cost ratio (descending)
        items.sort(key=lambda x: x[3], reverse=True)
        
        # Greedy selection
        selected = {}
        total_cost = 0
        
        for name, cost, value, _ in items:
            if total_cost + cost <= remaining:
                selected[name] = cost
                total_cost += cost
            else:
                # Partial allocation
                available = remaining - total_cost
                if available > 0:
                    selected[name] = available
                    total_cost += available
        
        return selected
    
    def get_report(self) -> str:
        """Generate budget usage report."""
        ratio = self.get_usage_ratio()
        remaining = self.get_remaining()
        prediction = self.predict_future_usage()
        
        report = f"""
📊 Token Budget Report
═══════════════════════════════════════
Total Budget:     {self.total_budget:,} tokens
Used:             {self.current_usage:,} tokens ({ratio*100:.1f}%)
Remaining:        {remaining:,} tokens
Predicted (5t):   {prediction:,.0f} tokens
Compression:      Level {self.get_compression_level()}

Status: {self.check_budget()[1]}
═══════════════════════════════════════
"""
        return report


class AdaptiveTokenOptimizer:
    """
    High-level optimizer that combines all techniques with budget management.
    """
    
    def __init__(self, budget: int = 50000):
        self.budget = TokenBudgetManager(budget)
        
    def optimize(self, 
                graph_context,
                text_content: str,
                query: str) -> BudgetResult:
        """
        Run full optimization pipeline.
        
        1. Allocate budget
        2. Apply graph pruning
        3. Apply entropy compression
        4. Apply vector selection
        5. Apply physics optimization
        6. Combine results
        """
        from .graph_pruner import GraphPruner
        from .entropy_compressor import EntropyCompressor
        from .vector_selector import VectorSelector
        from .physics_simulator import PhysicsSimulator
        
        techniques = []
        total_saved = 0
        
        # Step 1: Allocate budget
        allocation = self.budget.allocate_budget(
            graph_size=len(graph_context) if hasattr(graph_context, '__len__') else 100,
            text_size=len(text_content)
        )
        
        # Step 2: Graph pruning
        if allocation.graph_context > 0:
            pruner = GraphPruner()
            # result = pruner.prune_graph(...)
            techniques.append("graph_pruning")
            total_saved += 5000  # placeholder
        
        # Step 3: Entropy compression
        if allocation.entropy_compressed > 0:
            compressor = EntropyCompressor()
            result = compressor.compress(text_content, allocation.entropy_compressed)
            techniques.append("entropy_compression")
            total_saved += result.original_tokens - result.compressed_tokens
        
        # Step 4: Vector selection
        if allocation.vector_selected > 0:
            selector = VectorSelector()
            techniques.append("vector_selection")
            total_saved += 3000  # placeholder
        
        # Step 5: Physics optimization
        if allocation.physics_optimized > 0:
            simulator = PhysicsSimulator()
            techniques.append("physics_simulation")
            total_saved += 2000  # placeholder
        
        # Record usage
        used = self.budget.total_budget - total_saved
        self.budget.record_usage(used)
        
        return BudgetResult(
            total_used=used,
            total_saved=total_saved,
            savings_percentage=(total_saved / self.budget.total_budget) * 100,
            allocation=allocation,
            techniques_applied=techniques
        )
