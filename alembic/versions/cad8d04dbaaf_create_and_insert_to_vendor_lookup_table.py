"""create and insert to vendor_lookup table

Revision ID: cad8d04dbaaf
Revises: 
Create Date: 2026-03-31 04:15:32.368652

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cad8d04dbaaf'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    VendorID = A code indicating the TPEP provider that provided the record.
    vendorid                          int32
    1 = Creative Mobile Technologies, LLC
    2 = Curb Mobility, LLC
    6 = Myle Technologies Inc
    7 = Helix
    """
    vendor_table = op.create_table('vendor_lookup',
                    sa.Column('vendor_id', sa.INTEGER()),
                    sa.Column('vendor_name', sa.VARCHAR(), nullable=False),
                    sa.PrimaryKeyConstraint('vendor_id', name="vendor_lookup_pk")
                    )

    op.bulk_insert(
        vendor_table,
        [
            {'vendor_id': 1, 'vendor_name': 'Creative Mobile Technologies, LLC'},
            {'vendor_id': 2, 'vendor_name': 'Curb Mobility, LLC'},
            {'vendor_id': 6, 'vendor_name': 'Myle Technologies Inc'},
            {'vendor_id': 7, 'vendor_name': 'Helix'},
        ]        
    )

def downgrade() -> None:
    op.drop_table('vendor_lookup')
