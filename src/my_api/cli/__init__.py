"""CLI tools for my-api project management.

Provides commands for:
- Entity generation
- Database migrations
- Test execution
- Development utilities

Usage:
    api-cli --help
    api-cli generate entity product --fields "name:str,price:float"
    api-cli db migrate
    api-cli test run --coverage
"""

from my_api.cli.main import app

__all__ = ["app"]
