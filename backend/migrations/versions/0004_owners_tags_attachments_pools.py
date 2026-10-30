"""job owners and tags, applicant owners and attachments, hire date, talent pools

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-30 12:02:24.399626

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel  # noqa: F401  (autogenerate writes sqlmodel.AutoString)


# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, Sequence[str], None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('talent_pool',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('applicant_attachment',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('applicant_id', sa.Integer(), nullable=False),
    sa.Column('filename', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('stored_path', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('content_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('size', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['applicant_id'], ['applicant.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('applicant_attachment', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_applicant_attachment_applicant_id'), ['applicant_id'], unique=False)

    op.create_table('talent_pool_member',
    sa.Column('pool_id', sa.Integer(), nullable=False),
    sa.Column('applicant_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['applicant_id'], ['applicant.id'], ),
    sa.ForeignKeyConstraint(['pool_id'], ['talent_pool.id'], ),
    sa.PrimaryKeyConstraint('pool_id', 'applicant_id')
    )
    with op.batch_alter_table('applicant', schema=None) as batch_op:
        batch_op.add_column(sa.Column('next_action_user_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('hired_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index(batch_op.f('ix_applicant_user_id'), ['user_id'], unique=False)
        batch_op.create_foreign_key('fk_applicant_next_action_user_id', 'app_user', ['next_action_user_id'], ['id'])
        batch_op.create_foreign_key('fk_applicant_user_id', 'app_user', ['user_id'], ['id'])

    with op.batch_alter_table('job', schema=None) as batch_op:
        batch_op.add_column(sa.Column('recruiter_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('manager_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('tags', sa.JSON(), nullable=False, server_default='[]'))
        batch_op.create_foreign_key('fk_job_manager_id', 'app_user', ['manager_id'], ['id'])
        batch_op.create_foreign_key('fk_job_recruiter_id', 'app_user', ['recruiter_id'], ['id'])



def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('job', schema=None) as batch_op:
        batch_op.drop_column('tags')
        batch_op.drop_column('manager_id')
        batch_op.drop_column('recruiter_id')

    with op.batch_alter_table('applicant', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_applicant_user_id'))
        batch_op.drop_column('hired_at')
        batch_op.drop_column('user_id')
        batch_op.drop_column('next_action_user_id')

    op.drop_table('talent_pool_member')
    with op.batch_alter_table('applicant_attachment', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_applicant_attachment_applicant_id'))

    op.drop_table('applicant_attachment')
    op.drop_table('talent_pool')
