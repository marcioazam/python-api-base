# Scripts - Development Tools

This directory contains development tools, CLI commands, and utility scripts that are not part of the main API runtime.

## Structure

```
scripts/
├── cli/                    # CLI commands for development
│   ├── commands/
│   │   ├── db.py          # Database migration commands
│   │   ├── generate.py    # Code generation commands
│   │   └── test.py        # Test execution commands
│   └── __init__.py
└── README.md
```

## CLI Commands

### Database Commands (`db`)

```bash
# Run migrations
python -m scripts.cli.commands.db migrate --revision head

# Rollback migrations
python -m scripts.cli.commands.db rollback --steps 1

# Create new revision
python -m scripts.cli.commands.db revision --message "add users table"

# Show current revision
python -m scripts.cli.commands.db current

# Show migration history
python -m scripts.cli.commands.db history --verbose
```

### Code Generation Commands (`generate`)

```bash
# Generate entity with CRUD scaffolding
python -m scripts.cli.commands.generate entity user --fields "name:str,email:str"

# Dry run (preview without creating files)
python -m scripts.cli.commands.generate entity product --fields "name:str,price:float" --dry-run
```

### Test Commands (`test`)

```bash
# Run all tests
python -m scripts.cli.commands.test run

# Run with coverage
python -m scripts.cli.commands.test run --coverage

# Run unit tests only
python -m scripts.cli.commands.test unit

# Run integration tests
python -m scripts.cli.commands.test integration

# Run property-based tests
python -m scripts.cli.commands.test properties

# Watch mode
python -m scripts.cli.commands.test watch
```

## Notes

- These scripts are for development purposes only
- They should not be imported by the main API code
- The CLI uses Typer for command-line interface
