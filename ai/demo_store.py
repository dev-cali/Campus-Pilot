"""Isolated fictional SQLite storage. Never imports the shared database module."""

import argparse
from datetime import date
from pathlib import Path

from sqlalchemy import Column, ForeignKey, Integer, JSON, Text, create_engine, delete, event, select
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, declarative_base

from ai.document_eligibility import load_fictional_documents, process_documents


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = PROJECT_ROOT / ".campuspilot-demo" / "fictional.sqlite3"
DEFAULT_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "fictional_documents.json"
DemoBase = declarative_base()


class DemoDocument(DemoBase):
    """One complete validated fixture record, with a stable relational ID.

    JSON retains all source fields without inventing production schema mappings.
    Only the isolated demo adapter should write these records.
    """

    __tablename__ = "demo_documents"
    document_id = Column(Integer, primary_key=True)
    record = Column(JSON, nullable=False)


class DemoChunk(DemoBase):
    """Prepared public chunk snapshot; document/page/index form its identity."""

    __tablename__ = "demo_chunks"
    document_id = Column(Integer, ForeignKey("demo_documents.document_id"), primary_key=True)
    page_no = Column(Integer, primary_key=True)
    chunk_index = Column(Integer, primary_key=True)
    chunk_text = Column(Text, nullable=False)
    start_char = Column(Integer, nullable=False)
    end_char = Column(Integer, nullable=False)


class DemoStore:
    """A local-file-only store, independent of DATABASE_URL and Supabase.

    Construction creates only the SQLite engine. initialize() creates tables.
    Explicit disposal releases file handles, including on Windows.
    """

    def __init__(self, path: Path = DEFAULT_DATABASE):
        if not isinstance(path, Path):
            raise ValueError("demo_database_path_must_be_path")
        self.path = path.resolve()
        self.engine = create_engine(
            URL.create("sqlite+pysqlite", database=str(self.path)),
            echo=False,
        )

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(connection, _record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    def initialize(self) -> None:
        """Create the dedicated demo directory and tables, never shared tables."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        DemoBase.metadata.create_all(self.engine)

    def seed(self, documents: list, *, reference_date: date) -> tuple[int, int]:
        """Replace the demo catalog atomically after validating the whole input.

        Repeating the same seed does not duplicate records or chunks. Removed
        fixture records and their old chunks are removed from this demo only.
        Draft/restricted/revoked records are retained for policy checks, while
        only eligible public pages get prepared chunk rows.
        """
        if not isinstance(documents, list) or not documents:
            raise ValueError("invalid_demo_catalog")
        result = process_documents(
            documents, trusted_permissions={"public"}, reference_date=reference_date,
        )
        if any(d.reason in {"invalid_catalog", "invalid_reference_date"}
               for d in result.decisions):
            raise ValueError("invalid_demo_catalog")
        with Session(self.engine) as session, session.begin():
            session.execute(delete(DemoChunk))
            session.execute(delete(DemoDocument))
            session.add_all(
                DemoDocument(document_id=record["document_id"], record=record)
                for record in documents
            )
            session.flush()
            session.add_all(DemoChunk(
                document_id=chunk.document_id, page_no=chunk.page_no,
                chunk_index=chunk.chunk_index, chunk_text=chunk.chunk_text,
                start_char=chunk.start_char, end_char=chunk.end_char,
            ) for chunk in result.chunks)
        return len(documents), len(result.chunks)

    def load_documents(self) -> list:
        """Internal catalog read; never expose this list through a public route."""
        with Session(self.engine) as session:
            rows = session.scalars(select(DemoDocument).order_by(DemoDocument.document_id)).all()
            documents = []
            for row in rows:
                if not isinstance(row.record, dict) or row.record.get("document_id") != row.document_id:
                    raise ValueError("invalid_demo_catalog")
                documents.append(row.record)
            return documents

    def public_chunks(self, *, reference_date: date):
        """Revalidate stored records before returning any content for retrieval.

        Rebuild the tiny corpus through S3-01 instead of trusting a stale prepared
        chunk snapshot. No client-supplied permissions are accepted here.
        """
        result = process_documents(
            self.load_documents(), trusted_permissions={"public"}, reference_date=reference_date,
        )
        if any(d.reason in {"invalid_catalog", "invalid_reference_date"}
               for d in result.decisions):
            raise ValueError("invalid_demo_catalog")
        return result.chunks

    def close(self) -> None:
        self.engine.dispose()


def main() -> None:
    """Explicit local seed command; importing this module creates no database."""
    parser = argparse.ArgumentParser(description="Seed the fictional CampusPilot SQLite demo")
    parser.add_argument("--reference-date", required=True, type=date.fromisoformat)
    args = parser.parse_args()
    documents = load_fictional_documents(DEFAULT_FIXTURE)
    store = DemoStore()
    try:
        store.initialize()
        document_count, chunk_count = store.seed(documents, reference_date=args.reference_date)
        print(f"Fictional demo seeded: {document_count} documents, {chunk_count} public chunks.")
    finally:
        store.close()


if __name__ == "__main__":
    main()
