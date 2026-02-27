from typing import Any, Dict

from .credentials import Certificate

class App:
    credential: Any

_apps: Dict[str, App]

def initialize_app(cred: Certificate) -> App: ...
def get_app() -> App: ...
