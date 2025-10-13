"""Add distribution buckets and rating exclusion support

Revision ID: 002
Revises: 001
Create Date: 2025-10-13

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # Create distribution_buckets table
    op.create_table(
        'distribution_buckets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('min_percentage', sa.Float(), nullable=False),
        sa.Column('max_percentage', sa.Float(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.CheckConstraint('min_percentage >= 0 AND min_percentage <= 100',
                          name='min_percentage_valid'),
        sa.CheckConstraint('max_percentage >= 0 AND max_percentage <= 100',
                          name='max_percentage_valid'),
        sa.CheckConstraint('min_percentage <= max_percentage',
                          name='min_less_than_max'),
    )

    # Use batch mode for SQLite to add columns and foreign key
    with op.batch_alter_table('performance_ratings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('excluded_from_distribution', sa.Boolean(),
                                      nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('distribution_bucket_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_performance_rating_distribution_bucket',
            'distribution_buckets',
            ['distribution_bucket_id'], ['id'],
            ondelete='SET NULL'
        )


def downgrade():
    # Use batch mode for SQLite to remove columns and foreign key
    with op.batch_alter_table('performance_ratings', schema=None) as batch_op:
        batch_op.drop_constraint('fk_performance_rating_distribution_bucket', type_='foreignkey')
        batch_op.drop_column('distribution_bucket_id')
        batch_op.drop_column('excluded_from_distribution')

    # Drop distribution_buckets table
    op.drop_table('distribution_buckets')
