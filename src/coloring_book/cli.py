"""
Command-Line Interface for Coloring Book Generator
===================================================

Usage:
    python -m coloring_book generate --animal cat --style kawaii --difficulty easy
    python -m coloring_book batch --file animals.txt --output docs/examples/
"""

import logging
import argparse
from pathlib import Path
from typing import Optional

from .pipeline import ColoringBookPipeline, VALID_STYLES, VALID_DIFFICULTIES

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


class ColoringBookCLI:
    """Command-line interface for coloring book generation."""

    def __init__(self):
        self.parser = self._create_parser()

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser."""
        parser = argparse.ArgumentParser(
            prog="coloring-book",
            description="Generate coloring book pages with AI or SVG",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Generate single cat page
  python -m coloring_book generate --animal cat --style kawaii

  # Generate with all options
  python -m coloring_book generate --animal elephant --style realistic --difficulty hard --output cat.png

  # Batch generate from file
  python -m coloring_book batch --file animals.txt --output docs/examples/

  # Generate multiple animals inline
  python -m coloring_book batch --animals cat dog bird --output docs/examples/
            """,
        )

        # Global options
        parser.add_argument(
            "-v", "--verbose",
            action="store_true",
            help="Enable debug logging"
        )
        parser.add_argument(
            "--no-ai",
            action="store_true",
            help="Disable AI generation, use SVG only"
        )
        parser.add_argument(
            "--ai-url",
            default="http://localhost:5000",
            help="Genesis API base URL (default: http://localhost:5000)"
        )
        parser.add_argument(
            "--dpi",
            type=int,
            default=150,
            help="PNG export DPI (default: 150)"
        )

        # Subcommands
        subparsers = parser.add_subparsers(dest="command", help="Command to run")

        # Generate command
        generate_parser = subparsers.add_parser(
            "generate",
            help="Generate a single coloring page"
        )
        generate_parser.add_argument(
            "--no-ai",
            action="store_true",
            help="Disable AI generation, use SVG only"
        )
        generate_parser.add_argument(
            "-m", "--model",
            default="imagen",
            choices=["gemini", "imagen", "imagen-ultra"],
            help="AI model (default: imagen). imagen-ultra for highest detail"
        )
        generate_parser.add_argument(
            "-a", "--animal",
            required=True,
            help="Animal name (e.g., cat, dog, elephant, any animal)"
        )
        generate_parser.add_argument(
            "-s", "--style",
            default="coloring_book",
            choices=VALID_STYLES,
            help=f"Image style (default: coloring_book)"
        )
        generate_parser.add_argument(
            "-d", "--difficulty",
            default="medium",
            choices=VALID_DIFFICULTIES,
            help=f"Detail level (default: medium)"
        )
        generate_parser.add_argument(
            "-o", "--output",
            type=Path,
            help="Output file path (default: {animal}.png)"
        )

        # Batch command
        batch_parser = subparsers.add_parser(
            "batch",
            help="Generate multiple coloring pages"
        )

        batch_parser.add_argument(
            "--no-ai",
            action="store_true",
            help="Disable AI generation, use SVG only"
        )
        batch_parser.add_argument(
            "-m", "--model",
            default="imagen",
            choices=["gemini", "imagen", "imagen-ultra"],
            help="AI model (default: imagen). imagen-ultra for highest detail"
        )

        # Batch supports either --file or --animals
        batch_input = batch_parser.add_mutually_exclusive_group(required=True)
        batch_input.add_argument(
            "-f", "--file",
            type=Path,
            help="Text file with one animal per line"
        )
        batch_input.add_argument(
            "--animals",
            nargs="+",
            help="Animal names (space-separated)"
        )

        batch_parser.add_argument(
            "-s", "--style",
            default="coloring_book",
            choices=VALID_STYLES,
            help=f"Image style (default: coloring_book)"
        )
        batch_parser.add_argument(
            "-d", "--difficulty",
            default="medium",
            choices=VALID_DIFFICULTIES,
            help=f"Detail level (default: medium)"
        )
        batch_parser.add_argument(
            "-o", "--output",
            type=Path,
            required=True,
            help="Output directory"
        )

        # List command
        list_parser = subparsers.add_parser(
            "list",
            help="List available SVG animals"
        )
        list_parser.add_argument(
            "--json",
            action="store_true",
            help="Output as JSON"
        )

        return parser

    def run(self, args: Optional[list] = None):
        """Run the CLI."""
        parsed = self.parser.parse_args(args)
        setup_logging(parsed.verbose)

        if not parsed.command:
            self.parser.print_help()
            return 1

        try:
            if parsed.command == "generate":
                return self.cmd_generate(parsed)
            elif parsed.command == "batch":
                return self.cmd_batch(parsed)
            elif parsed.command == "list":
                return self.cmd_list(parsed)
            else:
                self.parser.print_help()
                return 1

        except Exception as e:
            logger.error(f"Error: {e}")
            return 1

    def cmd_generate(self, args) -> int:
        """Generate single page."""
        no_ai = getattr(args, 'no_ai', False)
        pipeline = ColoringBookPipeline(
            ai_enabled=not no_ai,
            ai_base_url=args.ai_url,
            png_dpi=args.dpi,
        )

        # Determine output path
        output_path = args.output or Path(f"{args.animal}.png")

        model = getattr(args, 'model', 'gemini')
        logger.info(f"Generating: {args.animal}")
        logger.info(f"  Style: {args.style}")
        logger.info(f"  Difficulty: {args.difficulty}")
        logger.info(f"  Model: {model}")
        logger.info(f"  Output: {output_path}")

        try:
            png_bytes = pipeline.generate(
                animal=args.animal,
                style=args.style,
                difficulty=args.difficulty,
                output_path=output_path,
                model=model,
            )

            logger.info(f"✅ Success! Generated {len(png_bytes)} bytes")
            logger.info(f"📁 Saved to: {output_path.absolute()}")
            return 0

        except Exception as e:
            logger.error(f"❌ Generation failed: {e}")
            return 1

    def cmd_batch(self, args) -> int:
        """Generate multiple pages."""
        # Load animal list
        if args.file:
            animals = self._load_animals_file(args.file)
        else:
            animals = args.animals

        model = getattr(args, 'model', 'gemini')
        logger.info(f"Batch generating {len(animals)} animals")
        logger.info(f"  Style: {args.style}")
        logger.info(f"  Difficulty: {args.difficulty}")
        logger.info(f"  Model: {model}")
        logger.info(f"  Output: {args.output}")

        no_ai = getattr(args, 'no_ai', False)
        pipeline = ColoringBookPipeline(
            ai_enabled=not no_ai,
            ai_base_url=args.ai_url,
            png_dpi=args.dpi,
        )

        results = pipeline.batch_generate(
            animals=animals,
            style=args.style,
            difficulty=args.difficulty,
            output_dir=args.output,
            model=model,
        )

        # Summary
        success = sum(1 for v in results.values() if v is not None)
        total = len(results)

        logger.info("")
        logger.info(f"📊 Batch Summary: {success}/{total} succeeded")

        for animal, png_bytes in results.items():
            if png_bytes:
                logger.info(f"  ✅ {animal}: {len(png_bytes)} bytes")
            else:
                logger.info(f"  ❌ {animal}: FAILED")

        return 0 if success == total else 1

    def cmd_list(self, args) -> int:
        """List available animals."""
        from .svg.factory import AnimalFactory

        animals = AnimalFactory.get_available_animals()

        if args.json:
            import json
            print(json.dumps(list(animals.keys())))
        else:
            logger.info("Available SVG animals:")
            for name in sorted(animals.keys()):
                logger.info(f"  - {name}")

        logger.info(f"\nTotal: {len(animals)} animals")
        logger.info("\nNote: AI generation supports any animal name, not just these!")

        return 0

    @staticmethod
    def _load_animals_file(path: Path) -> list[str]:
        """Load animal list from file."""
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        animals = []
        with open(path) as f:
            for line in f:
                animal = line.strip()
                if animal and not animal.startswith("#"):
                    animals.append(animal)

        return animals


def main():
    """Entry point."""
    cli = ColoringBookCLI()
    exit_code = cli.run()
    exit(exit_code)


if __name__ == "__main__":
    main()
