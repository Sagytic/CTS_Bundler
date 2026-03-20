from django.urls import path

from api.rag.views import RAGIngestView, RAGQueryView
from api.views import (
    AdtWriteView,
    AICodeReviewView,
    AnalyzeGuardianView,
    CodeReviewHistoryDetailView,
    CodeReviewHistoryListView,
    DeployReportHistoryDetailView,
    DeployReportHistoryListView,
    DependencyEdgesView,
    DependencyGraphView,
    SAPChatRAGView,
    SAPChatView,
    SapTestView,
    SnapshotUpdateView,
    TicketInfoView,
    TicketMappingUpsertView,
    TRListView,
)
from api.views.agent import AgentChatView  # not in __all__ to avoid circular deps
from api.views.usage_stats import LLMUsageStatsResetView, LLMUsageStatsView

urlpatterns = [
    path("analyze/", AnalyzeGuardianView.as_view(), name="analyze"),
    path("sap-test/", SapTestView.as_view(), name="sap-test"),
    path("transports/", TRListView.as_view(), name="transport-list"),
    path("chat/", SAPChatView.as_view(), name="sap-chat"),
    path("chat/rag/", SAPChatRAGView.as_view(), name="chat-rag"),
    path("agent/", AgentChatView.as_view(), name="agent"),
    path("dependency/", DependencyGraphView.as_view(), name="dependency-graph"),
    path("dependency-edges/", DependencyEdgesView.as_view(), name="dependency-edges"),
    path("snapshot/update/", SnapshotUpdateView.as_view(), name="snapshot-upload"),
    path("code-review/", AICodeReviewView.as_view(), name="code-review"),
    path(
        "code-review-history/",
        CodeReviewHistoryListView.as_view(),
        name="code-review-history-list",
    ),
    path(
        "code-review-history/<int:pk>/",
        CodeReviewHistoryDetailView.as_view(),
        name="code-review-history-detail",
    ),
    path(
        "deploy-report-history/",
        DeployReportHistoryListView.as_view(),
        name="deploy-report-history-list",
    ),
    path(
        "deploy-report-history/<int:pk>/",
        DeployReportHistoryDetailView.as_view(),
        name="deploy-report-history-detail",
    ),
    path("ticket-info/", TicketInfoView.as_view(), name="ticket-info"),
    path("ticket-mapping/", TicketMappingUpsertView.as_view(), name="ticket-mapping-upsert"),
    path("adt-write/", AdtWriteView.as_view(), name="adt-write"),
    path("rag/ingest/", RAGIngestView.as_view(), name="rag-ingest"),
    path("rag/query/", RAGQueryView.as_view(), name="rag-query"),
    path("usage-stats/", LLMUsageStatsView.as_view(), name="usage-stats"),
    path("usage-stats/reset/", LLMUsageStatsResetView.as_view(), name="usage-stats-reset"),
]