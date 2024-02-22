"""empty message

Revision ID: 99cf9629c224
Revises: cb1543b1696a
Create Date: 2024-02-21 21:31:38.912253

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = '99cf9629c224'
down_revision: Union[str, None] = 'cb1543b1696a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('entry', sa.Column('author', sqlmodel.sql.sqltypes.AutoString(), nullable=False))
    op.add_column('entry', sa.Column('image', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('entry', 'image')
    op.drop_column('entry', 'author')
    # ### end Alembic commands ###
