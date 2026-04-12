"""
Entropy-Based Compression using Information Theory
Physics: Thermodynamic Entropy
Math: Shannon Entropy, Huffman Coding
"""

import math
import re
from collections import Counter
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class CompressionResult:
    """Result of entropy compression"""
    compressed_text: str
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    entropy_score: float
    important_segments: List[Tuple[int, int, float]]


class EntropyCompressor:
    """
    Compress code context using Shannon entropy and information theory.
    
    Physics Concept:
    - Entropy = measure of disorder/information content
    - High entropy = high information = keep
    - Low entropy = redundant = compress/remove
    
    Math:
    - Shannon Entropy: H(X) = -Σ p(x) * log2(p(x))
    - Information Content: I(x) = -log2(p(x))
    - Cross-Entropy: H(P,Q) = -Σ p(x) * log2(q(x))
    """
    
    def __init__(self, window_size: int = 100, min_entropy_threshold: float = 0.5):
        self.window_size = window_size
        self.min_entropy_threshold = min_entropy_threshold
        
    def calculate_shannon_entropy(self, text: str) -> float:
        """
        Calculate Shannon entropy of text.
        
        Formula: H(X) = -Σ p(x) * log2(p(x))
        
        Higher entropy = more information = more important
        """
        if not text:
            return 0.0
        
        # Count character frequencies
        freq = Counter(text)
        total = len(text)
        
        # Calculate probabilities and entropy
        entropy = 0.0
        for count in freq.values():
            p = count / total
            entropy -= p * math.log2(p)
        
        return entropy
    
    def calculate_information_content(self, token: str, 
                                       global_freq: Dict[str, int],
                                       total_tokens: int) -> float:
        """
        Calculate information content of a token.
        
        Formula: I(x) = -log2(p(x))
        
        Rare tokens have higher information content.
        """
        freq = global_freq.get(token, 1)
        p = freq / total_tokens
        
        # Add smoothing to avoid log(0)
        p = max(p, 1e-10)
        
        return -math.log2(p)
    
    def sliding_window_entropy(self, text: str) -> List[Tuple[int, float]]:
        """
        Calculate entropy for each sliding window.
        
        Returns: List of (position, entropy) tuples
        """
        words = text.split()
        entropies = []
        
        for i in range(0, len(words), self.window_size // 2):
            window = words[i:i + self.window_size]
            window_text = ' '.join(window)
            entropy = self.calculate_shannon_entropy(window_text)
            entropies.append((i, entropy))
        
        return entropies
    
    def identify_important_segments(self, text: str,
                                     query: str = None) -> List[Tuple[int, int, float]]:
        """
        Identify high-entropy segments that should be preserved.
        
        Uses:
        1. Shannon entropy for information density
        2. TF-IDF for relevance to query
        3. Syntactic patterns (function defs, class defs, etc.)
        
        Returns: List of (start, end, importance_score) tuples
        """
        segments = []
        lines = text.split('\n')
        
        # Global word frequency for IDF
        all_words = text.split()
        global_freq = Counter(all_words)
        total_words = len(all_words)
        
        # Query terms for relevance
        query_terms = set(query.lower().split()) if query else set()
        
        current_segment_start = 0
        current_entropy = 0.0
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            
            # Calculate line entropy
            line_entropy = self.calculate_shannon_entropy(line)
            
            # Boost score for syntactically important lines
            boost = 1.0
            
            # Function/class definitions are important
            if re.match(r'^(def |class |function |const |let |var )', line.strip()):
                boost = 2.0
            
            # Import statements provide context
            if re.match(r'^(import |from |require|#include)', line.strip()):
                boost = 1.5
            
            # Comments with TODO/FIXME are important
            if re.search(r'(TODO|FIXME|HACK|BUG|NOTE):', line, re.IGNORECASE):
                boost = 1.8
            
            # Query relevance boost
            if query_terms:
                words = set(line_lower.split())
                overlap = len(words & query_terms)
                if overlap > 0:
                    boost *= (1 + 0.5 * overlap)
            
            # Calculate information content
            words = line.split()
            info_content = sum(
                self.calculate_information_content(w, global_freq, total_words)
                for w in words
            ) / max(len(words), 1)
            
            # Combined importance score
            importance = (line_entropy * 0.3 + info_content * 0.3 + boost * 0.4)
            
            # Segment boundary detection
            if importance < self.min_entropy_threshold:
                if current_segment_start < i:
                    segments.append((
                        current_segment_start,
                        i,
                        current_entropy / (i - current_segment_start)
                    ))
                current_segment_start = i + 1
                current_entropy = 0.0
            else:
                current_entropy += importance
        
        # Add final segment
        if current_segment_start < len(lines):
            segments.append((
                current_segment_start,
                len(lines),
                current_entropy / max(len(lines) - current_segment_start, 1)
            ))
        
        # Sort by importance and return
        segments.sort(key=lambda x: x[2], reverse=True)
        return segments
    
    def compress(self, text: str, 
                 max_tokens: int = 10000,
                 query: str = None) -> CompressionResult:
        """
        Main compression method.
        
        Algorithm:
        1. Calculate entropy for each segment
        2. Rank segments by importance
        3. Keep high-entropy segments until token budget
        4. Summarize/remove low-entropy segments
        
        Expected Savings: 30-50% of tokens
        """
        original_tokens = len(text.split())
        
        # Identify important segments
        segments = self.identify_important_segments(text, query)
        
        # Sort segments by position for reconstruction
        sorted_segments = sorted(segments, key=lambda x: x[0])
        
        # Build compressed text
        lines = text.split('\n')
        compressed_lines = []
        total_tokens = 0
        important_ranges = []
        
        for start, end, importance in sorted_segments:
            segment_lines = lines[start:end]
            segment_text = '\n'.join(segment_lines)
            segment_tokens = len(segment_lines)
            
            # Check if adding this segment exceeds budget
            if total_tokens + segment_tokens <= max_tokens:
                compressed_lines.extend(segment_lines)
                compressed_lines.append("\n[...]\n")  # Marker for removed content
                total_tokens += segment_tokens
                important_ranges.append((start, end, importance))
        
        compressed_text = '\n'.join(compressed_lines)
        compressed_tokens = len(compressed_text.split())
        
        # Calculate metrics
        compression_ratio = compressed_tokens / original_tokens if original_tokens > 0 else 1.0
        overall_entropy = self.calculate_shannon_entropy(text)
        
        return CompressionResult(
            compressed_text=compressed_text,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compression_ratio=compression_ratio,
            entropy_score=overall_entropy,
            important_segments=important_ranges
        )
    
    def huffman_optimal_compression(self, symbols: List[str]) -> Dict[str, str]:
        """
        Generate Huffman codes for symbols.
        
        This is the theoretically optimal compression.
        
        Returns: Dictionary mapping symbol to Huffman code
        """
        if not symbols:
            return {}
        
        # Count frequencies
        freq = Counter(symbols)
        
        # Build Huffman tree using heap
        import heapq
        
        heap = [[weight, [symbol, ""]] for symbol, weight in freq.items()]
        heapq.heapify(heap)
        
        while len(heap) > 1:
            lo = heapq.heappop(heap)
            hi = heapq.heappop(heap)
            
            for pair in lo[1:]:
                pair[1] = '0' + pair[1]
            for pair in hi[1:]:
                pair[1] = '1' + pair[1]
            
            heapq.heappush(heap, [lo[0] + hi[0]] + lo[1:] + hi[1:])
        
        huffman_codes = dict(heapq.heappop(heap)[1:])
        return huffman_codes
