from datetime import date, timedelta

import pytest

from reminders.models import Company, Task

TODAY = date(2026, 3, 10)


def make_task(last_done, cycle_days=10):
    return Task(
        company=Company(name="C"),
        name="t",
        responsible_email="a@example.com",
        cycle_days=cycle_days,
        last_done_date=last_done,
    )


@pytest.mark.parametrize(
    "offset, expected",
    [
        (-1, True),   # срок вчера: просрочена -> due
        (0, True),    # срок сегодня
        (1, True),
        (3, True),    # ровно на границе окна
        (4, False),   # сразу за окном
        (30, False),
        (-100, True),  # давно просрочена
    ],
)
def test_is_due_window_boundaries(offset, expected):
    due = TODAY + timedelta(days=offset)
    task = make_task(last_done=due - timedelta(days=10), cycle_days=10)
    assert task.next_due_date == due
    assert task.is_due(3, today=TODAY) is expected


def test_never_done_is_due():
    task = make_task(last_done=None)
    assert task.next_due_date is None
    assert task.is_due(0, today=TODAY) is True


def test_zero_days_ahead_only_today_and_overdue():
    assert make_task(TODAY - timedelta(days=10)).is_due(0, today=TODAY)
    assert not make_task(TODAY - timedelta(days=9)).is_due(0, today=TODAY)


def test_negative_days_ahead_rejected():
    with pytest.raises(ValueError):
        make_task(TODAY).is_due(-1, today=TODAY)


@pytest.mark.django_db
def test_mark_done_shifts_due_date():
    task = Task.objects.create(
        company=Company.objects.create(name="C"),
        name="t",
        responsible_email="a@example.com",
        cycle_days=10,
        last_done_date=TODAY - timedelta(days=50),
    )
    assert task.is_due(3, today=TODAY)
    task.mark_done(today=TODAY)
    task.refresh_from_db()
    assert task.next_due_date == TODAY + timedelta(days=10)
    assert not task.is_due(3, today=TODAY)
