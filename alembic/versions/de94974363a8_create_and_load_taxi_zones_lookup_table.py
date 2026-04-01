"""create and load taxi_zones_lookup table

Revision ID: de94974363a8
Revises: 318d85193ff0
Create Date: 2026-03-31 16:54:32.222426

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pandas as pd
import os

# revision identifiers, used by Alembic.
revision: str = 'de94974363a8'
down_revision: Union[str, Sequence[str], None] = '318d85193ff0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
# LocationID	Borough	 Zone	service_zone
    op.create_table('taxi_zones_lookup',
                    sa.Column('location_id', sa.INTEGER, primary_key=True),
                    sa.Column('borough', sa.VARCHAR),
                    sa.Column('zone', sa.VARCHAR),
                    sa.Column('service_zone', sa.VARCHAR)                    
                    )
    
    CSV_FILE = os.path.abspath(r"taxi_zone_lookup.csv")
    df_raw = pd.read_csv(CSV_FILE)
    df_raw.columns = [col.lower() for col in df_raw.columns]
    df = df_raw.rename(columns={
        "locationid": "location_id"
    })

    conn = op.get_bind()  # SQLAlchemy connection from Alembic
    df.to_sql('taxi_zones_lookup', conn, if_exists='append', index=False)

def downgrade() -> None:
    op.drop_table('taxi_zones_lookup')