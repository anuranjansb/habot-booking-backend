"""prevent overlapping active bookings

Revision ID: 45f8628ab72d
Revises: 0585aff203e7
Create Date: 2026-08-12 16:32:10.825418

"""

from alembic import op


revision = "45f8628ab72d"
down_revision = "0585aff203e7"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "CREATE EXTENSION IF NOT EXISTS btree_gist"
    )

    op.execute(
        """
        ALTER TABLE booking_requests
        ADD CONSTRAINT booking_no_overlap
        EXCLUDE USING gist (
            lsa_id WITH =,
            tstzrange(start_time, end_time, '[)') WITH &&
        )
        WHERE (
            status IN ('PENDING', 'CONFIRMED')
        )
        """
    )


def downgrade():
    op.execute(
        """
        ALTER TABLE booking_requests
        DROP CONSTRAINT IF EXISTS booking_no_overlap
        """
    )
