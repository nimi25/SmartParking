"""Remove latitude and longitude from parking_spots

Revision ID: 5db7fe035218
Revises: 5d8076feba0e
Create Date: 2025-02-24 04:01:02.815753

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5db7fe035218'
down_revision: Union[str, None] = '5d8076feba0e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    with op.batch_alter_table('parking_spots', schema=None) as batch_op:
        batch_op.drop_column('latitude')
        batch_op.drop_column('longitude')

def downgrade():
    with op.batch_alter_table('parking_spots', schema=None) as batch_op:
        batch_op.add_column(sa.Column('latitude', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('longitude', sa.Float(), nullable=True))
