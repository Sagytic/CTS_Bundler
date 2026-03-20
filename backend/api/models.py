from django.db import models

class DependencySnapshot(models.Model):
    # 호출하는 프로그램 (예: ZMMR0030)
    source_obj = models.CharField(max_length=100, db_index=True)
    
    # 호출당하는 객체 (예: ZMMT0010, EKKO, ZFI015050)
    target_obj = models.CharField(max_length=100, db_index=True)
    
    # 목적지의 성격 (2: 프로그램/클래스, 3: 펑션, 4: DB 테이블)
    target_group = models.IntegerField()

    class Meta:
        # 중복 저장 방지
        unique_together = ('source_obj', 'target_obj')

    def __str__(self):
        return f"{self.source_obj} -> {self.target_obj} (Group: {self.target_group})"
    
class LlmUsageRecord(models.Model):
    """LLM 호출 1건당 1행 — 서버 재시작 후에도 Token Dashboard 집계에 사용."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    operation = models.CharField(max_length=128, db_index=True)
    request_id = models.CharField(max_length=128, default="-", db_index=True)
    prompt_tokens = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)
    total_tokens = models.PositiveIntegerField(default=0)
    duration_ms = models.FloatField(default=0)
    ok = models.BooleanField(default=True)
    extra = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.operation} @ {self.created_at}"


class TicketMapping(models.Model):
    # TR 번호 혹은 오브젝트 명을 Key로 사용
    target_key = models.CharField(max_length=100, unique=True) 
    ticket_id = models.CharField(max_length=50)
    description = models.TextField()

    def __str__(self):
        return f"{self.ticket_id} ({self.target_key})"


class CodeReviewRecord(models.Model):
    """POST /api/code-review/ 결과 영속화 (서버 재시작 후에도 조회 가능)."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    request_id = models.CharField(max_length=128, default="-", db_index=True)
    user_id = models.CharField(max_length=64, blank=True, db_index=True)
    obj_name = models.CharField(max_length=255, blank=True, db_index=True)
    abap_code = models.TextField(blank=True)
    requirement_spec = models.TextField(blank=True)
    ai_result = models.TextField()
    streamed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"code_review {self.obj_name or self.id} @ {self.created_at}"


class DeployReportRecord(models.Model):
    """POST /api/analyze/ (배포 심의) 최종 리포트 영속화."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    request_id = models.CharField(max_length=128, default="-", db_index=True)
    user_id = models.CharField(max_length=64, blank=True, db_index=True)
    user_input = models.TextField(blank=True)
    selected_trs = models.JSONField(default=list, blank=True)
    final_report = models.TextField()
    extra = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"deploy_report @ {self.created_at}"