import os
import logging
import firebase_admin
from firebase_admin import credentials, firestore
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockDocument:
    def __init__(self, data=None, exists=False, id=None):
        self._data = data or {}
        self.exists = exists
        self.id = id

    def to_dict(self):
        return self._data

class MockQueryReference:
    def __init__(self, collection_name, db, field, op, value):
        self.collection_name = collection_name
        self.db = db
        self.filters = [(field, op, value)]

    def where(self, field, op, value):
        self.filters.append((field, op, value))
        return self

    def get(self):
        docs = self.db.store.get(self.collection_name, {})
        results = []
        for k, data in docs.items():
            match = True
            for field, op, value in self.filters:
                val = data.get(field)
                if op == "==":
                    if val != value:
                        match = False
                        break
            if match:
                results.append(MockDocument(data, exists=True, id=k))
        return results

class MockCollectionReference:
    def __init__(self, name, db):
        self.name = name
        self.db = db

    def document(self, doc_id=None):
        if not doc_id:
            import uuid
            doc_id = str(uuid.uuid4())
        return MockDocumentReference(self.name, doc_id, self.db)

    def stream(self):
        docs = self.db.store.get(self.name, {})
        return [MockDocument(data, exists=True, id=k) for k, data in docs.items()]

    def get(self):
        return self.stream()

    def where(self, field, op, value):
        return MockQueryReference(self.name, self.db, field, op, value)

class MockDocumentReference:
    def __init__(self, collection_name, doc_id, db):
        self.collection_name = collection_name
        self.id = doc_id
        self.db = db

    def get(self):
        coll = self.db.store.get(self.collection_name, {})
        if self.id in coll:
            return MockDocument(coll[self.id], exists=True, id=self.id)
        return MockDocument(exists=False, id=self.id)

    def set(self, data, merge=False):
        if self.collection_name not in self.db.store:
            self.db.store[self.collection_name] = {}
        
        if merge and self.id in self.db.store[self.collection_name]:
            self.db.store[self.collection_name][self.id].update(data)
        else:
            self.db.store[self.collection_name][self.id] = data
        return self

    def update(self, data):
        return self.set(data, merge=True)

    def delete(self):
        if self.collection_name in self.db.store and self.id in self.db.store[self.collection_name]:
            del self.db.store[self.collection_name][self.id]

class MockFirestoreClient:
    def __init__(self):
        self.store = {}
        logger.warning("Initializing Mock Firestore Client. Data will NOT persist between restarts.")

    def collection(self, name):
        return MockCollectionReference(name, self)

def get_firestore_client():
    # 1. Prioritize key file located at backend/serviceAccountKey.json
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    service_key_path = os.path.join(base_dir, "serviceAccountKey.json")
    
    if os.path.exists(service_key_path):
        try:
            if not firebase_admin._apps:
                logger.info(f"Initializing Firebase with certificate file: {service_key_path}")
                cred = credentials.Certificate(service_key_path)
                firebase_admin.initialize_app(cred)
            return firestore.client()
        except Exception as e:
            logger.error(f"Failed to initialize Firestore with key at {service_key_path}: {e}")
            
    # 1.5 Support initializing from raw credentials JSON string in environment variable
    service_account_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
    if service_account_json:
        try:
            import json
            if not firebase_admin._apps:
                logger.info("Initializing Firebase using FIREBASE_SERVICE_ACCOUNT_JSON environment variable.")
                service_account_info = json.loads(service_account_json)
                cred = credentials.Certificate(service_account_info)
                firebase_admin.initialize_app(cred)
            return firestore.client()
        except Exception as e:
            logger.error(f"Failed to initialize Firestore with FIREBASE_SERVICE_ACCOUNT_JSON env: {e}")

    # 2. Fallbacks
    if os_credentials_exist := (os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or settings.firebase_service_account_path):
        try:
            if not firebase_admin._apps:
                if settings.firebase_service_account_path:
                    logger.info(f"Initializing Firebase with certificate settings path: {settings.firebase_service_account_path}")
                    cred = credentials.Certificate(settings.firebase_service_account_path)
                    firebase_admin.initialize_app(cred)
                else:
                    logger.info("Initializing Firebase with Application Default Credentials (ADC)")
                    firebase_admin.initialize_app()
            return firestore.client()
        except Exception as e:
            logger.error(f"Failed to initialize Firestore with credentials fallback: {e}. Falling back to in-memory mock database.")
            return MockFirestoreClient()
    else:
        logger.warning("No Firebase credentials configured in environment or settings. Using Mock Firestore.")
        return MockFirestoreClient()

# Export active client
db = get_firestore_client()
