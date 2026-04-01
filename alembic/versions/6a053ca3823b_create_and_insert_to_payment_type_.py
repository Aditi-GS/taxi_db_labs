"""create and insert to payment_type_lookup table

Revision ID: 6a053ca3823b
Revises: 3030377fc35a
Create Date: 2026-03-31 04:39:00.645927

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6a053ca3823b'
down_revision: Union[str, Sequence[str], None] = '3030377fc35a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    payment_type = A numeric code signifying how the passenger paid for the trip.
    payment_type                      int64
    0 = Flex Fare trip
    1 = Credit card
    2 = Cash
    3 = No charge
    4 = Dispute
    5 = Unknown
    6 = Voided trip
    """
    payment_type_table = op.create_table('payment_type_lookup',
                                        sa.Column('payment_type', sa.BIGINT(), primary_key=True),
                                        sa.Column('description', sa.VARCHAR(), nullable=False)
                                        )
    
    op.bulk_insert(
        payment_type_table,
        [
            {"payment_type": 0, "description": "Flex Fare trip"},
            {"payment_type": 1, "description": "Credit card"},
            {"payment_type": 2, "description": "Cash"},
            {"payment_type": 3, "description": "No charge"},
            {"payment_type": 4, "description": "Dispute"},
            {"payment_type": 5, "description": "Unknown"},
            {"payment_type": 6, "description": "Voided trip"}
        ]
    )

def downgrade() -> None:
    op.execute("DROP TABLE payment_type_lookup;")