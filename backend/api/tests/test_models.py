"""Tests for api.models."""
import pytest
from django.core.exceptions import ValidationError

from api.models import DependencySnapshot, TicketMapping


@pytest.mark.django_db
class TestDependencySnapshot:
    """DependencySnapshot model."""

    def test_create_and_str(self):
        dep = DependencySnapshot.objects.create(
            source_obj="ZMMR0030",
            target_obj="EKKO",
            target_group=4,
        )
        assert dep.source_obj == "ZMMR0030"
        assert dep.target_obj == "EKKO"
        assert "ZMMR0030" in str(dep) and "EKKO" in str(dep)

    def test_unique_together(self):
        DependencySnapshot.objects.create(
            source_obj="A", target_obj="B", target_group=2
        )
        with pytest.raises(Exception):  # IntegrityError
            DependencySnapshot.objects.create(
                source_obj="A", target_obj="B", target_group=3
            )


@pytest.mark.django_db
class TestTicketMapping:
    """TicketMapping model."""

    def test_create_and_str(self):
        t = TicketMapping.objects.create(
            target_key="TR001",
            ticket_id="JIRA-1",
            description="Req",
        )
        assert t.target_key == "TR001"
        assert "JIRA-1" in str(t)

    def test_unique_target_key(self):
        TicketMapping.objects.create(
            target_key="K1", ticket_id="J1", description="D1"
        )
        with pytest.raises(Exception):
            TicketMapping.objects.create(
                target_key="K1", ticket_id="J2", description="D2"
            )
