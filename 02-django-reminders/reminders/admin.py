from django.contrib import admin, messages
from django.utils import timezone

from .models import Company, DigestLog, Task


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "company",
        "responsible_email",
        "cycle_days",
        "last_done_date",
        "next_due_date",
        "status",
    ]
    list_filter = ["status", "company"]
    search_fields = ["name", "responsible_email"]
    list_select_related = ["company"]
    actions = ["mark_done"]

    @admin.display(description="следующий срок")
    def next_due_date(self, obj: Task):
        return obj.next_due_date

    @admin.action(description="Отметить выполненными (сегодня)")
    def mark_done(self, request, queryset):
        count = queryset.update(last_done_date=timezone.localdate())
        self.message_user(
            request, f"Отмечено выполненными задач: {count}", messages.SUCCESS
        )


@admin.register(DigestLog)
class DigestLogAdmin(admin.ModelAdmin):
    list_display = ["email", "sent_on", "created_at"]
    list_filter = ["sent_on"]
    search_fields = ["email"]
