#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lock Manager for SAP ADT Objects

Manages object locks for editing operations.
Follows SAP's lock/unlock pattern for safe object modification.
"""
import time
import uuid
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class LockStatus(Enum):
    """Lock status values."""
    LOCKED = "LOCKED"
    UNLOCKED = "UNLOCKED"
    ERROR = "ERROR"


@dataclass
class LockInfo:
    """
    Information about an object lock.

    Attributes:
        object_name: Name of the locked object
        object_type: Type of the locked object (class, table, etc.)
        lock_handle: Unique lock identifier
        lock_owner: User/session who owns the lock
        locked_at: Timestamp when lock was acquired
        status: Current lock status
    """
    object_name: str
    object_type: str
    lock_handle: str = ""
    lock_owner: str = ""
    locked_at: float = field(default_factory=time.time)
    status: LockStatus = LockStatus.LOCKED

    def is_valid(self, timeout_seconds: int = 600) -> bool:
        """
        Check if lock is still valid (not expired).

        Args:
            timeout_seconds: Lock timeout in seconds (default: 10 min)

        Returns:
            True if lock is still valid
        """
        if self.status != LockStatus.LOCKED:
            return False
        return (time.time() - self.locked_at) < timeout_seconds


class LockManager:
    """
    Manager for SAP ADT object locks.

    Handles lock acquisition, release, and timeout.
    """

    def __init__(self):
        self._locks: Dict[str, LockInfo] = {}

    def _make_lock_key(self, object_name: str, object_type: str) -> str:
        """Create unique key for lock storage."""
        return f"{object_type}:{object_name}".lower()

    def acquire_lock(self, object_name: str, object_type: str,
                    owner: str = "system") -> LockInfo:
        """
        Acquire a lock on an object.

        Args:
            object_name: Name of the object to lock
            object_type: Type of the object (class, table, etc.)
            owner: Lock owner identifier

        Returns:
            LockInfo with lock details

        Raises:
            Exception if lock cannot be acquired
        """
        lock_key = self._make_lock_key(object_name, object_type)

        # Check if already locked
        existing = self._locks.get(lock_key)
        if existing and existing.is_valid():
            raise Exception(
                f"Object {object_name} ({object_type}) is already "
                f"locked by {existing.lock_owner}"
            )

        # Create new lock
        lock_handle = str(uuid.uuid4())
        lock_info = LockInfo(
            object_name=object_name,
            object_type=object_type,
            lock_handle=lock_handle,
            lock_owner=owner
        )

        self._locks[lock_key] = lock_info
        return lock_info

    def release_lock(self, object_name: str, object_type: str,
                      owner: str = None) -> bool:
        """
        Release a lock on an object.

        Args:
            object_name: Name of the locked object
            object_type: Type of the object
            owner: Optional lock owner (if specified, must match)

        Returns:
            True if lock was released, False otherwise
        """
        lock_key = self._make_lock_key(object_name, object_type)
        lock = self._locks.get(lock_key)

        if not lock:
            return False  # Not locked

        # Check ownership if specified
        if owner and lock.lock_owner != owner:
            return False  # Wrong owner

        # Remove lock
        del self._locks[lock_key]
        return True

    def get_lock(self, object_name: str, object_type: str) -> Optional[LockInfo]:
        """
        Get lock information for an object.

        Args:
            object_name: Name of the object
            object_type: Type of the object

        Returns:
            LockInfo if locked, None otherwise
        """
        lock_key = self._make_lock_key(object_name, object_type)
        lock = self._locks.get(lock_key)

        if lock and lock.is_valid():
            return lock
        return None

    def force_unlock(self, object_name: str, object_type: str) -> bool:
        """
        Force unlock an object (regardless of ownership).

        Use carefully - only for cleanup after errors.

        Args:
            object_name: Name of the object
            object_type: Type of the object

        Returns:
            True if lock was removed, False otherwise
        """
        lock_key = self._make_lock_key(object_name, object_type)
        if lock_key in self._locks:
            del self._locks[lock_key]
            return True
        return False

    def get_all_locks(self) -> Dict[str, LockInfo]:
        """Get all active locks."""
        return {
            key: lock for key, lock in self._locks.items()
            if lock.is_valid()
        }

    def cleanup_expired_locks(self, timeout_seconds: int = 600) -> int:
        """
        Remove expired locks.

        Args:
            timeout_seconds: Lock timeout in seconds

        Returns:
            Number of locks removed
        """
        expired_keys = [
            key for key, lock in self._locks.items()
            if not lock.is_valid(timeout_seconds)
        ]

        for key in expired_keys:
            del self._locks[key]

        return len(expired_keys)

    def release_all_for_owner(self, owner: str) -> int:
        """
        Release all locks owned by a specific owner.

        Args:
            owner: Lock owner identifier

        Returns:
            Number of locks released
        """
        released = 0
        for key, lock in list(self._locks.items()):
            if lock.lock_owner == owner:
                del self._locks[key]
                released += 1
        return released
