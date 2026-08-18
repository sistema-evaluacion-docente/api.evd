"""rework improvement plan module for official ufps forms

Reshapes the Plan de Seguimiento Docente module around the three official UFPS
forms (Formato 1 "Casos de docentes reportados", Formato 2 "Ficha de acuerdo de
mejoramiento", Formato 3 "Plan seguimiento y mejoramiento"):

- plans gain the acta lifecycle (número/fecha/estado) and the free-text
  observation blocks the forms print; the old single-PDF acta columns move to
  ``improvement_plan_documents``
- items gain ``aspect`` (1-5, the sections of the forms) and ``commitment``
- new tables for the asignaturas table, the per-aspect follow-up cells, the
  cited student comments, the Formato 1 case report, the generated/signed PDFs,
  and the evidence request workflow

Revision ID: 06c9289cc329
Revises: a7a8337332ef
Create Date: 2026-08-12 22:48:54.232048

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '06c9289cc329'
down_revision: Union[str, Sequence[str], None] = 'a7a8337332ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_tables() -> set[str]:
    """Tables already present in the database.

    ``api/app.py`` calls ``Base.metadata.create_all()`` on startup, so any
    developer who boots the app before migrating already has these tables and a
    bare ``create_table`` would fail with DuplicateTable. See MIGRATIONS.md.
    """

    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    """Upgrade schema."""

    existing = _existing_tables()

    # --- Formato 1: caso reportado por el programa académico -----------------
    if "improvement_plan_case_reports" not in existing:
        op.create_table(
            'improvement_plan_case_reports',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('plan_id', sa.Integer(), nullable=False),
            sa.Column('reported_by', sa.Integer(), nullable=True),
            sa.Column('complaint', sa.Text(), nullable=True),
            sa.Column('observations', sa.Text(), nullable=True),
            sa.Column('committee_act_reference', sa.String(length=255), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['plan_id'], ['improvement_plans.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['reported_by'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_improvement_plan_case_reports_id'), 'improvement_plan_case_reports', ['id'], unique=False)
        op.create_index(op.f('ix_improvement_plan_case_reports_plan_id'), 'improvement_plan_case_reports', ['plan_id'], unique=True)

    # --- Asignaturas/grupos impresos en Formatos 2 y 3 -----------------------
    if "improvement_plan_courses" not in existing:
        op.create_table(
            'improvement_plan_courses',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('plan_id', sa.Integer(), nullable=False),
            sa.Column('academic_group_id', sa.Integer(), nullable=True),
            sa.Column('course_name', sa.String(length=255), nullable=False),
            sa.Column('course_code', sa.String(length=50), nullable=True),
            sa.Column('group_name', sa.String(length=50), nullable=True),
            sa.Column('program_name', sa.String(length=255), nullable=True),
            sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['academic_group_id'], ['academic_groups.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['plan_id'], ['improvement_plans.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_improvement_plan_courses_id'), 'improvement_plan_courses', ['id'], unique=False)
        op.create_index(op.f('ix_improvement_plan_courses_plan_id'), 'improvement_plan_courses', ['plan_id'], unique=False)

    # --- PDFs generados y firmados de los tres formatos ----------------------
    if "improvement_plan_documents" not in existing:
        op.create_table(
            'improvement_plan_documents',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('plan_id', sa.Integer(), nullable=False),
            sa.Column('format_type', sa.String(length=20), nullable=False),
            sa.Column('generated_pdf_url', sa.Text(), nullable=True),
            sa.Column('generated_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('generated_by', sa.Integer(), nullable=True),
            sa.Column('signed_pdf_url', sa.Text(), nullable=True),
            sa.Column('signed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('signed_by', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['generated_by'], ['users.id'], ),
            sa.ForeignKeyConstraint(['plan_id'], ['improvement_plans.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['signed_by'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('plan_id', 'format_type', name='uq_plan_document_format')
        )
        op.create_index(op.f('ix_improvement_plan_documents_id'), 'improvement_plan_documents', ['id'], unique=False)
        op.create_index(op.f('ix_improvement_plan_documents_plan_id'), 'improvement_plan_documents', ['plan_id'], unique=False)

    # --- Celdas por aspecto de la matriz de seguimiento (Formato 3) ----------
    if "improvement_plan_checkpoint_notes" not in existing:
        op.create_table(
            'improvement_plan_checkpoint_notes',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('checkpoint_id', sa.Integer(), nullable=False),
            sa.Column('aspect', sa.Integer(), nullable=False),
            sa.Column('note', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['checkpoint_id'], ['improvement_plan_checkpoints.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_improvement_plan_checkpoint_notes_checkpoint_id'), 'improvement_plan_checkpoint_notes', ['checkpoint_id'], unique=False)
        op.create_index(op.f('ix_improvement_plan_checkpoint_notes_id'), 'improvement_plan_checkpoint_notes', ['id'], unique=False)

    # --- Solicitudes de evidencia + hilo de comentarios ----------------------
    if "improvement_plan_evidence_requests" not in existing:
        op.create_table(
            'improvement_plan_evidence_requests',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('plan_id', sa.Integer(), nullable=False),
            sa.Column('item_id', sa.Integer(), nullable=True),
            sa.Column('requested_by', sa.Integer(), nullable=True),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('status', sa.String(length=20), nullable=False, server_default='PENDIENTE'),
            sa.Column('due_date', sa.Date(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['item_id'], ['improvement_plan_items.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['plan_id'], ['improvement_plans.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['requested_by'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_improvement_plan_evidence_requests_id'), 'improvement_plan_evidence_requests', ['id'], unique=False)
        op.create_index(op.f('ix_improvement_plan_evidence_requests_plan_id'), 'improvement_plan_evidence_requests', ['plan_id'], unique=False)

    if "improvement_plan_evidence_comments" not in existing:
        op.create_table(
            'improvement_plan_evidence_comments',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('request_id', sa.Integer(), nullable=False),
            sa.Column('author_id', sa.Integer(), nullable=True),
            sa.Column('body', sa.Text(), nullable=False),
            sa.Column('is_system', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['author_id'], ['users.id'], ),
            sa.ForeignKeyConstraint(['request_id'], ['improvement_plan_evidence_requests.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_improvement_plan_evidence_comments_id'), 'improvement_plan_evidence_comments', ['id'], unique=False)
        op.create_index(op.f('ix_improvement_plan_evidence_comments_request_id'), 'improvement_plan_evidence_comments', ['request_id'], unique=False)

    # --- Comentarios estudiantiles citados como justificación ----------------
    if "improvement_plan_item_comments" not in existing:
        op.create_table(
            'improvement_plan_item_comments',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('item_id', sa.Integer(), nullable=False),
            sa.Column('comment_id', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['comment_id'], ['comments.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['item_id'], ['improvement_plan_items.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('item_id', 'comment_id', name='uq_plan_item_comment')
        )
        op.create_index(op.f('ix_improvement_plan_item_comments_comment_id'), 'improvement_plan_item_comments', ['comment_id'], unique=False)
        op.create_index(op.f('ix_improvement_plan_item_comments_id'), 'improvement_plan_item_comments', ['id'], unique=False)
        op.create_index(op.f('ix_improvement_plan_item_comments_item_id'), 'improvement_plan_item_comments', ['item_id'], unique=False)

    # --- Evidencias: enlace a la solicitud + estado de revisión --------------
    # server_default on the NOT NULL column so the ALTER also works on databases
    # that already hold evidence rows.
    op.add_column('improvement_plan_evidences', sa.Column('request_id', sa.Integer(), nullable=True))
    op.add_column('improvement_plan_evidences', sa.Column('status', sa.String(length=20), nullable=False, server_default='PENDIENTE'))
    op.add_column('improvement_plan_evidences', sa.Column('reviewed_by', sa.Integer(), nullable=True))
    op.add_column('improvement_plan_evidences', sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_improvement_plan_evidences_request_id'), 'improvement_plan_evidences', ['request_id'], unique=False)
    op.create_foreign_key('fk_plan_evidences_reviewed_by_users', 'improvement_plan_evidences', 'users', ['reviewed_by'], ['id'])
    op.create_foreign_key('fk_plan_evidences_request_id_requests', 'improvement_plan_evidences', 'improvement_plan_evidence_requests', ['request_id'], ['id'], ondelete='SET NULL')

    # --- Items: aspecto del formato + compromiso -----------------------------
    op.add_column('improvement_plan_items', sa.Column('commitment', sa.Text(), nullable=True))
    op.add_column('improvement_plan_items', sa.Column('aspect', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_improvement_plan_items_aspect'), 'improvement_plan_items', ['aspect'], unique=False)

    # --- Planes: acta (número/fecha/ciclo de vida) y observaciones -----------
    op.add_column('improvement_plans', sa.Column('program_name', sa.String(length=255), nullable=True))
    op.add_column('improvement_plans', sa.Column('acta_number', sa.String(length=50), nullable=True))
    op.add_column('improvement_plans', sa.Column('acta_date', sa.Date(), nullable=True))
    op.add_column('improvement_plans', sa.Column('acta_status', sa.String(length=20), nullable=False, server_default='BORRADOR'))
    op.add_column('improvement_plans', sa.Column('acta_closed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('improvement_plans', sa.Column('acta_closed_by', sa.Integer(), nullable=True))
    op.add_column('improvement_plans', sa.Column('council_observations', sa.Text(), nullable=True))
    op.add_column('improvement_plans', sa.Column('department_director_observations', sa.Text(), nullable=True))
    op.add_column('improvement_plans', sa.Column('program_director_observations', sa.Text(), nullable=True))
    op.create_foreign_key('fk_improvement_plans_acta_closed_by_users', 'improvement_plans', 'users', ['acta_closed_by'], ['id'])

    # Superseded by improvement_plan_documents (FORMATO_2).
    op.drop_column('improvement_plans', 'acta_uploaded_at')
    op.drop_column('improvement_plans', 'acta_description')
    op.drop_column('improvement_plans', 'acta_pdf_url')


def downgrade() -> None:
    """Downgrade schema."""

    op.add_column('improvement_plans', sa.Column('acta_pdf_url', sa.TEXT(), autoincrement=False, nullable=True))
    op.add_column('improvement_plans', sa.Column('acta_description', sa.TEXT(), autoincrement=False, nullable=True))
    op.add_column('improvement_plans', sa.Column('acta_uploaded_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True))
    op.drop_constraint('fk_improvement_plans_acta_closed_by_users', 'improvement_plans', type_='foreignkey')
    op.drop_column('improvement_plans', 'program_director_observations')
    op.drop_column('improvement_plans', 'department_director_observations')
    op.drop_column('improvement_plans', 'council_observations')
    op.drop_column('improvement_plans', 'acta_closed_by')
    op.drop_column('improvement_plans', 'acta_closed_at')
    op.drop_column('improvement_plans', 'acta_status')
    op.drop_column('improvement_plans', 'acta_date')
    op.drop_column('improvement_plans', 'acta_number')
    op.drop_column('improvement_plans', 'program_name')

    op.drop_index(op.f('ix_improvement_plan_items_aspect'), table_name='improvement_plan_items')
    op.drop_column('improvement_plan_items', 'aspect')
    op.drop_column('improvement_plan_items', 'commitment')

    op.drop_constraint('fk_plan_evidences_request_id_requests', 'improvement_plan_evidences', type_='foreignkey')
    op.drop_constraint('fk_plan_evidences_reviewed_by_users', 'improvement_plan_evidences', type_='foreignkey')
    op.drop_index(op.f('ix_improvement_plan_evidences_request_id'), table_name='improvement_plan_evidences')
    op.drop_column('improvement_plan_evidences', 'reviewed_at')
    op.drop_column('improvement_plan_evidences', 'reviewed_by')
    op.drop_column('improvement_plan_evidences', 'status')
    op.drop_column('improvement_plan_evidences', 'request_id')

    op.drop_index(op.f('ix_improvement_plan_evidence_comments_request_id'), table_name='improvement_plan_evidence_comments')
    op.drop_index(op.f('ix_improvement_plan_evidence_comments_id'), table_name='improvement_plan_evidence_comments')
    op.drop_table('improvement_plan_evidence_comments')
    op.drop_index(op.f('ix_improvement_plan_item_comments_item_id'), table_name='improvement_plan_item_comments')
    op.drop_index(op.f('ix_improvement_plan_item_comments_id'), table_name='improvement_plan_item_comments')
    op.drop_index(op.f('ix_improvement_plan_item_comments_comment_id'), table_name='improvement_plan_item_comments')
    op.drop_table('improvement_plan_item_comments')
    op.drop_index(op.f('ix_improvement_plan_evidence_requests_plan_id'), table_name='improvement_plan_evidence_requests')
    op.drop_index(op.f('ix_improvement_plan_evidence_requests_id'), table_name='improvement_plan_evidence_requests')
    op.drop_table('improvement_plan_evidence_requests')
    op.drop_index(op.f('ix_improvement_plan_checkpoint_notes_id'), table_name='improvement_plan_checkpoint_notes')
    op.drop_index(op.f('ix_improvement_plan_checkpoint_notes_checkpoint_id'), table_name='improvement_plan_checkpoint_notes')
    op.drop_table('improvement_plan_checkpoint_notes')
    op.drop_index(op.f('ix_improvement_plan_documents_plan_id'), table_name='improvement_plan_documents')
    op.drop_index(op.f('ix_improvement_plan_documents_id'), table_name='improvement_plan_documents')
    op.drop_table('improvement_plan_documents')
    op.drop_index(op.f('ix_improvement_plan_courses_plan_id'), table_name='improvement_plan_courses')
    op.drop_index(op.f('ix_improvement_plan_courses_id'), table_name='improvement_plan_courses')
    op.drop_table('improvement_plan_courses')
    op.drop_index(op.f('ix_improvement_plan_case_reports_plan_id'), table_name='improvement_plan_case_reports')
    op.drop_index(op.f('ix_improvement_plan_case_reports_id'), table_name='improvement_plan_case_reports')
    op.drop_table('improvement_plan_case_reports')
