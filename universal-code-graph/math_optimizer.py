"""
Advanced Mathematical Token Optimization Techniques

Applies physics-inspired and information theory techniques to minimize token usage:
1. Shannon Entropy-based symbol filtering
2. Spectral Graph Theory (eigenvector centrality)
3. Thermodynamic Free Energy minimization
4. Fractal Dimension analysis
5. Wave Function Collapse for symbol merging
6. Renormalization Group Flow for multi-scale abstraction
"""

import math
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Optional, Any
import json
import hashlib


@dataclass
class SymbolImportance:
    """Scored symbol with multiple mathematical metrics."""
    symbol_key: str
    shannon_entropy: float  # Information content
    spectral_score: float   # Eigenvector centrality
    free_energy: float      # Thermodynamic cost
    fractal_dimension: float  # Complexity measure
    composite_score: float  # Weighted combination
    file_tokens: int
    estimated_tokens: int


class EntropyOptimizer:
    """
    Shannon entropy-based symbol filtering.
    
    Measures information content of symbols based on:
    - Frequency distribution across files
    - Symbol type distribution
    - Call graph connectivity
    """
    
    @staticmethod
    def calculate_symbol_entropy(symbols: List[Dict], edges: List[Dict]) -> Dict[str, float]:
        """
        Calculate Shannon entropy for each symbol.
        
        H(X) = -Σ p(x) log₂ p(x)
        
        Lower entropy = more predictable = less informative
        Higher entropy = more surprising = more informative
        """
        if not symbols:
            return {}
        
        # Calculate probability distributions
        file_dist = Counter(s['file_path'] for s in symbols)
        type_dist = Counter(s['symbol_type'] for s in symbols)
        
        total_symbols = len(symbols)
        
        # Build adjacency for connectivity
        call_counts = Counter()
        for edge in edges:
            call_counts[edge['caller']] += 1
            call_counts[edge['callee']] += 1
        
        entropies = {}
        for symbol in symbols:
            key = symbol.get('key', symbol.get('symbol_key', ''))
            
            # File entropy: how common is this symbol's file?
            p_file = file_dist.get(symbol.get('file_path', ''), 1) / total_symbols
            h_file = -p_file * math.log2(p_file) if p_file > 0 else 0
            
            # Type entropy: how common is this symbol type?
            p_type = type_dist.get(symbol.get('symbol_type', ''), 1) / total_symbols
            h_type = -p_type * math.log2(p_type) if p_type > 0 else 0
            
            # Connectivity entropy: how many calls involve this symbol?
            connectivity = call_counts.get(key, 0)
            p_conn = min(connectivity / total_symbols, 1.0)
            h_conn = -p_conn * math.log2(p_conn) if p_conn > 0 else 0
            
            # Weighted combination
            entropies[key] = 0.4 * h_file + 0.3 * h_type + 0.3 * h_conn
        
        return entropies
    
    @staticmethod
    def filter_by_entropy_threshold(
        symbols: List[Dict],
        entropies: Dict[str, float],
        threshold: float = 0.5,
        top_k: Optional[int] = None
    ) -> List[Dict]:
        """
        Filter symbols by entropy threshold.
        
        Keeps symbols with information content above threshold.
        Optionally keeps only top-k highest entropy symbols.
        """
        scored = []
        for symbol in symbols:
            key = symbol.get('key', symbol.get('symbol_key', ''))
            entropy = entropies.get(key, 0)
            if entropy >= threshold:
                scored.append((entropy, symbol))
        
        # Sort by entropy descending
        scored.sort(key=lambda x: x[0], reverse=True)
        
        if top_k:
            scored = scored[:top_k]
        
        return [s for _, s in scored]


