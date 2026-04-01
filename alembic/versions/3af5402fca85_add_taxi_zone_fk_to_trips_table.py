"""add taxi_zone fk to trips table

Revision ID: 3af5402fca85
Revises: de94974363a8
Create Date: 2026-03-31 17:08:15.977764

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3af5402fca85'
down_revision: Union[str, Sequence[str], None] = 'de94974363a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
        # pu_location_id INT,
        # do_location_id INT,

    op.create_foreign_key(
        'fk_trips_pu_location',
        source_table='trips',
        referent_table='taxi_zones_lookup',
        local_cols=['pu_location_id'],
        remote_cols=['location_id'],
        ondelete='CASCADE'
    )

    op.create_foreign_key(
        'fk_trips_do_location',
        source_table='trips',
        referent_table='taxi_zones_lookup',
        local_cols=['do_location_id'],
        remote_cols=['location_id'],
        ondelete='CASCADE'
    )

def downgrade() -> None:
    op.drop_constraint('fk_trips_pu_location', 'trips', 'foreignkey')
    op.drop_constraint('fk_trips_do_location', 'trips', 'foreignkey')