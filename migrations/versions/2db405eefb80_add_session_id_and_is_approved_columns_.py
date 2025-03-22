"""Add session_id and is_approved columns to booking

Revision ID: 2db405eefb80
Revises: cd32820d3a21
Create Date: 2025-03-23 02:09:08.734701

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2db405eefb80'
down_revision = 'cd32820d3a21'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('booking', schema=None) as batch_op:
        batch_op.add_column(sa.Column('session_id', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('is_approved', sa.Boolean(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('booking', schema=None) as batch_op:
        batch_op.drop_column('is_approved')
        batch_op.drop_column('session_id')

    # ### end Alembic commands ###
