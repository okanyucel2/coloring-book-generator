"""Module entry point for CLI execution.

Usage:
    python -m coloring_book generate --animal cat --style kawaii
    python -m coloring_book batch --file animals.txt --output docs/examples/
"""

from .cli import main

if __name__ == "__main__":
    main()