class SpectralGraphOptimizer:
    """
    Spectral Graph Theory-based symbol prioritization.
    
    Uses eigenvector centrality from adjacency matrix to identify
    most important symbols in the call graph.
    
    Based on: A = λx where A is adjacency matrix, λ is eigenvalue,
    x is eigenvector (centrality scores)
    """
    
    @staticmethod
    def build_adjacency_matrix(symbols: List[Dict], edges: List[Dict]) -> Tuple[sparse.csr_matrix, Dict[int, str]]:
        """Build sparse adjacency matrix from symbol graph."""
        symbol_to_idx = {s.get('key', s.get('symbol_key', '')): i 
                        for i, s in enumerate(symbols)}
        idx_to_symbol = {i: s.get('key', s.get('symbol_key', '')) 
                        for i, s in enumerate(symbols)}
        
        n = len(symbols)
        rows, cols, vals = [], [], []
        
        for edge in edges:
            caller = edge.get('caller', '')
            callee = edge.get('callee', '')
            if caller in symbol_to_idx and callee in symbol_to_idx:
                i, j = symbol_to_idx[caller], symbol_to_idx[callee]
                rows.append(i)
                cols.append(j)
                vals.append(1.0)
        
        adj_matrix = sparse.csr_matrix(
            (vals, (rows, cols)),
            shape=(n, n),
            dtype=np.float64
        )
        
        return adj_matrix, idx_to_symbol
    
    @staticmethod
    def compute_eigenvector_centrality(
        symbols: List[Dict],
        edges: List[Dict],
        top_k: int = 50
    ) -> Dict[str, float]:
        """
        Compute eigenvector centrality for all symbols.
        
        Higher centrality = more influential symbol = higher priority
        Uses power iteration method for large graphs.
        """
        if len(symbols) < 2:
            return {s.get('key', s.get('symbol_key', '')): 1.0 for s in symbols}
        
        adj_matrix, idx_to_symbol = SpectralGraphOptimizer.build_adjacency_matrix(symbols, edges)
        
        try:
            # Compute dominant eigenvector using ARPACK
            eigenvalues, eigenvectors = eigsh(
                adj_matrix.astype(np.float64),
                k=1,  # Top eigenvalue
                which='LM',  # Largest magnitude
                maxiter=1000
            )
            
            centrality = {}
            eigenvector = np.abs(eigenvectors[:, 0])
            
            # Normalize to [0, 1]
            if eigenvector.max() > 0:
                eigenvector = eigenvector / eigenvector.max()
            
            for idx, score in enumerate(eigenvector):
                symbol_key = idx_to_symbol.get(idx, '')
                centrality[symbol_key] = float(score)
            
            return centrality
        
        except Exception:
            # Fallback: use degree centrality
            degree_centrality = {}
            for symbol in symbols:
                key = symbol.get('key', symbol.get('symbol_key', ''))
                degree = sum(1 for e in edges if e.get('caller') == key or e.get('callee') == key)
                degree_centrality[key] = degree / max(len(symbols), 1)
            return degree_centrality
    
    @staticmethod
    def spectral_filtering(
        symbols: List[Dict],
        edges: List[Dict],
        centrality_threshold: float = 0.3,
        top_k: Optional[int] = None
    ) -> List[Dict]:
        """Filter symbols by spectral centrality."""
        centralities = SpectralGraphOptimizer.compute_eigenvector_centrality(
            symbols, edges, top_k or len(symbols)
        )
        
        filtered = []
        for symbol in symbols:
            key = symbol.get('key', symbol.get('symbol_key', ''))
            score = centralities.get(key, 0)
            if score >= centrality_threshold:
                filtered.append((score, symbol))
        
        filtered.sort(key=lambda x: x[0], reverse=True)
        
        if top_k:
            filtered = filtered[:top_k]
        
        return [s for _, s in filtered]


