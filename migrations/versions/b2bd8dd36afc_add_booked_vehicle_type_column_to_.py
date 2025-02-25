"""Add booked_vehicle_type column to booking table

Revision ID: b2bd8dd36afc
Revises: 3fb8fa1e071b
Create Date: 2025-02-25 11:25:40.803982

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2bd8dd36afc'
down_revision = '3fb8fa1e071b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('booking', schema=None) as batch_op:
        batch_op.add_column(sa.Column('booked_vehicle_type', sa.String(length=50), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('booking', schema=None) as batch_op:
        batch_op.drop_column('booked_vehicle_type')

    # ### end Alembic commands ###
