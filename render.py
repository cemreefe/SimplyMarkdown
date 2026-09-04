"""Compatibility entry point; prefer `python -m simplymarkdown`."""

from simplymarkdown.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