class ThermodynamicOptimizer:
    """
    Thermodynamic Free Energy Minimization.
    
    Models symbol graph as physical system where:
    - Energy (E) = code complexity (cyclomatic, nesting depth)
    - Entropy (S) = symbol connectivity diversity
    - Free Energy (F) = E - T*S
    
    System naturally minimizes F, keeping only symbols that
    provide informational value greater than their complexity cost.
    """
    
    @dataclass
    class ThermodynamicState:
        energy: float
        entropy: float
        temperature: float
        free_energy: float
    
    @staticmethod
    def calculate_symbol_energy(symbol: Dict, edges: List[Dict]) -> float:
        """
        Calculate energy (complexity cost) of a symbol.
        
        E = cyclomatic_complexity * nesting_depth * log(connections)
        """
        # Estimate complexity from symbol properties
        complexity = symbol.get('cyclomatic_complexity', 1)
        nesting = symbol.get('nesting_depth', 1)
        
        # Count connections
        connections = sum(1 for e in edges 
                         if e.get('caller') == symbol.get('key', '') 
                         or e.get('callee') == symbol.get('key', ''))
        
        energy = complexity * nesting * math.log(1 + connections)
        return energy
    
    @staticmethod
    def calculate_system_entropy(symbols: List[Dict], edges: List[Dict]) -> float:
        """
        Calculate configurational entropy of the symbol system.
        
        S = k_B * ln(Ω) where Ω is number of microstates
        Approximated by edge distribution entropy
        """
        if not edges:
            return 0.0
        
        # Edge type distribution
        edge_types = Counter(e.get('call_type', 'unknown') for e in edges)
        total_edges = len(edges)
        
        entropy = 0.0
        for count in edge_types.values():
            p = count / total_edges
            if p > 0:
                entropy -= p * math.log(p)
        
        return entropy
    
    @staticmethod
    def compute_free_energies(
        symbols: List[Dict],
        edges: List[Dict],
        temperature: float = 1.0
    ) -> Dict[str, float]:
        """
        Compute free energy for each symbol.
        
        F_i = E_i - T * S_i
        
        Lower free energy = more stable = keep this symbol
        """
        system_entropy = ThermodynamicOptimizer.calculate_system_entropy(symbols, edges)
        free_energies = {}
        
        for symbol in symbols:
            key = symbol.get('key', symbol.get('symbol_key', ''))
            energy = ThermodynamicOptimizer.calculate_symbol_energy(symbol, edges)
            
            # Symbol's contribution to system entropy
            connections = sum(1 for e in edges 
                            if e.get('caller') == key or e.get('callee') == key)
            symbol_entropy = system_entropy * (connections / max(len(edges), 1))
            
            free_energy = energy - temperature * symbol_entropy
            free_energies[key] = free_energy
        
        return free_energies
    
    @staticmethod
    def thermodynamic_pruning(
        symbols: List[Dict],
        edges: List[Dict],
        temperature: float = 1.0,
        energy_threshold: float = 0.7,
        top_k: Optional[int] = None
    ) -> List[Dict]:
        """
        Prune symbols with high free energy (unstable, costly).
        
        Keeps symbols with low free energy (stable, valuable).
        """
        free_energies = ThermodynamicOptimizer.compute_free_energies(
            symbols, edges, temperature
        )
        
        if not free_energies:
            return symbols
        
        # Normalize to [0, 1]
        min_f = min(free_energies.values())
        max_f = max(free_energies.values())
        range_f = max_f - min_f if max_f != min_f else 1.0
        
        normalized = {}
        for key, energy in free_energies.items():
            normalized[key] = (energy - min_f) / range_f
        
        # Filter by threshold (keep low energy symbols)
        filtered = []
        for symbol in symbols:
            key = symbol.get('key', symbol.get('symbol_key', ''))
            score = normalized.get(key, 1.0)
            if score <= energy_threshold:
                filtered.append((score, symbol))
        
        filtered.sort(key=lambda x: x[0])
        
        if top_k:
            filtered = filtered[:top_k]
        
        return [s for _, s in filtered]


