"""Add ParkingSpace model

Revision ID: 4002a4366598
Revises: 6faea6f4e177
Create Date: 2025-03-18 17:13:09.922989

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '4002a4366598'
down_revision = '6faea6f4e177'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create the new parking_space table.
    op.create_table(
        'parking_space',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('parking_spot_id', sa.Integer(), nullable=False),
        sa.Column('vehicle_type', sa.String(length=10), nullable=False),
        sa.Column('sub_spot_number', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True, server_default='available'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    # Create foreign key from parking_space.parking_spot_id to parking_spot.id.
    op.create_foreign_key(None, 'parking_space', 'parking_spot', ['parking_spot_id'], ['id'])

    # 2. Add new column parking_space_id to booking as nullable.
    op.add_column('booking', sa.Column('parking_space_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'booking', 'parking_space', ['parking_space_id'], ['id'])

    # 3. Update legacy booking rows:
    conn = op.get_bind()

    # a) Find an existing ParkingSpot row; if none, create a dummy one.
    dummy_parking_spot = conn.execute(text("SELECT id FROM parking_spot LIMIT 1")).fetchone()
    if dummy_parking_spot is None:
        result = conn.execute(
            text(
                "INSERT INTO parking_spot (owner_id, location, price, lat, lng, availability) "
                "VALUES (1, 'Dummy Location', 0, 0, 0, true) RETURNING id"
            )
        )
        dummy_parking_spot = result.fetchone()
    dummy_spot_id = dummy_parking_spot[0]

    # b) Create a dummy ParkingSpace row for that ParkingSpot.
    result = conn.execute(
        text(
            "INSERT INTO parking_space (parking_spot_id, vehicle_type, sub_spot_number, status) "
            "VALUES (:dummy_spot_id, '2W', 1, 'available') RETURNING id"
        ),
        {"dummy_spot_id": dummy_spot_id}
    )
    dummy_parking_space = result.fetchone()
    dummy_parking_space_id = dummy_parking_space[0]

    # c) Update all legacy bookings to use the dummy parking_space_id.
    conn.execute(
        text("UPDATE booking SET parking_space_id = :dummy_parking_space_id WHERE parking_space_id IS NULL"),
        {"dummy_parking_space_id": dummy_parking_space_id}
    )

    # 4. Alter the column to be non-nullable.
    op.alter_column('booking', 'parking_space_id', nullable=False)


def downgrade():
    # Reverse changes made in upgrade.
    # 1. Restore removed columns in booking and parking_spot (if desired).
    with op.batch_alter_table('parking_spot', schema=None) as batch_op:
        batch_op.add_column(sa.Column('four_wheeler_spaces', sa.INTEGER(), autoincrement=False, nullable=True))
        batch_op.add_column(sa.Column('two_wheeler_spaces', sa.INTEGER(), autoincrement=False, nullable=True))

    with op.batch_alter_table('booking', schema=None) as batch_op:
        batch_op.add_column(sa.Column('four_wheeler', sa.INTEGER(), autoincrement=False, nullable=True))
        batch_op.add_column(sa.Column('two_wheeler', sa.INTEGER(), autoincrement=False, nullable=True))
        batch_op.add_column(sa.Column('spot_id', sa.INTEGER(), autoincrement=False, nullable=False))
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key('booking_spot_id_fkey', 'parking_spot', ['spot_id'], ['id'])
        batch_op.drop_column('parking_space_id')

    # 2. Drop the parking_space table.
    op.drop_table('parking_space')
