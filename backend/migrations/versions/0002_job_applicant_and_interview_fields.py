"""job, applicant and interview fields

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-30 10:46:44.791003

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel  # noqa: F401  (autogenerate writes sqlmodel.AutoString)


# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Postgres needs the enum types created before columns use them (no-op on SQLite).
REFUSEREASON = sa.Enum('does_not_fit', 'refused_job_fit', 'refused_salary', 'job_filled', 'duplicate', 'spam', name='refusereason')
INTERVIEWSTATUS = sa.Enum('scheduled', 'done', 'no_show', 'cancelled', name='interviewstatus')
RECOMMENDATION = sa.Enum('hire', 'maybe', 'no_hire', name='recommendation')
EMPLOYMENTTYPE = sa.Enum('full_time', 'part_time', 'internship', 'contract', name='employmenttype')
ENUMS = (REFUSEREASON, INTERVIEWSTATUS, RECOMMENDATION, EMPLOYMENTTYPE)

# server_default fills existing rows; the app always sends its own values.
def upgrade() -> None:
    """Upgrade schema."""
    for enum in ENUMS:
        enum.create(op.get_bind(), checkfirst=True)
    with op.batch_alter_table('applicant', schema=None) as batch_op:
        batch_op.add_column(sa.Column('linkedin', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('short_intro', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('notes', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('priority', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('tags', sa.JSON(), nullable=False, server_default='[]'))
        batch_op.add_column(sa.Column('available_from', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('degree', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('salary_expected', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('salary_proposed', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('archived', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('refuse_reason', REFUSEREASON, nullable=True))
        batch_op.add_column(sa.Column('refused_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('stage_changed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))

    with op.batch_alter_table('interview', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', INTERVIEWSTATUS, nullable=False, server_default='scheduled'))
        batch_op.add_column(sa.Column('sequence', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('score', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('recommendation', RECOMMENDATION, nullable=True))
        batch_op.add_column(sa.Column('feedback', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''))

    with op.batch_alter_table('job', schema=None) as batch_op:
        batch_op.add_column(sa.Column('opens_on', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('closes_on', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('employment_type', EMPLOYMENTTYPE, nullable=False, server_default='full_time'))
        batch_op.add_column(sa.Column('is_remote', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('salary_min', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('salary_max', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('expected_degree', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''))



def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('job', schema=None) as batch_op:
        batch_op.drop_column('expected_degree')
        batch_op.drop_column('salary_max')
        batch_op.drop_column('salary_min')
        batch_op.drop_column('is_remote')
        batch_op.drop_column('employment_type')
        batch_op.drop_column('closes_on')
        batch_op.drop_column('opens_on')

    with op.batch_alter_table('interview', schema=None) as batch_op:
        batch_op.drop_column('feedback')
        batch_op.drop_column('recommendation')
        batch_op.drop_column('score')
        batch_op.drop_column('sequence')
        batch_op.drop_column('status')

    with op.batch_alter_table('applicant', schema=None) as batch_op:
        batch_op.drop_column('stage_changed_at')
        batch_op.drop_column('refused_at')
        batch_op.drop_column('refuse_reason')
        batch_op.drop_column('archived')
        batch_op.drop_column('salary_proposed')
        batch_op.drop_column('salary_expected')
        batch_op.drop_column('degree')
        batch_op.drop_column('available_from')
        batch_op.drop_column('tags')
        batch_op.drop_column('priority')
        batch_op.drop_column('notes')
        batch_op.drop_column('short_intro')
        batch_op.drop_column('linkedin')

    for enum in ENUMS:
        enum.drop(op.get_bind(), checkfirst=True)