class FractalDimensionOptimizer:
    """
    Fractal Dimension Analysis for Code Complexity.
    
    Uses box-counting method to estimate fractal dimension of symbol distribution.
    Higher fractal dimension = more complex/self-similar = higher token cost.
    
    D = lim(ε→0) [log N(ε) / log(1/ε)]
    
    Where N(ε) is number of boxes of size ε needed to cover the set.
    """
    
    @staticmethod
    def compute_box_counting_dimension(
        symbols: List[Dict],
        num_scales: int = 5
    ) -> float:
        """
        Estimate fractal dimension using box-counting method.
        
        Symbols are mapped to 2D space (line_number, file_index)
        and dimension is computed from scaling behavior.
        """
        if not symbols:
            return 0.0
        
        # Map symbols to 2D points
        files = list(set(s.get('file_path', '') for s in symbols))
        file_to_idx = {f: i for i, f in enumerate(files)}
        
        points = []
        for s in symbols:
            x = file_to_idx.get(s.get('file_path', ''), 0)
            y = s.get('line_start', 0)
            points.append((x, y))
        
        if not points:
            return 0.0
        
        # Box counting at multiple scales
        scales = np.logspace(0, np.log10(max(max(p) for p in points) + 1), num_scales)
        log_scales = []
        log_counts = []
        
        for scale in scales:
            if scale <= 0:
                continue
            
            # Count boxes needed
            boxes = set()
            for x, y in points:
                box_x = int(x / scale)
                box_y = int(y / scale)
                boxes.add((box_x, box_y))
            
            log_scales.append(math.log(1.0 / scale))
            log_counts.append(math.log(len(boxes)))
        
        if len(log_scales) < 2:
            return 1.0
        
        # Fit line: slope is fractal dimension
        coeffs = np.polyfit(log_scales, log_counts, 1)
        dimension = coeffs[0]
        
        # Fractal dimension should be positive
        return max(0.0, dimension)
    
    @staticmethod
    def compute_symbol_complexity_score(
        symbol: Dict,
        fractal_dimension: float
    ) -> float:
        """
        Compute complexity score for a symbol based on fractal dimension.
        
        Higher dimension = more complex representation needed = more tokens
        """
        base_complexity = symbol.get('cyclomatic_complexity', 1)
        nesting = symbol.get('nesting_depth', 1)
        num_params = symbol.get('num_parameters', 0)
        
        # Fractal scaling
        complexity = (base_complexity + nesting) * (1 + fractal_dimension / 2.0)
        complexity *= (1 + num_params / 10.0)
        
        return complexity
    
    @staticmethod
    def filter_by_complexity(
        symbols: List[Dict],
        edges: List[Dict],
        complexity_percentile: float = 0.7,
        top_k: Optional[int] = None
    ) -> List[Dict]:
        """Keep symbols with high fractal-based complexity scores."""
        fractal_dim = FractalDimensionOptimizer.compute_box_counting_dimension(symbols)
        
        scored = []
        for symbol in symbols:
            score = FractalDimensionOptimizer.compute_symbol_complexity_score(
                symbol, fractal_dim
            )
            scored.append((score, symbol))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        
        # Keep top percentile
        cutoff_idx = int(len(scored) * (1 - complexity_percentile))
        filtered = scored[cutoff_idx:]
        
        if top_k:
            filtered = filtered[:top_k]
        
        return [s for _, s in filtered]


