"""Example system tables (ItemExample, PedidoExample)

Revision ID: example_system_001
Revises: 
Create Date: 2024-12-01 00:00:00.000000

**Feature: example-system-demo**
**To disable: Remove this migration and related models**
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'example_system_001'
down_revision = None  # Update to your last migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    # === ItemExample Table ===
    op.create_table(
        'item_examples',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False, index=True),
        sa.Column('description', sa.Text(), nullable=True, default=''),
        sa.Column('sku', sa.String(50), nullable=False, unique=True, index=True),
        sa.Column('price_amount', sa.Numeric(12, 2), nullable=False, default=0),
        sa.Column('price_currency', sa.String(3), nullable=False, default='BRL'),
        sa.Column('quantity', sa.Integer(), nullable=False, default=0),
        sa.Column('status', sa.String(20), nullable=False, default='active', index=True),
        sa.Column('category', sa.String(100), nullable=True, default='', index=True),
        sa.Column('tags', sa.JSON(), nullable=True, default=[]),
        sa.Column('metadata', sa.JSON(), nullable=True, default={}),
        # Audit
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(100), nullable=False, default='system'),
        sa.Column('updated_by', sa.String(100), nullable=False, default='system'),
        # Soft delete
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False, index=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )

    # === PedidoExample Table ===
    op.create_table(
        'pedido_examples',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('customer_id', sa.String(100), nullable=False, index=True),
        sa.Column('customer_name', sa.String(200), nullable=False),
        sa.Column('customer_email', sa.String(255), nullable=True, default=''),
        sa.Column('status', sa.String(20), nullable=False, default='pending', index=True),
        sa.Column('shipping_address', sa.String(500), nullable=True, default=''),
        sa.Column('notes', sa.Text(), nullable=True, default=''),
        sa.Column('tenant_id', sa.String(100), nullable=True, index=True),
        sa.Column('metadata', sa.JSON(), nullable=True, default={}),
        # Audit
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(100), nullable=False, default='system'),
        sa.Column('updated_by', sa.String(100), nullable=False, default='system'),
        # Soft delete
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False, index=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )

    # === PedidoItemExample Table ===
    op.create_table(
        'pedido_item_examples',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('pedido_id', sa.String(36), sa.ForeignKey('pedido_examples.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('item_id', sa.String(36), sa.ForeignKey('item_examples.id'), nullable=False, index=True),
        sa.Column('item_name', sa.String(200), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('unit_price_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('unit_price_currency', sa.String(3), nullable=False, default='BRL'),
        sa.Column('discount', sa.Numeric(5, 2), nullable=False, default=0),
    )


def downgrade() -> None:
    op.drop_table('pedido_item_examples')
    op.drop_table('pedido_examples')
    op.drop_table('item_examples')
