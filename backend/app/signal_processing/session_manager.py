import time
import uuid
import logging
from typing import Dict, Optional, Any
from app.signal_processing.models import SignalData

logger = logging.getLogger("signalscope.session")

SESSION_TTL_SECONDS = 1800  # 30 minutes


class SignalSessionStore:
    """
    In-memory temporary signal session manager for local development.
    Associates a unique signal_id (UUID) with loaded SignalData instances.
    """

    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def create_session(self, signal_data: SignalData, filename: str) -> str:
        """
        Stores SignalData in memory and returns a generated signal_id.
        Automatically triggers cleanup of old expired sessions.
        """
        self.cleanup_expired_sessions()

        signal_id = str(uuid.uuid4())
        self._sessions[signal_id] = {
            "signal_data": signal_data,
            "filename": filename,
            "created_at": time.time()
        }
        logger.info(f"Created signal session {signal_id} for file '{filename}'.")
        return signal_id

    def get_session(self, signal_id: str) -> Optional[SignalData]:
        """
        Retrieves SignalData for a valid active signal_id.
        Returns None if missing or expired.
        """
        session = self._sessions.get(signal_id)
        if not session:
            return None

        # Check expiration
        if time.time() - session["created_at"] > SESSION_TTL_SECONDS:
            logger.info(f"Signal session {signal_id} expired. Cleaning up.")
            del self._sessions[signal_id]
            return None

        return session["signal_data"]

    def cleanup_expired_sessions(self):
        """
        Removes all sessions older than SESSION_TTL_SECONDS.
        """
        now = time.time()
        expired_ids = [
            sid for sid, data in self._sessions.items()
            if now - data["created_at"] > SESSION_TTL_SECONDS
        ]
        for sid in expired_ids:
            del self._sessions[sid]


# Global session manager instance
session_store = SignalSessionStore()
