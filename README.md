# Nornikel

## Testing

This project uses pytest for testing. To run the tests:

```bash
# Install test dependencies
uv sync --group test

# Run all tests
uv run pytest

# Run tests with verbose output
uv run pytest -v
```

## Project Structure

- `src/` - Source code files
- `test/` - Test files
- `pyproject.toml` - Project configuration and dependencies