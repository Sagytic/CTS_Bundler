from django.contrib import admin

from api.models import (
    CodeReviewRecord,
    DependencySnapshot,
    DeployReportRecord,
    TicketMapping,
)


@admin.register(DependencySnapshot)
class DependencySnapshotAdmin(admin.ModelAdmin):
    list_display = ("source_obj", "target_obj", "target_group")
    list_filter = ("target_group",)
    search_fields = ("source_obj", "target_obj")


@admin.register(TicketMapping)
class TicketMappingAdmin(admin.ModelAdmin):
    list_display = ("target_key", "ticket_id", "description")
    search_fields = ("target_key", "ticket_id")


@admin.register(CodeReviewRecord)
class CodeReviewRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "obj_name", "user_id", "streamed")
    list_filter = ("streamed",)
    search_fields = ("obj_name", "user_id", "request_id")
    readonly_fields = ("created_at",)


@admin.register(DeployReportRecord)
class DeployReportRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "user_id", "request_id")
    search_fields = ("user_id", "request_id")
    readonly_fields = ("created_at",)
