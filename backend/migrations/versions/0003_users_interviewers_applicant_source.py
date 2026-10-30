"""users, job interviewers, applicant source and next action

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-30 11:19:23.462982

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel  # noqa: F401  (autogenerate writes sqlmodel.AutoString)


# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Postgres needs the enum type before the column uses it; create_table makes `role` itself.
SOURCE = sa.Enum('careers_site', 'linkedin', 'referral', 'job_board', 'other', name='source')

# server_default fills existing applicants.
def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('app_user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('role', sa.Enum('admin', 'recruiter', 'interviewer', name='role'), nullable=False),
    sa.Column('password_hash', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('app_user', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_app_user_email'), ['email'], unique=True)

    op.create_table('job_interviewer',
    sa.Column('job_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['job_id'], ['job.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['app_user.id'], ),
    sa.PrimaryKeyConstraint('job_id', 'user_id')
    )
    SOURCE.create(op.get_bind(), checkfirst=True)
    with op.batch_alter_table('applicant', schema=None) as batch_op:
        batch_op.add_column(sa.Column('source', SOURCE, nullable=False, server_default='careers_site'))
        batch_op.add_column(sa.Column('source_detail', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('next_action', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('next_action_due', sa.Date(), nullable=True))



def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('applicant', schema=None) as batch_op:
        batch_op.drop_column('next_action_due')
        batch_op.drop_column('next_action')
        batch_op.drop_column('source_detail')
        batch_op.drop_column('source')

    op.drop_table('job_interviewer')
    with op.batch_alter_table('app_user', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_app_user_email'))

    op.drop_table('app_user')
    SOURCE.drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='role').drop(op.get_bind(), checkfirst=True)
