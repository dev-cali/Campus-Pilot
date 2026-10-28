import os
import tempfile
import unittest
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base
import main
from main import app
from routers import documents, chunks, questions, users, ingest


class BackendCrudTests(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(self.db_fd)
        self.engine = create_engine(
            'sqlite:///' + self.db_path,
            connect_args={'check_same_thread': False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        def override_get_db():
            try:
                db = TestingSessionLocal()
                yield db
            finally:
                db.close()
        
        app.dependency_overrides[main.get_db] = override_get_db
        app.dependency_overrides[documents.get_db] = override_get_db
        app.dependency_overrides[chunks.get_db] = override_get_db
        app.dependency_overrides[questions.get_db] = override_get_db
        app.dependency_overrides[users.get_db] = override_get_db
        app.dependency_overrides[ingest.get_db] = override_get_db
        
        self.client = TestClient(app)
    
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
            'department_id': 1,
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
            'department_id': 1,
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
            'department_id': 1,
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
            'department_id': 1,
            'title': 'FAQ',
            'version': 'v1',
            'effective_date': '2026-01-01',
            'status': 'active'
        })
        doc_id = response.json()['id']
        
        # Create question
        response = self.client.post('/questions/', json={
            'user_id': user_id,
            'department_id': 1,
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
            'department_id': 1,
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
            'department_id': 1,
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


if __name__ == '__main__':
    unittest.main()
