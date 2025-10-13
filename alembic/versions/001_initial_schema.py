"""Initial schema

Revision ID: 001
Revises:
Create Date: 2025-10-12

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create associate_levels table
    op.create_table(
        'associate_levels',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('description', sa.String(length=100), nullable=False),
        sa.Column('level_indicator', sa.Integer(), nullable=False),
        sa.CheckConstraint('level_indicator > 0', name='level_indicator_positive'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('description'),
        sa.UniqueConstraint('level_indicator')
    )

    # Create performance_ratings table
    op.create_table(
        'performance_ratings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('description', sa.String(length=100), nullable=False),
        sa.Column('level_indicator', sa.Integer(), nullable=False),
        sa.CheckConstraint('level_indicator > 0', name='performance_level_positive'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('description'),
        sa.UniqueConstraint('level_indicator')
    )

    # Create associates table
    op.create_table(
        'associates',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('associate_level_id', sa.Integer(), nullable=False),
        sa.Column('manager_id', sa.Integer(), nullable=True),
        sa.Column('performance_rating_id', sa.Integer(), nullable=True),
        sa.Column('is_people_manager', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['associate_level_id'], ['associate_levels.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['manager_id'], ['associates.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['performance_rating_id'], ['performance_ratings.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for better query performance
    op.create_index('ix_associates_manager_id', 'associates', ['manager_id'])
    op.create_index('ix_associates_associate_level_id', 'associates', ['associate_level_id'])
    op.create_index('ix_associates_performance_rating_id', 'associates', ['performance_rating_id'])
    op.create_index('ix_associates_is_people_manager', 'associates', ['is_people_manager'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_associates_is_people_manager', table_name='associates')
    op.drop_index('ix_associates_performance_rating_id', table_name='associates')
    op.drop_index('ix_associates_associate_level_id', table_name='associates')
    op.drop_index('ix_associates_manager_id', table_name='associates')

    # Drop tables in reverse order
    op.drop_table('associates')
    op.drop_table('performance_ratings')
    op.drop_table('associate_levels')
