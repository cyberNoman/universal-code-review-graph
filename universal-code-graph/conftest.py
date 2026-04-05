"""
Root conftest.py — makes pytest add universal-code-graph/ to sys.path
so tests can do: from code_graph import ...
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
