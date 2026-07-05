"""Main entry point for the package.

Lets the tool run as a module:

    python -m legal_agent review contract.txt --side buyer --jurisdiction US-CA

This mirrors the `legal-agent` console script defined in pyproject.toml.
"""

from __future__ import annotations

from .cli import main

if __name__ == "__main__":
    main()
