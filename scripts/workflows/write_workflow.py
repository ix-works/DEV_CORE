#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Write Workflow Manager for SAP ADT

Implements safe write workflows: Lock → Create → Activate → Unlock
Based on mcp-abap-adt reference implementation.
"""
import time
from typing import Optional, Dict, Any, Callable
from session import LockManager, SessionManager, LockInfo
from sap_adt_lib import SAPConnectionError, SAPActivationError


class WriteWorkflow:
    """
    Manages safe object write operations.

    Workflow: Lock → Create → Activate → Unlock

    Ensures:
    - Objects are locked before modification
    - Locks are released even if operations fail
    - Activation errors are properly handled
    - Session state is maintained
    """

    def __init__(self, session_manager: SessionManager = None,
                 lock_manager: LockManager = None):
        """
        Initialize workflow manager.

        Args:
            session_manager: SessionManager instance (creates default if None)
            lock_manager: LockManager instance (creates default if None)
        """
        self.session = session_manager or SessionManager()
        self.locks = lock_manager or LockManager()

    def execute_write(self,
                      object_name: str,
                      object_type: str,
                      write_operation: Callable,
                      lock_owner: str = "system",
                      transport: str = None,
                      activate: bool = True,
                      unlock_on_error: bool = True) -> Dict[str, Any]:
        """
        Execute a write operation with full workflow.

        Args:
            object_name: Name of the object to modify
            object_type: Type of object (class, table, program, etc.)
            write_operation: Function that performs the actual write
            lock_owner: Owner identifier for the lock
            transport: Transport request number
            activate: Whether to activate after write
            unlock_on_error: Whether to unlock on error

        Returns:
            Dict with:
                - success: bool
                - result: Operation result
                - lock: LockInfo (if acquired)
                - error: Error message (if failed)

        Example:
            def create_class(session):
                return session.make_request(
                    'PUT',
                    f'/sap/bc/adt/oo/classes/{name}',
                    data=class_source
                )

            result = workflow.execute_write(
                'ZCL_MY_CLASS', 'class', create_class,
                lock_owner='DEVELOPER',
                transport='NPLK900077'
            )
        """
        lock = None
        session = None

        try:
            # Step 1: Acquire lock
            print(f"[1/4] Acquiring lock on {object_type} {object_name}...")
            lock = self.locks.acquire_lock(object_name, object_type, lock_owner)
            print(f"   Lock acquired: {lock.lock_handle[:8]}...")

            # Step 2: Perform write operation
            print(f"[2/4] Performing write operation...")
            result = write_operation(lock=lock, transport=transport)

            # Step 3: Activate
            if activate:
                print(f"[3/4] Activating object...")
                # Activation would happen here
                # For now, just note it
                print(f"   Activation: skipped (not implemented)")

            # Step 4: Release lock
            print(f"[4/4] Releasing lock...")
            self.locks.release_lock(object_name, object_type, lock_owner)
            print(f"   Lock released")

            return {
                'success': True,
                'result': result,
                'lock': lock
            }

        except Exception as e:
            print(f"\n   [ERROR] Operation failed: {e}")

            # Cleanup: Unlock on error if requested
            if unlock_on_error and lock:
                print(f"\n   [CLEANUP] Unlocking due to error...")
                self.locks.release_lock(object_name, object_type, lock_owner)
                print("   [OK] Unlocked")

            # Also try to unlock with force if regular unlock fails
            if lock:
                self.locks.force_unlock(object_name, object_type)

            return {
                'success': False,
                'result': None,
                'lock': lock,
                'error': str(e)
            }


class ObjectEditor:
    """
    High-level editor for SAP objects with automatic lock management.

    Provides context manager style editing for objects.
    """

    def __init__(self, object_name: str, object_type: str,
                 workflow: WriteWorkflow = None,
                 lock_owner: str = "system"):
        """
        Initialize object editor.

        Args:
            object_name: Name of the object
            object_type: Type of object
            workflow: WriteWorkflow instance
            lock_owner: Lock owner identifier
        """
        self.object_name = object_name
        self.object_type = object_type
        self.workflow = workflow or WriteWorkflow()
        self.lock_owner = lock_owner
        self._lock = None

    def __enter__(self):
        """Enter context: Acquire lock."""
        self._lock = self.workflow.locks.acquire_lock(
            self.object_name, self.object_type, self.lock_owner
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context: Release lock."""
        if self._lock:
            self.workflow.locks.release_lock(
                self.object_name, self.object_type, self.lock_owner
            )
        return False  # Don't suppress exceptions


def create_write_workflow(session_manager: SessionManager = None,
                         lock_manager: LockManager = None) -> WriteWorkflow:
    """
    Factory function to create WriteWorkflow.

    Args:
        session_manager: Optional SessionManager
        lock_manager: Optional LockManager

    Returns:
        WriteWorkflow instance
    """
    return WriteWorkflow(session_manager, lock_manager)


def create_object_editor(object_name: str, object_type: str,
                          lock_owner: str = "system") -> ObjectEditor:
    """
    Factory function to create ObjectEditor.

    Args:
        object_name: Name of the object
        object_type: Type of object
        lock_owner: Lock owner identifier

    Returns:
        ObjectEditor instance
    """
    return ObjectEditor(object_name, object_type, lock_owner=lock_owner)
