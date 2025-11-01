"""
Configuration management for the client
"""
import json
import os
from pathlib import Path
from typing import Optional


class Config:
    """Client configuration"""

    def __init__(self, config_dir: str = None):
        if config_dir is None:
            config_dir = os.path.expanduser("~/.hiring-client")

        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.config_file = self.config_dir / "config.json"
        self.db_file = self.config_dir / "local.db"

        self.data = self._load()

    def _load(self) -> dict:
        """Load configuration from file"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {}

    def save(self):
        """Save configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.data, f, indent=2)

    @property
    def server_url(self) -> str:
        return self.data.get('server_url', 'http://localhost:8000/api')

    @server_url.setter
    def server_url(self, value: str):
        self.data['server_url'] = value
        self.save()

    @property
    def encryption_key(self) -> Optional[str]:
        return self.data.get('encryption_key')

    @encryption_key.setter
    def encryption_key(self, value: str):
        self.data['encryption_key'] = value
        self.save()

    @property
    def last_sync(self) -> Optional[str]:
        """Last sync timestamp (ISO format)"""
        return self.data.get('last_sync')

    @last_sync.setter
    def last_sync(self, value: str):
        self.data['last_sync'] = value
        self.save()

    @property
    def schema_version(self) -> int:
        """Current schema version"""
        return self.data.get('schema_version', 1)

    @schema_version.setter
    def schema_version(self, value: int):
        self.data['schema_version'] = value
        self.save()

    def is_initialized(self) -> bool:
        """Check if client is initialized"""
        return self.encryption_key is not None
