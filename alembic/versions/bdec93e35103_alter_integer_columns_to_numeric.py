"""alter passenger_count column in trips table

Revision ID: bdec93e35103
Revises: 3af5402fca85
Create Date: 2026-03-31 17:21:07.060188

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bdec93e35103'
down_revision: Union[str, Sequence[str], None] = '3af5402fca85'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'trips',
        'passenger_count',
        type_=sa.Numeric(10, 0),
        postgresql_using='passenger_count::NUMERIC'
    )

    op.alter_column(
        'ratecode_lookup',
        'ratecode_id',
        type_=sa.Numeric(10, 0),
        postgresql_using='ratecode_id::NUMERIC'
    )  

    op.alter_column(
        'trips',
        'ratecode_id',
        type_=sa.Numeric(10, 0),
        postgresql_using='ratecode_id::NUMERIC'
    )    

def downgrade() -> None:
    op.alter_column(
        'trips',
        'passenger_count',
        type_=sa.Integer(),
        postgresql_using='passenger_count::INTEGER'
    )

    op.alter_column(
        'trips',
        'ratecode_id',
        type_=sa.Integer(),
        postgresql_using='ratecode_id::INTEGER'
    )    

    op.alter_column(
        'ratecode_lookup',
        'ratecode_id',
        type_=sa.Integer(),
        postgresql_using='ratecode_id::INTEGER'
    )        