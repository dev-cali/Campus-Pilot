import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from auth import get_current_user
from database import Base, Department, get_db
from main import app


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
    """SQLite ignores foreign keys unless asked; make the test database strict."""
    cursor = dbapi_connection.cursor()
    cursor.execute('PRAGMA foreign_keys=ON')
    cursor.close()


class BackendCrudTests(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(self.db_fd)
        self.engine = create_engine(
            'sqlite:///' + self.db_path,
            connect_args={'check_same_thread': False},
            poolclass=StaticPool,
        )
        event.listen(self.engine, 'connect', _enable_sqlite_foreign_keys)
        Base.metadata.create_all(bind=self.engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        def override_get_db():
            try:
                db = TestingSessionLocal()
                yield db
            finally:
                db.close()
        
        # All routers import the same get_db callable, so one override covers
        # the whole application.
        app.dependency_overrides[get_db] = override_get_db

        # These tests cover CRUD behaviour, not access control: act as staff and
        # let tests/test_auth.py exercise the 401/403 paths.
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
            id=1, name='Test Staff', email='staff@example.test', role='staff'
        )

        self.client = TestClient(app)

        # Documents and questions reference a department, so create a real one
        # instead of relying on foreign keys being silently ignored.
        session = TestingSessionLocal()
        department = Department(name='Test Department')
        session.add(department)
        session.commit()
        self.department_id = department.id
        session.close()
    
    def tearDown(self):
        app.dependency_overrides = {}
        self.client.close()
        self.engine.dispose()
        os.unlink(self.db_path)
    
    def test_health_endpoints_still_work(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('message', response.json())
        
        response = self.client.get('/departments')
        self.assertEqual(response.status_code, 200)
        self.assertIn('departments', response.json())
    
    def test_users_crud(self):
        # Create
        response = self.client.post('/users/', json={
            'name': 'Test User',
            'email': 'test@example.com',
            'role': 'student'
        })
        self.assertEqual(response.status_code, 200)
        user = response.json()
        self.assertEqual(user['name'], 'Test User')
        user_id = user['id']
        
        # Read all
        response = self.client.get('/users/')
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.json()), 1)
        
        # Read one
        response = self.client.get(f'/users/{user_id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['email'], 'test@example.com')
        
        # Delete
        response = self.client.delete(f'/users/{user_id}')
        self.assertEqual(response.status_code, 200)
        self.assertIn('message', response.json())
    
    def test_documents_crud(self):
        # Create document
        response = self.client.post('/documents/', json={
            'department_id': self.department_id,
            'title': 'Test Policy',
            'version': 'v1.0',
            'effective_date': '2026-01-01',
            'status': 'active'
        })
        self.assertEqual(response.status_code, 200)
        doc = response.json()
        doc_id = doc['id']
        
        # Read
        response = self.client.get(f'/documents/{doc_id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['title'], 'Test Policy')
        
        # Update
        response = self.client.put(f'/documents/{doc_id}', json={
            'department_id': self.department_id,
            'title': 'Updated Policy',
            'version': 'v1.1',
            'effective_date': '2026-02-01',
            'status': 'active'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['title'], 'Updated Policy')
        
        # Delete
        response = self.client.delete(f'/documents/{doc_id}')
        self.assertEqual(response.status_code, 200)
    
    def test_chunks_crud(self):
        # Create document first
        response = self.client.post('/documents/', json={
            'department_id': self.department_id,
            'title': 'Test Doc',
            'version': 'v1',
            'effective_date': '2026-01-01',
            'status': 'active'
        })
        doc_id = response.json()['id']
        
        # Create chunk
        response = self.client.post('/chunks/', json={
            'document_id': doc_id,
            'page_no': 1,
            'chunk_text': 'This is a test chunk.',
            'embedding': None
        })
        self.assertEqual(response.status_code, 200)
        chunk = response.json()
        chunk_id = chunk['id']
        
        # Read
        response = self.client.get(f'/chunks/{chunk_id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['chunk_text'], 'This is a test chunk.')
        
        # Filter by document
        response = self.client.get(f'/chunks/?document_id={doc_id}')
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.json()), 1)
        
        # Delete
        response = self.client.delete(f'/chunks/{chunk_id}')
        self.assertEqual(response.status_code, 200)
    
    def test_questions_crud(self):
        # Create dependencies
        response = self.client.post('/users/', json={
            'name': 'Student',
            'email': 'student@example.com',
            'role': 'student'
        })
        user_id = response.json()['id']
        
        response = self.client.post('/documents/', json={
            'department_id': self.department_id,
            'title': 'FAQ',
            'version': 'v1',
            'effective_date': '2026-01-01',
            'status': 'active'
        })
        doc_id = response.json()['id']
        
        # Create question
        response = self.client.post('/questions/', json={
            'user_id': user_id,
            'department_id': self.department_id,
            'query': 'What is the enrollment process?',
            'answer': 'You need to register online.',
            'citations': {'document_id': doc_id}
        })
        self.assertEqual(response.status_code, 200)
        question = response.json()
        question_id = question['id']
        
        # Read
        response = self.client.get(f'/questions/{question_id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['query'], 'What is the enrollment process?')
        
        # Delete
        response = self.client.delete(f'/questions/{question_id}')
        self.assertEqual(response.status_code, 200)
    
    def test_ingest_chunk_endpoint(self):
        # Create document first
        response = self.client.post('/documents/', json={
            'department_id': self.department_id,
            'title': 'Enrollment Guide',
            'version': 'v1.0',
            'effective_date': '2026-01-01',
            'status': 'active'
        })
        self.assertEqual(response.status_code, 200)
        doc_id = response.json()['id']
        
        # Ingest a page with text
        text = 'First paragraph.\n\nSecond paragraph with more information.'
        response = self.client.post('/ingest/chunk', json={
            'document_id': doc_id,
            'page_no': 1,
            'text': text,
            'source_reference': 'https://example.com/guide',
            'max_chars': 100
        })
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertIn('created', result)
        self.assertGreater(result['created'], 0)
        self.assertIn('chunks', result)
        
        # Verify chunks were saved to DB
        response = self.client.get(f'/chunks/?document_id={doc_id}')
        self.assertEqual(response.status_code, 200)
        chunks = response.json()
        self.assertGreater(len(chunks), 0)
        self.assertEqual(chunks[0]['document_id'], doc_id)
        self.assertEqual(chunks[0]['page_no'], 1)
    
    def test_ingest_chunk_document_not_found(self):
        response = self.client.post('/ingest/chunk', json={
            'document_id': 99999,
            'page_no': 1,
            'text': 'Some text',
            'source_reference': 'https://example.com/guide'
        })
        self.assertEqual(response.status_code, 404)
    
    def test_ingest_chunk_invalid_input(self):
        # Create document
        response = self.client.post('/documents/', json={
            'department_id': self.department_id,
            'title': 'Test',
            'version': 'v1',
            'effective_date': '2026-01-01',
            'status': 'active'
        })
        doc_id = response.json()['id']
        
        # Empty source reference should fail
        response = self.client.post('/ingest/chunk', json={
            'document_id': doc_id,
            'page_no': 1,
            'text': 'Some text',
            'source_reference': ''
        })
        self.assertEqual(response.status_code, 400)


    def test_get_missing_user_returns_404(self):
        response = self.client.get('/users/999999')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['detail'], 'User not found')

    def test_delete_missing_user_returns_404(self):
        response = self.client.delete('/users/999999')
        self.assertEqual(response.status_code, 404)

    def test_create_user_missing_email_returns_422(self):
        response = self.client.post('/users/', json={'name': 'No Email', 'role': 'student'})
        self.assertEqual(response.status_code, 422)

    def test_get_missing_document_returns_404(self):
        response = self.client.get('/documents/999999')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['detail'], 'Document not found')

    def test_update_missing_document_returns_404(self):
        response = self.client.put('/documents/999999', json={
            'department_id': self.department_id,
            'title': 'Missing Policy',
            'version': 'v1',
            'effective_date': '2026-01-01',
            'status': 'active'
        })
        self.assertEqual(response.status_code, 404)

    def test_update_document_persists_changes(self):
        created = self.client.post('/documents/', json={
            'department_id': self.department_id,
            'title': 'Original Title',
            'version': 'v1',
            'effective_date': '2026-01-01',
            'status': 'active'
        })
        doc_id = created.json()['id']

        updated = self.client.put(f'/documents/{doc_id}', json={
            'department_id': self.department_id,
            'title': 'Updated Title',
            'version': 'v2',
            'effective_date': '2026-03-01',
            'status': 'archived'
        })
        self.assertEqual(updated.status_code, 200)

        # Read it back to prove the update was committed, not just echoed.
        fetched = self.client.get(f'/documents/{doc_id}')
        self.assertEqual(fetched.json()['title'], 'Updated Title')
        self.assertEqual(fetched.json()['version'], 'v2')
        self.assertEqual(fetched.json()['status'], 'archived')

    def test_create_document_invalid_date_returns_422(self):
        response = self.client.post('/documents/', json={
            'department_id': self.department_id,
            'title': 'Bad Date Policy',
            'version': 'v1',
            'effective_date': 'not-a-date',
            'status': 'active'
        })
        self.assertEqual(response.status_code, 422)

    def test_get_document_non_integer_id_returns_422(self):
        response = self.client.get('/documents/not-a-number')
        self.assertEqual(response.status_code, 422)

    def test_delete_missing_document_returns_404(self):
        response = self.client.delete('/documents/999999')
        self.assertEqual(response.status_code, 404)

    def test_get_missing_chunk_returns_404(self):
        response = self.client.get('/chunks/999999')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['detail'], 'Chunk not found')

    def test_delete_missing_chunk_returns_404(self):
        response = self.client.delete('/chunks/999999')
        self.assertEqual(response.status_code, 404)

    def test_create_chunk_missing_text_returns_422(self):
        response = self.client.post('/chunks/', json={'document_id': 1, 'page_no': 1})
        self.assertEqual(response.status_code, 422)

    def test_chunk_filter_for_unknown_document_returns_empty_list(self):
        response = self.client.get('/chunks/?document_id=999999')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_get_missing_question_returns_404(self):
        response = self.client.get('/questions/999999')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['detail'], 'Question not found')

    def test_delete_missing_question_returns_404(self):
        response = self.client.delete('/questions/999999')
        self.assertEqual(response.status_code, 404)

    def test_create_question_missing_answer_returns_422(self):
        response = self.client.post('/questions/', json={
            'user_id': 1,
            'department_id': self.department_id,
            'query': 'Where is the library?'
        })
        self.assertEqual(response.status_code, 422)

    def test_create_duplicate_user_email_returns_409(self):
        payload = {
            'name': 'Fictional Student',
            'email': 'duplicate@example.test',
            'role': 'student'
        }
        first = self.client.post('/users/', json=payload)
        self.assertEqual(first.status_code, 200)

        second = self.client.post('/users/', json=payload)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()['detail'], 'A user with this email already exists')

        # The failed request must not leave a second row behind.
        self.assertEqual(len(self.client.get('/users/').json()), 1)

    def test_delete_document_with_chunks_removes_chunks(self):
        doc = self.client.post('/documents/', json={
            'department_id': self.department_id,
            'title': 'Document With Chunks',
            'version': 'v1',
            'effective_date': '2026-01-01',
            'status': 'active'
        }).json()
        chunk = self.client.post('/chunks/', json={
            'document_id': doc['id'],
            'page_no': 1,
            'chunk_text': 'Chunk that belongs to the document.'
        }).json()

        response = self.client.delete(f"/documents/{doc['id']}")
        self.assertEqual(response.status_code, 200)

        # The chunks must be gone with their parent, not orphaned or kept.
        self.assertEqual(self.client.get(f"/chunks/{chunk['id']}").status_code, 404)
        self.assertEqual(self.client.get(f"/chunks/?document_id={doc['id']}").json(), [])

    def test_create_document_unknown_department_returns_404(self):
        response = self.client.post('/documents/', json={
            'department_id': 999999,
            'title': 'Orphan Policy',
            'version': 'v1',
            'effective_date': '2026-01-01',
            'status': 'active'
        })
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['detail'], 'Department not found')

    def test_update_document_unknown_department_returns_404(self):
        doc = self.client.post('/documents/', json={
            'department_id': self.department_id,
            'title': 'Kept Title',
            'version': 'v1',
            'effective_date': '2026-01-01',
            'status': 'active'
        }).json()

        response = self.client.put(f"/documents/{doc['id']}", json={
            'department_id': 999999,
            'title': 'Rejected Title',
            'version': 'v2',
            'effective_date': '2026-02-01',
            'status': 'archived'
        })
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['detail'], 'Department not found')

        # A rejected update must not partially apply.
        self.assertEqual(self.client.get(f"/documents/{doc['id']}").json()['title'], 'Kept Title')

    def test_create_chunk_unknown_document_returns_404(self):
        response = self.client.post('/chunks/', json={
            'document_id': 999999,
            'page_no': 1,
            'chunk_text': 'Orphan chunk.'
        })
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['detail'], 'Document not found')

    def test_create_question_unknown_user_returns_404(self):
        response = self.client.post('/questions/', json={
            'user_id': 999999,
            'department_id': self.department_id,
            'query': 'Who am I?',
            'answer': 'Nobody.'
        })
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['detail'], 'User not found')

    def test_create_question_unknown_department_returns_404(self):
        user = self.client.post('/users/', json={
            'name': 'Fictional Student',
            'email': 'question-author@example.test',
            'role': 'student'
        }).json()

        response = self.client.post('/questions/', json={
            'user_id': user['id'],
            'department_id': 999999,
            'query': 'Where is the library?',
            'answer': 'Down the hall.'
        })
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['detail'], 'Department not found')


if __name__ == '__main__':
    unittest.main()
