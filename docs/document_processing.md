# S2-03: Document processing and RAG preparation

## Purpose and scope

Retrieval needs short passages that can be traced back to university sources.
This component splits **already-extracted text from one page** into ordered
passages. It does not extract PDFs, access a database, check source approval,
generate embeddings, call an AI provider, or connect to Pinecone.

## Files

- [Package marker](../ai/__init__.py): identifies the AI Python package.
- [Processing code](../ai/document_processing.py): normalization, validation,
  chunk results, and splitting.
- [Tests](../tests/test_document_processing.py): offline built-in unittest checks.
- [Fictional fixture](../tests/fixtures/sample_university_document.txt): invented
  university content for tests; never use it as approved university evidence.

## Example

Run Python from the repository root so it can find the `ai` package:

```python
from ai.document_processing import split_document_text

chunks = split_document_text(
    "Fictional enrollment guidance.\n\nMore fictional guidance.",
    document_id=17,
    page_no=1,
    source_reference="https://example.invalid/fictional-guide",
    title="Fictional Enrollment Guide",
    version="test-v1",
    max_chars=40,
)
for chunk in chunks:
    print(chunk.chunk_index, chunk.chunk_text)
```

The example contains only fictional public test content. Production code should
not print private documents or credentials.

## Input and output contract

Call `split_document_text` once per extracted page. `document_id` and `page_no`
are positive integers; page numbers are one-based. Do not concatenate different
pages and assign them one page number. A future ingestion adapter must agree on
a page convention for sources without physical pages rather than inventing one.

`source_reference` and `title` are required nonblank strings. The source reference
can be an original resource URL or a stable storage reference; this function
does not verify it or access it. `version` is optional (`None` by default), but
must be a nonblank string when provided. All metadata is copied exactly.
`max_chars` is a positive integer, defaulting to 1000. Booleans are rejected as
integer inputs even though Python normally treats them as integers.

Each returned immutable `DocumentChunk` contains these metadata fields plus:

- `chunk_index`: zero-based position within this call, not a database ID.
- `chunk_text`: nonblank passage with no surrounding whitespace.
- `start_char`, `end_char`: positions in the **normalized** page text; the start
  is included and the end is excluded, following Python string slicing.

This result class is independent of the SQLAlchemy class with the same name.
Import it from `ai.document_processing`, not from the database module.

## How splitting works

1. `normalize_document_text` converts Windows and old-style line endings to
   newlines. It collapses whitespace within a paragraph to a single space and
   preserves blank-line paragraph boundaries as two newlines. It preserves
   non-whitespace characters, their case, punctuation, and order.
2. `split_document_text` checks all inputs, including when text is empty.
3. It takes a window no larger than `max_chars`, preferring a paragraph boundary
   inside an overflowing window. Otherwise it uses a whitespace boundary where
   necessary to avoid splitting a word.
4. If a word is too long, it cuts that word at the character limit. This ensures
   progress even for long URLs or text without spaces.
5. It copies metadata and records offsets and order for each passage.

Empty or whitespace-only text returns `[]`. Wrong types raise `TypeError`;
invalid values raise `ValueError`. Bytes must be decoded by the caller before
processing. Plain text cannot reliably tell us whether content came from an
unsupported file or a failed extraction; the future extraction layer must
validate formats and extraction quality. Missing required arguments also raise
Python's normal `TypeError`.

Only whitespace at chunk boundaries may be omitted. Joining chunk strings with
a space is **not** a lossless reconstruction: a long word might have been split.
Use offsets into `normalize_document_text(original_text)` to recover exact
placement and paragraph separators. There is no overlap or duplicated content.

The character limit counts Python Unicode code points, not bytes, visual letters,
or model tokens. A hard cut can separate a combining character or emoji sequence.
Normalization is intended for prose, not layout-sensitive tables or code. There
is no sentence parser, OCR repair, dehyphenation, or automatic content correction.

## Tests

From the repository root:

```powershell
python -B -m unittest discover -s tests -v
```

`-B` prevents Python from creating bytecode cache files. `unittest` discovers the
test module and runs its checks. No extra dependencies, network, credentials,
database access, or paid AI calls are needed.

Tests cover fictional documents, whitespace normalization, blank input, missing
metadata, incorrect types, invalid values, long paragraphs, oversized words,
Unicode, metadata preservation, exact character limits, and deterministic order.
Completeness checks verify that offsets match the source, gaps contain only
whitespace, and all meaningful characters remain in the original order. Limits
from one character upward exercise difficult boundary cases.

## Future integration and ownership

The current [database models](../database.py) provide document metadata and chunk
fields, but no document content location or source-reference field. Coordinate
with Brian before adding a source-storage contract or changing the schema.

An eventual backend adapter should load an approved document, extract pages,
call this function per page, and save each result's `document_id`, `page_no`, and
`chunk_text` to the existing chunk model. Title and version belong to the parent
document. Source references, ordering/offset storage, reprocessing, and removal
of obsolete chunks need an agreed persistence design. No database writes are
implemented here.

For Sprint 3, confirm the team's embedding provider/model and its token limit.
Generate an embedding (a numeric representation for similarity search) for each
passage, and index it in Pinecone using stable persisted identifiers and citation
metadata. The local `chunk_index` resets per page and is not a globally unique
Pinecone ID. Do not assume the database's optional text embedding field defines
the future vector-storage design.

Retrieval can then return relevant passages with document and source references.
Approval, effective dates, version currency, and sufficient evidence must be
checked by later stages: a nonempty source reference is not proof of approval,
and an effective date is not proof that a document is still current. User-facing
answers should cite original university resources and explain missing evidence.

Coordinate adding the test command to CI with Cassie. This task leaves existing
backend endpoints, database configuration, frontend, dependencies, and CI intact.
