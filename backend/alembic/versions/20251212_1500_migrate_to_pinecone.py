"""Migrate from pgvector to Pinecone - add pinecone_id, remove embedding column.

Revision ID: migrate_to_pinecone
Revises: fef62c2b46e1
Create Date: 2025-12-12 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'migrate_to_pinecone'
down_revision: Union[str, None] = 'fef62c2b46e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add pinecone_id column to document_chunks
    op.add_column(
        'document_chunks',
        sa.Column('pinecone_id', sa.String(255), nullable=True)
    )
    
    # Create index on pinecone_id
    op.create_index(
        'ix_document_chunks_pinecone_id',
        'document_chunks',
        ['pinecone_id']
    )
    
    # Drop the embedding index (if exists)
    try:
        op.drop_index('ix_document_chunks_embedding', table_name='document_chunks')
    except Exception:
        pass  # Index might not exist
    
    # Drop the embedding column (vectors now stored in Pinecone)
    try:
        op.drop_column('document_chunks', 'embedding')
    except Exception:
        pass  # Column might not exist


def downgrade() -> None:
    # Re-add embedding column (requires pgvector extension)
    # Note: This will lose all vector data as it's now in Pinecone
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.add_column(
        'document_chunks',
        sa.Column('embedding', sa.dialects.postgresql.ARRAY(sa.Float()), nullable=True)
    )
    
    # Drop pinecone_id index
    op.drop_index('ix_document_chunks_pinecone_id', table_name='document_chunks')
    
    # Drop pinecone_id column
    op.drop_column('document_chunks', 'pinecone_id')
