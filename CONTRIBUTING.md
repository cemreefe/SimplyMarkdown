# Contributing to SimplyMarkdown

Thank you for your interest in contributing to SimplyMarkdown! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Code Style](#code-style)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)

## Code of Conduct

Please be respectful and considerate in all interactions. We aim to maintain a welcoming and inclusive environment for everyone.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/SimplyMarkdown.git
   cd SimplyMarkdown
   ```
3. Add the upstream repository:
   ```bash
   git remote add upstream https://github.com/cemreefe/SimplyMarkdown.git
   ```

## Development Setup

### Prerequisites

- Python 3.10 or higher
- pip

### Installation

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install the package in development mode with all dependencies:
   ```bash
   pip install -e ".[all]"
   ```

3. Verify the installation:
   ```bash
   simplymarkdown --version
   pytest
   ```

## Making Changes

### Branching Strategy

1. Create a new branch for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bugfix-name
   ```

2. Make your changes in small, focused commits

3. Keep your branch up to date with upstream:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

### Commit Messages

Use clear, descriptive commit messages:

```
type: short description

Longer description if needed. Explain what and why,
not how (the code shows how).
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat: add pagination support for post listings

fix: resolve file handle leak in render.py

docs: improve README with more examples
```

## Code Style

### Python Style

We follow PEP 8 with some modifications. Use the following tools:

- **Ruff** for linting and formatting:
  ```bash
  ruff check simplymarkdown tests
  ruff format simplymarkdown tests
  ```

- **MyPy** for type checking:
  ```bash
  mypy simplymarkdown
  ```

### Key Guidelines

1. **Type hints**: Use type hints for all function parameters and return values
   ```python
   def process_file(path: str, options: dict[str, Any]) -> str:
       ...
   ```

2. **Docstrings**: Use Google-style docstrings for all public functions
   ```python
   def convert_to_html(content: str, base_path: str = "") -> tuple[str, dict]:
       """Convert markdown content to HTML.
       
       Args:
           content: Raw markdown string.
           base_path: Base path for resolving relative links.
           
       Returns:
           Tuple of (html_content, metadata_dict).
       """
   ```

3. **Imports**: Use explicit imports, avoid wildcards
   ```python
   # Good
   from simplymarkdown.utils import read_file_content, get_extension
   
   # Avoid
   from simplymarkdown.utils import *
   ```

4. **Constants**: Use UPPER_CASE for module-level constants
   ```python
   DEFAULT_TEMPLATE = "templates/base.html"
   MAX_PREVIEW_LENGTH = 160
   ```

## Testing

### Running Tests

Run the full test suite:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=simplymarkdown --cov-report=html
```

Run specific tests:
```bash
pytest tests/test_utils.py
pytest tests/test_utils.py::TestGetExtension
pytest tests/test_utils.py::TestGetExtension::test_simple_extension
```

### Writing Tests

1. Place tests in the `tests/` directory
2. Name test files `test_*.py`
3. Name test functions `test_*`
4. Use pytest fixtures for common setup
5. Aim for high coverage of new code

Example test:
```python
import pytest
from simplymarkdown.utils import sanitize_filename


class TestSanitizeFilename:
    """Tests for sanitize_filename function."""

    def test_spaces_to_dashes(self) -> None:
        assert sanitize_filename("my file name") == "my-file-name"

    def test_no_changes_needed(self) -> None:
        assert sanitize_filename("already-clean") == "already-clean"
```

## Submitting Changes

### Pull Request Process

1. Ensure all tests pass:
   ```bash
   pytest
   ruff check simplymarkdown tests
   mypy simplymarkdown
   ```

2. Update documentation if needed

3. Push your branch:
   ```bash
   git push origin feature/your-feature-name
   ```

4. Create a Pull Request on GitHub:
   - Provide a clear title and description
   - Reference any related issues
   - Include screenshots for UI changes

5. Wait for review and address any feedback

### PR Checklist

- [ ] Tests added/updated for new functionality
- [ ] All tests pass
- [ ] Linting passes
- [ ] Type checking passes
- [ ] Documentation updated if needed
- [ ] CHANGELOG.md updated for notable changes

## Questions?

If you have questions, feel free to:
- Open an issue on GitHub
- Start a discussion

Thank you for contributing!
