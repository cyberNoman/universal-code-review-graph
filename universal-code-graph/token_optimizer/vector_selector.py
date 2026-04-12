"""
Vector-Based Selection using LSH (Locality Sensitive Hashing)
Physics: Vector Space, Cosine Similarity
Math: Linear Algebra, Hash Functions, ANN (Approximate Nearest Neighbors)
"""

import hashlib
import random
import numpy as np
from typing import List, Dict, Tuple, Set
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class VectorResult:
    """Result of vector-based selection"""
    selected_symbols: List[str]
    similarities: Dict[str, float]
    token_savings: int
    accuracy: float


class VectorSelector:
    """
    Select relevant symbols using vector embeddings and LSH.
    
    Physics Concept:
    - Symbols exist in high-dimensional vector space
    - Similar symbols cluster together
    - Distance = dissimilarity
    
    Math:
    - Cosine Similarity: cos(θ) = (A·B) / (||A|| ||B||)
    - LSH: Hash similar vectors to same bucket with high probability
    - Random Projection: Reduce dimensions while preserving similarity
    """
    
    def __init__(self, num_hash_tables: int = 10, 
                 hash_size: int = 16,
                 embedding_dim: int = 128):
        self.num_hash_tables = num_hash_tables
        self.hash_size = hash_size
        self.embedding_dim = embedding_dim
        
        # Initialize random projection vectors for LSH
        self.hash_functions = self._initialize_hash_functions()
        
        # Hash tables
        self.hash_tables = [defaultdict(list) for _ in range(num_hash_tables)]
        
    def _initialize_hash_functions(self) -> List[np.ndarray]:
        """Initialize random projection vectors for LSH."""
        hash_functions = []
        for _ in range(self.num_hash_tables * self.hash_size):
            # Random hyperplane for projection
            v = np.random.randn(self.embedding_dim)
            v = v / np.linalg.norm(v)  # Normalize
            hash_functions.append(v)
        return hash_functions
    
    def text_to_embedding(self, text: str) -> np.ndarray:
        """
        Convert text to vector embedding.
        
        Simple approach: Character n-gram frequency vector
        Advanced: Use pre-trained embeddings (Word2Vec, BERT, etc.)
        """
        # Simple character n-gram representation
        n = 3  # trigrams
        ngrams = [text[i:i+n] for i in range(len(text) - n + 1)]
        
        # Create frequency vector
        vocab = set(ngrams)
        embedding = np.zeros(self.embedding_dim)
        
        # Hash n-grams to embedding dimensions
        for ngram in ngrams:
            idx = hash(ngram) % self.embedding_dim
            embedding[idx] += 1
        
        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        return embedding
    
    def cosine_similarity(self, vec1: np.ndarray, 
                          vec2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Formula: cos(θ) = (A·B) / (||A|| ||B||)
        
        Returns value between -1 and 1.
        1 = identical direction (similar)
        0 = orthogonal (unrelated)
        -1 = opposite direction (dissimilar)
        """
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def lsh_hash(self, embedding: np.ndarray, 
                 table_idx: int) -> str:
        """
        Compute LSH hash for embedding.
        
        Using random projection LSH:
        - Project vector onto random hyperplanes
        - Hash bit = 1 if projection > 0, else 0
        - Similar vectors have same hash with high probability
        """
        hash_bits = []
        start_idx = table_idx * self.hash_size
        
        for i in range(self.hash_size):
            hyperplane = self.hash_functions[start_idx + i]
            projection = np.dot(embedding, hyperplane)
            hash_bits.append('1' if projection > 0 else '0')
        
        return ''.join(hash_bits)
    
    def index_symbol(self, symbol: str, text: str):
        """Add symbol to LSH index."""
        embedding = self.text_to_embedding(text)
        
        for table_idx in range(self.num_hash_tables):
            hash_value = self.lsh_hash(embedding, table_idx)
            self.hash_tables[table_idx][hash_value].append((symbol, embedding))
    
    def query_similar(self, query: str, 
                      top_k: int = 10) -> List[Tuple[str, float]]:
        """
        Find similar symbols using LSH.
        
        Algorithm:
        1. Hash query to all hash tables
        2. Retrieve candidates from same buckets
        3. Calculate exact cosine similarity
        4. Return top-k results
        
        Expected Speedup: 100-1000x vs brute force
        """
        query_embedding = self.text_to_embedding(query)
        
        # Collect candidates from all hash tables
        candidates = set()
        for table_idx in range(self.num_hash_tables):
            hash_value = self.lsh_hash(query_embedding, table_idx)
            for symbol, _ in self.hash_tables[table_idx][hash_value]:
                candidates.add(symbol)
        
        # Calculate exact similarity for candidates
        similarities = []
        for symbol in candidates:
            # Find symbol's embedding
            for table_idx in range(self.num_hash_tables):
                hash_value = self.lsh_hash(query_embedding, table_idx)
                for s, emb in self.hash_tables[table_idx][hash_value]:
                    if s == symbol:
                        sim = self.cosine_similarity(query_embedding, emb)
                        similarities.append((symbol, sim))
                        break
        
        # Sort by similarity and return top-k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def select_relevant_symbols(self, 
                                symbols: Dict[str, str],
                                query: str,
                                changed_symbols: List[str],
                                max_tokens: int = 50000,
                                tokens_per_symbol: int = 500) -> VectorResult:
        """
        Select relevant symbols using vector similarity.
        
        Strategy:
        1. Index all symbols
        2. Query with changed symbols + user query
        3. Select top symbols by similarity until token budget
        
        Expected Savings: 40-60% of tokens
        """
        # Index all symbols
        for symbol, content in symbols.items():
            self.index_symbol(symbol, content)
        
        # Query with changed symbols
        all_similarities = defaultdict(float)
        
        for changed in changed_symbols:
            if changed in symbols:
                similar = self.query_similar(symbols[changed], top_k=20)
                for symbol, sim in similar:
                    all_similarities[symbol] += sim
        
        # Also query with user query if provided
        if query:
            similar = self.query_similar(query, top_k=20)
            for symbol, sim in similar:
                all_similarities[symbol] += sim * 1.5  # Boost user query
        
        # Always include changed symbols
        for changed in changed_symbols:
            all_similarities[changed] = float('inf')
        
        # Sort by similarity
        sorted_symbols = sorted(all_similarities.items(), 
                               key=lambda x: x[1], 
                               reverse=True)
        
        # Select until token budget
        selected = []
        total_tokens = 0
        
        for symbol, sim in sorted_symbols:
            if total_tokens + tokens_per_symbol <= max_tokens:
                selected.append(symbol)
                total_tokens += tokens_per_symbol
        
        # Calculate savings
        original_tokens = len(symbols) * tokens_per_symbol
        saved = original_tokens - total_tokens
        accuracy = len(selected) / len(symbols) if symbols else 0
        
        return VectorResult(
            selected_symbols=selected,
            similarities=dict(all_similarities),
            token_savings=saved,
            accuracy=accuracy
        )
    
    def ann_search(self, query_embedding: np.ndarray,
                   k: int = 10) -> List[Tuple[str, float]]:
        """
        Approximate Nearest Neighbor search.
        
        Uses LSH for fast approximate search.
        """
        return self.query_similar("query", top_k=k)
