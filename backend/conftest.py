"""
Pytest configuration and shared fixtures for CTS Bundler backend.
"""
import os

import django
import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()


@pytest.fixture
def api_client():
    """DRF API client for request tests."""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def dependency_snapshot_data(db):
    """Create sample DependencySnapshot records for tests."""
    from api.models import DependencySnapshot
    DependencySnapshot.objects.bulk_create([
        DependencySnapshot(source_obj="ZMMR0030", target_obj="EKKO", target_group=4),
        DependencySnapshot(source_obj="ZMMR0030", target_obj="MARA", target_group=4),
        DependencySnapshot(source_obj="ZMM_MAIN", target_obj="ZMMR0030", target_group=2),
    ])
    return None


@pytest.fixture
def ticket_mapping_data(db):
    """Create sample TicketMapping for tests."""
    from api.models import TicketMapping
    TicketMapping.objects.create(
        target_key="EDAK901372",
        ticket_id="JIRA-123",
        description="Sample requirement",
    )
    return None
