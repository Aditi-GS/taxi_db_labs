"""add foreign keys to trips table

Revision ID: 318d85193ff0
Revises: 883e08bdff0f
Create Date: 2026-03-31 04:53:01.017792

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '318d85193ff0'
down_revision: Union[str, Sequence[str], None] = '883e08bdff0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    vendor_id INT REFERENCES vendor_lookup(vendor_id)
    ratecode_id INT REFERENCES ratecode_lookup(ratecode_id)
    payment_type INT REFERENCES payment_type_lookup(payment_type)
    """
    op.create_foreign_key(
        'fk_trips_vendor',
        source_table='trips',
        referent_table='vendor_lookup',
        local_cols=['vendor_id'],
        remote_cols=['vendor_id'],
        ondelete='CASCADE'
    )

    op.create_foreign_key(
        'fk_trips_ratecode',
        source_table='trips',
        referent_table='ratecode_lookup',
        local_cols=['ratecode_id'],
        remote_cols=['ratecode_id'],
        ondelete='CASCADE'
    )

    op.create_foreign_key(
        'fk_trips_payment_type',
        source_table='trips',
        referent_table='payment_type_lookup',
        local_cols=['payment_type'],
        remote_cols=['payment_type'],
        ondelete='CASCADE'
    )

def downgrade() -> None:
    op.drop_constraint('fk_trips_vendor', 'trips', 'foreignkey')
    op.drop_constraint('fk_trips_ratecode', 'trips', 'foreignkey')
    op.drop_constraint('fk_trips_payment_type', 'trips', 'foreignkey')    