class WaveFunctionCollapseOptimizer:
    """
    Wave Function Collapse for Symbol Merging.
    
    Inspired by quantum mechanics: symbols exist in superposition of states
    until observed (used). Collapses redundant/overlapping symbols into
    minimal representation.
    
    Merges symbols that:
    1. Have similar names (Levenshtein distance < threshold)
    2. Are in same file
    3. Have overlapping call patterns
    """
    
    @staticmethod
    def compute_symbol_similarity(key1: str, key2: str) -> float:
        """
        Compute similarity between two symbol keys.
        
        Uses normalized Levenshtein distance + structural similarity
        """
        if key1 == key2:
            return 1.0
        
        # Levenshtein distance
        def levenshtein(s1, s2):
            if len(s1) < len(s2):
                return levenshtein(s2, s1)
            if len(s2) == 0:
                return len(s1)
            
            prev_row = range(len(s2) + 1)
            for i, c1 in enumerate(s1):
                curr_row = [i + 1]
                for j, c2 in enumerate(s2):
                    insertions = prev_row[j + 1] + 1
                    deletions = curr_row[j] + 1
                    substitutions = prev_row[j] + (c1 != c2)
                    curr_row.append(min(insertions, deletions, substitutions))
                prev_row = curr_row
            
            return prev_row[-1]
        
        distance = levenshtein(key1, key2)
        max_len = max(len(key1), len(key2))
        similarity = 1.0 - (distance / max_len if max_len > 0 else 0)
        
        return similarity
    
    @staticmethod
    def find_collapsible_symbols(
        symbols: List[Dict],
        edges: List[Dict],
        similarity_threshold: float = 0.8
    ) -> List[List[str]]:
        """
        Find groups of symbols that can be collapsed/merged.
        
        Returns list of symbol key groups that are highly similar.
        """
        # Build call signature for each symbol
        call_signatures = defaultdict(set)
        for edge in edges:
            call_signatures[edge.get('caller', '')].add(edge.get('callee', ''))
            call_signatures[edge.get('callee', '')].add(edge.get('caller', ''))
        
        # Find similar symbols
        collapsed_groups = []
        visited = set()
        
        symbol_keys = [s.get('key', s.get('symbol_key', '')) for s in symbols]
        
        for i, key1 in enumerate(symbol_keys):
            if key1 in visited:
                continue
            
            group = [key1]
            visited.add(key1)
            
            for j, key2 in enumerate(symbol_keys[i+1:], i+1):
                if key2 in visited:
                    continue
                
                similarity = WaveFunctionCollapseOptimizer.compute_symbol_similarity(
                    key1, key2
                )
                
                # Check call pattern overlap
                calls1 = call_signatures.get(key1, set())
                calls2 = call_signatures.get(key2, set())
                
                if calls1 and calls2:
                    overlap = len(calls1 & calls2) / len(calls1 | calls2)
                    similarity = 0.6 * similarity + 0.4 * overlap
                
                if similarity >= similarity_threshold:
                    group.append(key2)
                    visited.add(key2)
            
            if len(group) > 1:
                collapsed_groups.append(group)
        
        return collapsed_groups
    
    @staticmethod
    def collapse_symbols(
        symbols: List[Dict],
        edges: List[Dict],
        similarity_threshold: float = 0.8
    ) -> Tuple[List[Dict], Dict[str, str]]:
        """
        Collapse similar symbols and return merged representation.
        
        Returns:
            - Merged symbol list
            - Mapping from old keys to new collapsed keys
        """
        groups = WaveFunctionCollapseOptimizer.find_collapsible_symbols(
            symbols, edges, similarity_threshold
        )
        
        # Create mapping
        key_mapping = {}
        for group in groups:
            representative = group[0]  # Keep first as representative
            for key in group[1:]:
                key_mapping[key] = representative
        
        # Filter out collapsed symbols
        merged_symbols = [
            s for s in symbols
            if s.get('key', s.get('symbol_key', '')) not in key_mapping
        ]
        
        return merged_symbols, key_mapping


