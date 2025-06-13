"""create_user_table

Revision ID: 3c5581805108
Revises:
Create Date: 2025-06-13 09:26:00.306101

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel # Added for SQLModel specific types if needed, though sa types are primary here


# revision identifiers, used by Alembic.
revision: str = '3c5581805108'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'user',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True, index=True),
        sa.Column('canvas_id', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('email', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now())
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('user')
