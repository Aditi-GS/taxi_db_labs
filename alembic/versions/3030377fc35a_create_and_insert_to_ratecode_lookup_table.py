"""create and insert to rate_code_lookup table

Revision ID: 3030377fc35a
Revises: cad8d04dbaaf
Create Date: 2026-03-31 04:27:24.728441

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3030377fc35a'
down_revision: Union[str, Sequence[str], None] = 'cad8d04dbaaf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    RatecodeID = The final rate code in effect at the end of the trip.
    ratecodeid                      float64
    1 = Standard rate
    2 = JFK
    3 = Newark
    4 = Nassau or Westchester
    5 = Negotiated fare
    6 = Group ride
    99 = Null/unknown
    """

    ratecode_table = op.create_table('ratecode_lookup',
                                    sa.Column('ratecode_id', sa.FLOAT(), primary_key=True),
                                    sa.Column('ratecode_name', sa.VARCHAR(), nullable=True)
                                    )
    op.bulk_insert(
        ratecode_table, 
        [
            {'ratecode_id': 1, 'ratecode_name': 'Standard rate'},
            {'ratecode_id': 2, 'ratecode_name': 'JFK'},
            {'ratecode_id': 3, 'ratecode_name': 'Newark'},
            {'ratecode_id': 4, 'ratecode_name': 'Nassau or Westchester'},
            {'ratecode_id': 5, 'ratecode_name': 'Negotiated fare'},
            {'ratecode_id': 6, 'ratecode_name': 'Group ride'},
            {'ratecode_id': 99, 'ratecode_name': 'Null/unknown'},
        ]
    )

def downgrade() -> None:
    op.drop_table('ratecode_lookup')
