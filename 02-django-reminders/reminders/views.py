from datetime import date

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.vary import vary_on_headers

from .models import Company, Task

DAYS_CHOICES = (3, 7, 30)
DEFAULT_DAYS = 3


def _parse_days(raw: str | None) -> int:
    try:
        days = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_DAYS
    return days if days in DAYS_CHOICES else DEFAULT_DAYS


def _parse_company(raw: str | None) -> int | None:
    return int(raw) if raw and raw.isdigit() else None


def _row(task: Task, today: date) -> dict:
    due = task.next_due_date
    return {
        "task": task,
        "due": due,
        "overdue": due is not None and due < today,
        "never_done": due is None,
    }


@staff_member_required
@vary_on_headers("HX-Request")
def upcoming(request):
    """Ближайшие сроки. Для HTMX-запроса (заголовок HX-Request) отдаёт только фрагмент."""
    today = timezone.localdate()
    days = _parse_days(request.GET.get("days"))
    company_id = _parse_company(request.GET.get("company"))

    tasks = Task.objects.filter(status=Task.Status.ACTIVE).select_related("company")
    if company_id:
        tasks = tasks.filter(company_id=company_id)
    due_tasks = [t for t in tasks if t.is_due(days, today=today)]
    due_tasks.sort(key=lambda t: (t.next_due_date or date.min, t.company.name, t.name))

    context = {
        "rows": [_row(t, today) for t in due_tasks],
        "today": today,
        "days": days,
        "days_choices": DAYS_CHOICES,
        "companies": Company.objects.all(),
        "company_id": company_id,
    }
    template = (
        "reminders/_upcoming_results.html"
        if request.headers.get("HX-Request")
        else "reminders/upcoming.html"
    )
    return render(request, template, context)


@staff_member_required
@require_POST
def mark_done(request, pk: int):
    task = get_object_or_404(Task, pk=pk)
    task.mark_done()
    row = _row(task, timezone.localdate())
    row["just_done"] = True
    return render(request, "reminders/_task_row.html", {"row": row})
