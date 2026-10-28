"""add provenance fields to document_chunks

Revision ID: a1b2c3d4e5f6
Revises: 
Create Date: 2026-10-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('document_chunks', sa.Column('source_reference', sa.String(), nullable=True))
    op.add_column('document_chunks', sa.Column('start_char', sa.Integer(), nullable=True))
    op.add_column('document_chunks', sa.Column('end_char', sa.Integer(), nullable=True))
    op.add_column('document_chunks', sa.Column('chunk_index', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('document_chunks', 'chunk_index')
    op.drop_column('document_chunks', 'end_char')
    op.drop_column('document_chunks', 'start_char')
    op.drop_column('document_chunks', 'source_reference')
