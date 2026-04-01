"""create trips table

Revision ID: 883e08bdff0f
Revises: 6a053ca3823b
Create Date: 2026-03-31 04:46:38.684569

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '883e08bdff0f'
down_revision: Union[str, Sequence[str], None] = '6a053ca3823b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE trips (
        trip_id BIGSERIAL PRIMARY KEY,
        vendor_id INT,
        tpep_pickup_datetime TIMESTAMP,
        tpep_dropoff_datetime TIMESTAMP,
        passenger_count INT,
        trip_distance FLOAT,
        ratecode_id INT,
        store_and_fwd_flag VARCHAR(1) CHECK (store_and_fwd_flag IN ('Y','N')),
        pu_location_id INT,
        do_location_id INT,
        payment_type INT,
        fare_amount FLOAT,
        extra FLOAT,
        mta_tax FLOAT,
        tip_amount FLOAT,
        tolls_amount FLOAT,
        improvement_surcharge FLOAT,
        total_amount FLOAT,
        congestion_surcharge FLOAT,
        airport_fee FLOAT,
        cbd_congestion_fee FLOAT
    );
    """)

def downgrade() -> None:
    op.drop_table('trips')