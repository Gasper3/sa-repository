default:
    @just --list

# Code quality

[group('quality')]
[doc('Run ruff linter')]
lint:
    uv run ruff check .

[group('quality')]
[doc('Run ruff linter and auto-fix violations')]
lint-fix:
    uv run ruff check --fix .

[group('quality')]
[doc('Format code with ruff')]
format:
    uv run ruff format .

[group('quality')]
[doc('Check formatting without writing changes')]
format-check:
    uv run ruff format --check .

[group('quality')]
[doc('Run mypy type checker')]
typecheck:
    uv run mypy sa_repository/

# Testing

[group('test')]
[doc('Run test suite')]
test:
    uv run pytest tests/

[group('test')]
[doc('Run test suite with coverage report')]
test-cov:
    uv run pytest --cov=sa_repository tests/

[group('test')]
[doc('Generate HTML coverage report and open it')]
cov-html:
    uv run pytest --cov=sa_repository --cov-report=html tests/
    open htmlcov/index.html

# CI

[group('ci')]
[doc('Run all checks: lint, format, typecheck, tests with coverage')]
run-checks: lint format-check typecheck test-cov
