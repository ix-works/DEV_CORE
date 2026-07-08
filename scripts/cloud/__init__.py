#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cloud Connection Helpers for SAP BTP

This module provides helpers for connecting to SAP Business Technology Platform:
- Service key parsing
- BTP connection creation
- System type detection
"""

from cloud.service_key_parser import ServiceKeyParser
from cloud.cloud_connection import (
    get_btp_connection_from_service_key,
    detect_system_type_from_env,
    create_connection_auto
)

__all__ = [
    'ServiceKeyParser',
    'get_btp_connection_from_service_key',
    'detect_system_type_from_env',
    'create_connection_auto'
]
