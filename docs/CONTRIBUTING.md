# Contributing to MVG Departures

This project follows a **trunk-based development** approach for simplicity and continuous integration.

## Development Workflow

### Trunk-Based Development

- **Main branch** (`main`) is the primary development branch
- All features are developed in **short-lived feature branches**
- Feature branches are merged directly to `main` via pull requests
- `main` is always in a deployable state

### Branch Naming

Use descriptive, short branch names:

```bash
# Feature branches
feature/add-station-search
feature/improve-ui-layout

# Bug fixes
fix/departure-time-formatting
fix/config-loading-error

# Documentation
docs/update-readme
```

### Workflow Steps

1. **Create a feature branch from main:**
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes:**
   - Write code following the project's architecture (ports-and-adapters)
   - Write tests for new functionality
   - Ensure all tests pass locally
   - Follow code style (Black, Ruff)

3. **Test locally:**
   ```bash
   # Run all tests
   uv run pytest
   
   # Check code formatting
   uv run black --check src tests
   
   # Lint code
   uv run ruff check src tests
   
   # Type check
   uv run mypy src
   ```

4. **Commit your changes:**
   ```bash
   git add .
   git commit -m "feat: add station search functionality"
   ```
   
   Use conventional commit messages:
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `docs:` - Documentation changes
   - `refactor:` - Code refactoring
   - `test:` - Test additions/changes
   - `chore:` - Maintenance tasks

5. **Push and create a pull request:**
   ```bash
   git push origin feature/your-feature-name
   ```
   
   Then create a pull request to `main` on GitHub.

6. **After review and approval:**
   - Merge the PR to `main`
   - Delete the feature branch
   - `main` is automatically tested and ready for deployment

### Code Quality Standards

- **Tests**: All new features must have tests
- **Coverage**: Maintain or improve test coverage
- **Type Hints**: Use type hints throughout
- **Documentation**: Update README/docs as needed
- **Linting**: Code must pass Black, Ruff, and mypy checks

### Running Tests Locally

```bash
# Install dependencies
uv sync --dev

# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=mvg_departures --cov-report=html

# Run specific test file
uv run pytest tests/test_services.py

# Run specific test
uv run pytest tests/test_services.py::test_group_departures_by_direction
```

### Code Style

The project uses:
- **Black** for code formatting (line length: 100)
- **Ruff** for linting
- **mypy** for type checking

Format your code before committing:
```bash
uv run black src tests
uv run ruff check --fix src tests
uv run mypy src
```

### Pull Request Guidelines

- Keep PRs small and focused (one feature/fix per PR)
- Ensure all CI checks pass
- Update documentation if needed
- Add tests for new functionality
- Write clear commit messages

### Architecture Principles

This project follows **ports-and-adapters** (hexagonal) architecture:

- **Domain Layer**: Core business logic and models (no external dependencies)
- **Application Layer**: Use cases and services
- **Adapters Layer**: External integrations (MVG API, Web UI, Config)

When adding features:
- Keep business logic in the domain/application layers
- Use interfaces (ports) for external dependencies
- Implement adapters for external systems
- Write tests that focus on behavior, not implementation

### Questions?

If you have questions about the development workflow or architecture, please open an issue on GitHub.


