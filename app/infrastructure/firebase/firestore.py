import logging
from typing import Optional

import requests
from requests import Session

from app.core.firestore_handler.FirestoreService import FirestoreService

logger = logging.getLogger(__name__)


class FirestoreAdapter:
    def __init__(self, project_id: str, api_key: str) -> None:
        self.projectId = project_id
        self.api_key = api_key
        self.requests: Session = requests.Session()
        for scheme in ("http://", "https://"):
            self.requests.mount(scheme, requests.adapters.HTTPAdapter(max_retries=3))
        self._database: Optional[FirestoreService] = None

    def database(self) -> FirestoreService:
        if self._database is None:
            self._database = FirestoreService(self)
        return self._database
