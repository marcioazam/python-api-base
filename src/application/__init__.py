"""Application Layer - Vertical Slices Architecture.

Organized by bounded contexts with shared infrastructure:

Structure:
├── _shared/              # Shared infrastructure
│   ├── cqrs/             # Command/Query/Event buses
│   ├── middleware/       # Pipeline middleware
│   ├── batch/            # Batch operations
│   └── ...               # DTOs, exceptions, mappers
├── _services/            # Cross-cutting services
│   ├── feature_flags/    # Feature toggles
│   ├── file_upload/      # S3-compatible uploads
│   └── multitenancy/     # Tenant isolation
├── users/                # Users bounded context
│   ├── commands/         # Write operations
│   ├── queries/          # Read operations
│   ├── projections.py    # Event handlers
│   ├── read_model/       # Query-optimized DTOs
│   └── ...
└── items/                # Items bounded context
    ├── commands/
    └── queries/

**Architecture: Vertical Slices + CQRS**
**Feature: application-layer-restructuring-2025**
"""
