import logging
from collections import defaultdict
from datetime import date

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import DigestLog, Task

logger = logging.getLogger(__name__)


def collect_due_tasks(days_ahead: int, today: date) -> dict[str, list[Task]]:
    """Активные задачи, у которых наступает срок, сгруппированные по email (в нижнем регистре)."""
    tasks = Task.objects.filter(status=Task.Status.ACTIVE).select_related("company")
    grouped: dict[str, list[Task]] = defaultdict(list)
    for task in tasks:
        if task.is_due(days_ahead, today=today):
            grouped[task.responsible_email.strip().lower()].append(task)
    return grouped


def render_digest(tasks: list[Task], today: date) -> tuple[str, str]:
    lines = []
    for task in sorted(tasks, key=lambda t: (t.next_due_date or date.min, t.name)):
        due = task.next_due_date
        if due is None:
            when = "ещё не выполнялась"
        elif due < today:
            when = f"просрочено, срок был {due:%d.%m.%Y}"
        else:
            when = f"срок {due:%d.%m.%Y}"
        lines.append(f"- [{task.company}] {task.name} — {when}")
    subject = f"Напоминание: задач к выполнению — {len(tasks)}"
    body = "Здравствуйте!\n\nБлижайшие задачи:\n\n" + "\n".join(lines) + "\n"
    return subject, body


def send_due_digests(today: date | None = None) -> int:
    """Отправляет по одному дайджесту на ответственного. Возвращает число отправленных писем.

    Идемпотентность: запись DigestLog(email, today) создаётся в той же транзакции,
    что и отправка. Уникальное ограничение не даёт второму (в том числе параллельному)
    запуску отправить повторно; если отправка упала — транзакция откатывает запись,
    и следующий запуск повторит попытку.
    """
    today = today or timezone.localdate()
    grouped = collect_due_tasks(settings.DIGEST_DAYS_AHEAD, today)
    sent = 0
    for email, tasks in sorted(grouped.items()):
        with transaction.atomic():
            _, created = DigestLog.objects.get_or_create(email=email, sent_on=today)
            if not created:
                logger.info("Дайджест для %s за %s уже отправлен", email, today)
                continue
            subject, body = render_digest(tasks, today)
            send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [email])
            sent += 1
    return sent
