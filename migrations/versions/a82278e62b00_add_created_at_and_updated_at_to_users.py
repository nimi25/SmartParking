"""Add created_at and updated_at to users

Revision ID: a82278e62b00
Revises: c1628470173f
Create Date: 2025-02-15 21:07:27.779499

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a82278e62b00'
down_revision = 'c1628470173f'
branch_labels = None
depends_on = None


def upgrade():
    # All columns already exist in the database.
    # Skipping all operations.
    pass


def downgrade():
    # Since nothing was added in upgrade, no changes need to be reverted.
    pass
