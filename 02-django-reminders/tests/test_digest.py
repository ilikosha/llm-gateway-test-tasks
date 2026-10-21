from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from reminders.models import Company, DigestLog, Task
from reminders.services import send_due_digests
from reminders.tasks import send_due_digests as send_due_digests_task

pytestmark = pytest.mark.django_db

TODAY = date(2026, 3, 10)


@pytest.fixture
def company():
    return Company.objects.create(name="Альфа")


def add_task(company, name, email, due_in, status=Task.Status.ACTIVE, cycle=10):
    """Создаёт задачу, срок которой наступает через due_in дней от TODAY."""
    return Task.objects.create(
        company=company,
        name=name,
        responsible_email=email,
        cycle_days=cycle,
        last_done_date=TODAY + timedelta(days=due_in - cycle),
        status=status,
    )


def test_one_digest_per_responsible_with_all_tasks(company):
    add_task(company, "Задача 1", "a@example.com", 1)
    add_task(company, "Задача 2", "A@example.com", 3)  # тот же человек, другой регистр
    add_task(company, "Задача 3", "b@example.com", -2)  # просрочена

    assert send_due_digests(today=TODAY) == 2

    by_rcpt = {m.to[0]: m for m in mail.outbox}
    assert set(by_rcpt) == {"a@example.com", "b@example.com"}
    body_a = by_rcpt["a@example.com"].body
    assert "Задача 1" in body_a and "Задача 2" in body_a
    assert "Задача 3" in by_rcpt["b@example.com"].body
    assert "просрочено" in by_rcpt["b@example.com"].body


@pytest.mark.parametrize(
    "due_in, included",
    [(0, True), (3, True), (4, False), (-1, True)],
    ids=["today", "in-3-days", "in-4-days", "overdue"],
)
def test_digest_window_boundaries(company, due_in, included):
    add_task(company, "Граница", "a@example.com", due_in)
    assert send_due_digests(today=TODAY) == (1 if included else 0)
    assert len(mail.outbox) == (1 if included else 0)


def test_not_due_and_paused_tasks_excluded(company):
    add_task(company, "Далеко", "a@example.com", 4)
    add_task(company, "На паузе", "a@example.com", 1, status=Task.Status.PAUSED)
    add_task(company, "Скоро", "b@example.com", 2)

    assert send_due_digests(today=TODAY) == 1
    assert [m.to[0] for m in mail.outbox] == ["b@example.com"]
    assert "Далеко" not in mail.outbox[0].body


def test_never_done_task_is_included(company):
    Task.objects.create(
        company=company, name="Новая", responsible_email="a@example.com", cycle_days=5
    )
    assert send_due_digests(today=TODAY) == 1
    assert "ещё не выполнялась" in mail.outbox[0].body


def test_no_duplicate_on_second_run_same_day(company):
    add_task(company, "Задача", "a@example.com", 1)

    assert send_due_digests(today=TODAY) == 1
    assert send_due_digests(today=TODAY) == 0
    assert len(mail.outbox) == 1
    assert DigestLog.objects.filter(email="a@example.com", sent_on=TODAY).count() == 1


def test_next_day_sends_again(company):
    add_task(company, "Задача", "a@example.com", 1)
    send_due_digests(today=TODAY)
    send_due_digests(today=TODAY + timedelta(days=1))
    assert len(mail.outbox) == 2


def test_failed_send_does_not_block_retry(company, monkeypatch):
    add_task(company, "Задача", "a@example.com", 1)

    def boom(*args, **kwargs):
        raise OSError("smtp down")

    monkeypatch.setattr("reminders.services.send_mail", boom)
    with pytest.raises(OSError):
        send_due_digests(today=TODAY)
    assert DigestLog.objects.count() == 0

    monkeypatch.undo()
    assert send_due_digests(today=TODAY) == 1


def test_celery_task_runs_via_apply(company):
    Task.objects.create(
        company=company, name="Новая", responsible_email="a@example.com", cycle_days=5
    )
    assert send_due_digests_task.apply().get() == 1
    assert len(mail.outbox) == 1


def test_admin_mark_done_action_shifts_due_date(client, company):
    task = add_task(company, "Задача", "a@example.com", -5)
    assert task.is_due(3)
    admin = get_user_model().objects.create_superuser("root", "root@example.com", "pw")
    client.force_login(admin)

    response = client.post(
        reverse("admin:reminders_task_changelist"),
        {"action": "mark_done", "_selected_action": [task.pk]},
        follow=True,
    )

    assert response.status_code == 200
    task.refresh_from_db()
    today = timezone.localdate()
    assert task.last_done_date == today
    assert task.next_due_date == today + timedelta(days=task.cycle_days)
    assert not task.is_due(3)
