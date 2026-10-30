"""mail templates, stored files, google calendar, slot proposals

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-30 13:59:48.540442

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import secrets

import sqlmodel  # noqa: F401  (autogenerate writes sqlmodel.AutoString)
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: Union[str, Sequence[str], None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# `stage` already exists (0001); the two new enums are created / dropped here explicitly.
STAGE = postgresql.ENUM('new', 'screening', 'interview', 'offer', 'hired', 'rejected', name='stage', create_type=False)
CANDIDATE_RESPONSE = sa.Enum('none', 'accepted', 'declined', name='candidateresponse')


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('mail_template',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('key', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''),
    sa.Column('subject', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''),
    sa.Column('body', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''),
    sa.Column('stage', STAGE, nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('key')
    )
    op.create_table('stored_file',
    sa.Column('id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('filename', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('content_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('size', sa.Integer(), nullable=False),
    sa.Column('data', sa.LargeBinary(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('google_credential',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('refresh_token', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('email', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['app_user.id'], ),
    sa.PrimaryKeyConstraint('user_id')
    )
    op.create_table('slot_proposal',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('token', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('applicant_id', sa.Integer(), nullable=False),
    sa.Column('interviewer_id', sa.Integer(), nullable=False),
    sa.Column('slots', sa.JSON(), nullable=False),
    sa.Column('location', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''),
    sa.Column('status', sa.Enum('open', 'booked', 'expired', name='proposalstatus'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['applicant_id'], ['applicant.id'], ),
    sa.ForeignKeyConstraint(['interviewer_id'], ['app_user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('slot_proposal', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_slot_proposal_applicant_id'), ['applicant_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_slot_proposal_token'), ['token'], unique=True)

    CANDIDATE_RESPONSE.create(op.get_bind(), checkfirst=True)
    with op.batch_alter_table('interview', schema=None) as batch_op:
        batch_op.add_column(sa.Column('google_event_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('meet_url', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('response_token', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
        batch_op.add_column(sa.Column('candidate_response', CANDIDATE_RESPONSE, nullable=False, server_default='none'))
    # Existing interviews need their own unique token before the column becomes NOT NULL + unique.
    bind = op.get_bind()
    for (interview_id,) in bind.execute(sa.text('SELECT id FROM interview')).all():
        bind.execute(sa.text('UPDATE interview SET response_token = :t WHERE id = :i'),
                     {'t': secrets.token_urlsafe(24), 'i': interview_id})
    with op.batch_alter_table('interview', schema=None) as batch_op:
        batch_op.alter_column('response_token', existing_type=sqlmodel.sql.sqltypes.AutoString(), nullable=False)
        batch_op.create_index(batch_op.f('ix_interview_response_token'), ['response_token'], unique=True)



def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('interview', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_interview_response_token'))
        batch_op.drop_column('candidate_response')
        batch_op.drop_column('response_token')
        batch_op.drop_column('meet_url')
        batch_op.drop_column('google_event_id')

    with op.batch_alter_table('slot_proposal', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_slot_proposal_token'))
        batch_op.drop_index(batch_op.f('ix_slot_proposal_applicant_id'))

    op.drop_table('slot_proposal')
    op.drop_table('google_credential')
    op.drop_table('stored_file')
    op.drop_table('mail_template')
    CANDIDATE_RESPONSE.drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='proposalstatus').drop(op.get_bind(), checkfirst=True)