class RenormalizationGroupOptimizer:
    """
    Renormalization Group Flow for Multi-Scale Abstraction.
    
    Inspired by statistical physics RG flow:
    1. Start with fine-grained symbol graph
    2. Coarse-grain by grouping related symbols
    3. Iterate to create hierarchical abstraction levels
    4. Select optimal scale based on token budget
    
    This creates a "flow" from detailed → abstract representations.
    """
    
    @dataclass
    class RenormalizationLevel:
        scale: int
        symbols: List[Dict]
        edges: List[Dict]
        num_symbols: int
        estimated_tokens: int
    
    @staticmethod
    def coarse_grain(
        symbols: List[Dict],
        edges: List[Dict],
        grouping_factor: int = 2
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Coarse-grain symbol graph by grouping related symbols.
        
        Groups symbols by:
        - Same file
        - Same parent class/module
        - High connectivity
        """
        # Group symbols by file and parent
        groups = defaultdict(list)
        for symbol in symbols:
            file_path = symbol.get('file_path', '')
            parent = symbol.get('parent', '')
            key = f"{file_path}::{parent}" if parent else file_path
            groups[key].append(symbol)
        
        # Merge groups if they exceed grouping factor
        coarse_symbols = []
        symbol_mapping = {}
        
        for group_key, group_symbols in groups.items():
            if len(group_symbols) <= grouping_factor:
                # Keep individual symbols
                coarse_symbols.extend(group_symbols)
                for s in group_symbols:
                    symbol_mapping[s.get('key', '')] = s.get('key', '')
            else:
                # Create coarse-grained symbol
                merged = {
                    'key': f"{group_key}::[COARSE_{len(coarse_symbols)}]",
                    'name': f"[COARSE] {group_key.split('::')[-1] or group_key}",
                    'symbol_type': 'coarse_grained',
                    'file_path': group_key.split('::')[0],
                    'line_start': min(s.get('line_start', 0) for s in group_symbols),
                    'line_end': max(s.get('line_end', 0) for s in group_symbols),
                    'num_merged_symbols': len(group_symbols)
                }
                coarse_symbols.append(merged)
                
                for s in group_symbols:
                    symbol_mapping[s.get('key', '')] = merged['key']
        
        # Remap edges
        coarse_edges = []
        for edge in edges:
            new_caller = symbol_mapping.get(edge.get('caller', ''), edge.get('caller', ''))
            new_callee = symbol_mapping.get(edge.get('callee', ''), edge.get('callee', ''))
            if new_caller != new_callee:
                coarse_edges.append({
                    'caller': new_caller,
                    'callee': new_callee,
                    'call_type': edge.get('call_type', 'call')
                })
        
        return coarse_symbols, coarse_edges
    
    @staticmethod
    def build_renormalization_flow(
        symbols: List[Dict],
        edges: List[Dict],
        max_levels: int = 4
    ) -> List['RenormalizationGroupOptimizer.RenormalizationLevel']:
        """
        Build complete renormalization group flow.
        
        Returns hierarchy of abstraction levels from fine to coarse.
        """
        levels = []
        current_symbols = symbols.copy()
        current_edges = edges.copy()
        
        for scale in range(max_levels):
            # Estimate tokens at this level
            symbol_text = json.dumps(current_symbols, separators=(',', ':'))
            edge_text = json.dumps(current_edges, separators=(',', ':'))
            estimated_tokens = (len(symbol_text) + len(edge_text)) // 4
            
            level = RenormalizationGroupOptimizer.RenormalizationLevel(
                scale=scale,
                symbols=current_symbols,
                edges=current_edges,
                num_symbols=len(current_symbols),
                estimated_tokens=estimated_tokens
            )
            levels.append(level)
            
            # Coarse-grain for next level
            if scale < max_levels - 1:
                current_symbols, current_edges = RenormalizationGroupOptimizer.coarse_grain(
                    current_symbols,
                    current_edges,
                    grouping_factor=2 ** (scale + 1)
                )
        
        return levels
    
    @staticmethod
    def select_optimal_scale(
        levels: List['RenormalizationGroupOptimizer.RenormalizationLevel'],
        token_budget: int = 2000
    ) -> 'RenormalizationGroupOptimizer.RenormalizationLevel':
        """
        Select coarsest scale that fits within token budget.
        
        Finds optimal trade-off between detail and token efficiency.
        """
        for level in reversed(levels):
            if level.estimated_tokens <= token_budget:
                return level
        
        # Return coarsest if even finest exceeds budget
        return levels[-1]


class UnifiedMathOptimizer:
    """
    Unified Mathematical Optimization Engine.
    
    Combines all mathematical techniques into a single pipeline:
    1. Entropy filtering (remove low-information symbols)
    2. Spectral ranking (prioritize central symbols)
    3. Thermodynamic pruning (remove high-energy symbols)
    4. Fractal complexity scoring (estimate true token cost)
    5. Wave function collapse (merge redundant symbols)
    6. Renormalization group (select optimal abstraction level)
    """
    
    @dataclass
    class OptimizationResult:
        optimized_symbols: List[Dict]
        optimized_edges: List[Dict]
        original_tokens: int
        optimized_tokens: int
        reduction_ratio: float
        techniques_applied: List[str]
        symbol_mapping: Dict[str, str]
    
    @staticmethod
    def estimate_tokens(symbols: List[Dict], edges: List[Dict]) -> int:
        """Estimate token count using compact JSON representation."""
        # Use compact JSON (no indentation)
        symbol_text = json.dumps(symbols, separators=(',', ':'))
        edge_text = json.dumps(edges, separators=(',', ':'))
        return (len(symbol_text) + len(edge_text)) // 4  # ~4 chars/token
    
    @staticmethod
    def optimize(
        symbols: List[Dict],
        edges: List[Dict],
        token_budget: int = 2000,
        enable_entropy: bool = True,
        enable_spectral: bool = True,
        enable_thermodynamic: bool = True,
        enable_fractal: bool = False,
        enable_wave_collapse: bool = True,
        enable_renormalization: bool = True
    ) -> 'UnifiedMathOptimizer.OptimizationResult':
        """
        Apply mathematical optimization pipeline.
        
        Args:
            symbols: List of symbol dicts
            edges: List of edge dicts
            token_budget: Target token count
            enable_*: Toggle individual techniques
        
        Returns:
            OptimizationResult with optimized symbols and metrics
        """
        techniques = []
        original_tokens = UnifiedMathOptimizer.estimate_tokens(symbols, edges)
        
        current_symbols = symbols.copy()
        current_edges = edges.copy()
        symbol_mapping = {}
        
        # Step 1: Wave function collapse (merge redundant symbols)
        if enable_wave_collapse and len(current_symbols) > 10:
            merged, mapping = WaveFunctionCollapseOptimizer.collapse_symbols(
                current_symbols, current_edges
            )
            if mapping:
                current_symbols = merged
                symbol_mapping.update(mapping)
                techniques.append(f"wave_collapse(merged={len(mapping)})")
        
        # Step 2: Entropy filtering
        if enable_entropy and len(current_symbols) > 20:
            entropies = EntropyOptimizer.calculate_symbol_entropy(
                current_symbols, current_edges
            )
            # Keep top 70% by entropy
            top_k = max(int(len(current_symbols) * 0.7), 20)
            filtered = EntropyOptimizer.filter_by_entropy_threshold(
                current_symbols, entropies, threshold=0.3, top_k=top_k
            )
            if len(filtered) < len(current_symbols):
                current_symbols = filtered
                techniques.append(f"entropy_filter(kept={len(filtered)})")
        
        # Step 3: Spectral ranking
        if enable_spectral and len(current_symbols) > 15:
            ranked = SpectralGraphOptimizer.spectral_filtering(
                current_symbols, current_edges,
                centrality_threshold=0.2,
                top_k=max(int(len(current_symbols) * 0.6), 15)
            )
            if len(ranked) < len(current_symbols):
                current_symbols = ranked
                techniques.append(f"spectral_ranking(kept={len(ranked)})")
        
        # Step 4: Thermodynamic pruning
        if enable_thermodynamic and len(current_symbols) > 10:
            pruned = ThermodynamicOptimizer.thermodynamic_pruning(
                current_symbols, current_edges,
                temperature=1.0,
                energy_threshold=0.8
            )
            if len(pruned) < len(current_symbols):
                current_symbols = pruned
                techniques.append(f"thermodynamic_prune(kept={len(pruned)})")
        
        # Step 5: Fractal complexity filtering
        if enable_fractal and len(current_symbols) > 20:
            filtered = FractalDimensionOptimizer.filter_by_complexity(
                current_symbols, current_edges,
                complexity_percentile=0.6
            )
            if len(filtered) < len(current_symbols):
                current_symbols = filtered
                techniques.append(f"fractal_filter(kept={len(filtered)})")
        
        # Step 6: Renormalization group (select optimal scale)
        if enable_renormalization:
            levels = RenormalizationGroupOptimizer.build_renormalization_flow(
                current_symbols, current_edges, max_levels=3
            )
            optimal = RenormalizationGroupOptimizer.select_optimal_scale(
                levels, token_budget
            )
            if optimal.scale > 0:
                current_symbols = optimal.symbols
                current_edges = optimal.edges
                techniques.append(f"renormalization(scale={optimal.scale})")
        
        optimized_tokens = UnifiedMathOptimizer.estimate_tokens(
            current_symbols, current_edges
        )
        reduction_ratio = original_tokens / max(optimized_tokens, 1)
        
        return UnifiedMathOptimizer.OptimizationResult(
            optimized_symbols=current_symbols,
            optimized_edges=current_edges,
            original_tokens=original_tokens,
            optimized_tokens=optimized_tokens,
            reduction_ratio=reduction_ratio,
            techniques_applied=techniques,
            symbol_mapping=symbol_mapping
        )
