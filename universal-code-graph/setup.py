from setuptools import setup, find_packages

setup(
    name="universal-code-review-graph",
    version="1.0.0",
    description="Universal Code Review Graph MCP Server - Works with ALL AI assistants",
    author="Universal Code Review Graph Team",
    packages=find_packages(),
    install_requires=[
        "mcp>=1.0.0",
        "tree-sitter>=0.25.0",
        "tree-sitter-python>=0.25.0",
        "tree-sitter-javascript>=0.25.0",
        "tree-sitter-go>=0.25.0",
        "networkx>=3.0",
    ],
    entry_points={
        "console_scripts": [
            "universal-code-graph=server:main",
        ],
    },
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
