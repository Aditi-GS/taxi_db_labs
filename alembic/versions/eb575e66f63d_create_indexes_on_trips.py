"""create indexes on trips

Revision ID: eb575e66f63d
Revises: bdec93e35103
Create Date: 2026-04-19 14:35:37.523569

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eb575e66f63d'
down_revision: Union[str, Sequence[str], None] = 'bdec93e35103'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('idx_trips_pickup_datetime', 'trips', ['tpep_pickup_datetime'])
    op.create_index('idx_trips_pickup_zone', 'trips', ['pu_location_id'])
    op.create_index('idx_trips_total_amount', 'trips', ['total_amount'])

def downgrade() -> None:
    op.drop_index('idx_trips_pickup_datetime', table_name='trips')
    op.drop_index('idx_trips_pickup_zone', table_name='trips')
    op.drop_index('idx_trips_total_amount', table_name='trips')