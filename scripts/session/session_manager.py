#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Session Manager for SAP ADT

Manages session state including cookies, CSRF tokens, and session persistence.
"""
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class SessionState:
    """
    Represents SAP ADT session state.

    Attributes:
        cookies: Session cookies
        csrf_token: Current CSRF token
        session_id: Unique session identifier
        created_at: Session creation timestamp
        last_used: Last activity timestamp
    """
    cookies: Dict[str, str] = field(default_factory=dict)
    csrf_token: Optional[str] = None
    session_id: str = ""
    created_at: float = field(default_factory=lambda: time.time())
    last_used: float = field(default_factory=lambda: time.time())

    def is_expired(self, timeout_seconds: int = 3600) -> bool:
        """
        Check if session has expired.

        Args:
            timeout_seconds: Session timeout in seconds (default: 1 hour)

        Returns:
            True if session expired
        """
        idle_time = time.time() - self.last_used
        return idle_time > timeout_seconds

    def touch(self) -> None:
        """Update last_used timestamp."""
        self.last_used = time.time()


class SessionManager:
    """
    Manager for SAP ADT sessions.

    Handles session creation, retrieval, and cleanup.
    """

    def __init__(self):
        self._sessions: Dict[str, SessionState] = {}

    def create_session(self, cookies: Dict[str, str] = None,
                     csrf_token: str = None) -> SessionState:
        """
        Create a new session.

        Args:
            cookies: Initial cookies from authentication
            csrf_token: Initial CSRF token

        Returns:
            SessionState instance
        """
        import uuid
        session_id = str(uuid.uuid4())

        session = SessionState(
            cookies=cookies or {},
            csrf_token=csrf_token,
            session_id=session_id
        )

        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[SessionState]:
        """
        Get existing session by ID.

        Args:
            session_id: Session identifier

        Returns:
            SessionState or None if not found
        """
        return self._sessions.get(session_id)

    def update_session(self, session_id: str, **kwargs) -> bool:
        """
        Update session attributes.

        Args:
            session_id: Session identifier
            **kwargs: Attributes to update (cookies, csrf_token, etc.)

        Returns:
            True if session exists and was updated
        """
        session = self._sessions.get(session_id)
        if session:
            for key, value in kwargs.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            session.touch()
            return True
        return False

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: Session identifier

        Returns:
            True if session was deleted
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def cleanup_expired(self, timeout_seconds: int = 3600) -> int:
        """
        Remove expired sessions.

        Args:
            timeout_seconds: Session timeout in seconds

        Returns:
            Number of sessions removed
        """
        expired_ids = [
            sid for sid, session in self._sessions.items()
            if session.is_expired(timeout_seconds)
        ]

        for sid in expired_ids:
            del self._sessions[sid]

        return len(expired_ids)

    def get_all_sessions(self) -> Dict[str, SessionState]:
        """
        Get all active sessions.

        Returns:
            Dict mapping session_id to SessionState
        """
        return self._sessions.copy()

    def session_count(self) -> int:
        """Get number of active sessions."""
        return len(self._sessions)
