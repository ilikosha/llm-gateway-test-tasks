from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from reminders.models import Company, Task

pytestmark = pytest.mark.django_db


def make(company, name, due_in, cycle=10, status=Task.Status.ACTIVE):
    today = timezone.localdate()
    return Task.objects.create(
        company=company, name=name, responsible_email="a@example.com",
        cycle_days=cycle, last_done_date=today + timedelta(days=due_in - cycle),
        status=status,
    )


@pytest.fixture
def company():
    return Company.objects.create(name="Альфа")


@pytest.fixture
def staff_client():
    user = get_user_model().objects.create_user("st", password="pw", is_staff=True)
    c = Client(enforce_csrf_checks=True)
    c.force_login(user)
    return c


def test_requires_staff_login(company):
    r = Client().get(reverse("upcoming"))
    assert r.status_code == 302 and "login" in r["Location"]


def test_page_renders_full_with_overdue_highlight(staff_client, company):
    make(company, "Просроченная", -2)
    make(company, "Сегодня", 0)
    make(company, "Через три", 3)
    make(company, "Через четыре", 4)
    r = staff_client.get(reverse("upcoming"))
    html = r.content.decode()
    assert "<html" in html and "htmx.org@2.0.4" in html
    assert "Просроченная" in html and "Сегодня" in html and "Через три" in html
    assert "Через четыре" not in html
    assert 'class="overdue' in html
    assert html.index("Просроченная") < html.index("Сегодня") < html.index("Через три")


def test_days_selector_and_company_filter(staff_client, company):
    other = Company.objects.create(name="Бета")
    make(company, "Через неделю", 7)
    make(other, "Бета-задача", 1)
    url = reverse("upcoming")
    assert "Через неделю" not in staff_client.get(url).content.decode()
    html = staff_client.get(url, {"days": 7}).content.decode()
    assert "Через неделю" in html
    html = staff_client.get(url, {"days": 7, "company": other.pk}).content.decode()
    assert "Бета-задача" in html and "Через неделю" not in html
    # недопустимое значение -> по умолчанию 3
    assert "Через неделю" not in staff_client.get(url, {"days": 99}).content.decode()


def test_paused_excluded(staff_client, company):
    make(company, "Пауза", 1, status=Task.Status.PAUSED)
    assert "Пауза" not in staff_client.get(reverse("upcoming")).content.decode()


def test_htmx_request_returns_fragment_only(staff_client, company):
    make(company, "Задача", 1)
    r = staff_client.get(reverse("upcoming"), HTTP_HX_REQUEST="true")
    html = r.content.decode()
    assert "Задача" in html
    assert "<html" not in html and "<body" not in html
    assert "HX-Request" in r["Vary"]


def test_mark_done_requires_post(staff_client, company):
    t = make(company, "Задача", -1)
    r = staff_client.get(reverse("upcoming_done", args=[t.pk]))
    assert r.status_code == 405
    t.refresh_from_db()
    assert t.last_done_date != timezone.localdate()


def test_mark_done_updates_date_and_returns_row(staff_client, company):
    t = make(company, "Задача", -1)
    token = staff_client.get(reverse("upcoming")).cookies["csrftoken"].value
    r = staff_client.post(
        reverse("upcoming_done", args=[t.pk]), HTTP_X_CSRFTOKEN=token, HTTP_HX_REQUEST="true"
    )
    assert r.status_code == 200
    t.refresh_from_db()
    assert t.last_done_date == timezone.localdate()
    html = r.content.decode()
    assert f'id="task-{t.pk}"' in html and "<html" not in html
    assert "Выполнено, след. срок" in html


def test_mark_done_rejects_missing_csrf_and_anonymous(staff_client, company):
    t = make(company, "Задача", -1)
    assert staff_client.post(reverse("upcoming_done", args=[t.pk])).status_code == 403
    r = Client().post(reverse("upcoming_done", args=[t.pk]))
    assert r.status_code in (302, 403)
    t.refresh_from_db()
    assert t.last_done_date != timezone.localdate()
