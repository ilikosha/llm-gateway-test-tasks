from datetime import date, timedelta

from django.db import models
from django.utils import timezone


class Company(models.Model):
    name = models.CharField("название", max_length=255, unique=True)

    class Meta:
        verbose_name = "компания"
        verbose_name_plural = "компании"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Task(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Активна"
        PAUSED = "paused", "Приостановлена"

    company = models.ForeignKey(
        Company,
        verbose_name="компания",
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    name = models.CharField("название", max_length=255)
    responsible_email = models.EmailField("email ответственного")
    cycle_days = models.PositiveIntegerField("периодичность, дней")
    last_done_date = models.DateField(
        "дата последнего выполнения", null=True, blank=True
    )
    status = models.CharField(
        "статус", max_length=16, choices=Status.choices, default=Status.ACTIVE
    )

    class Meta:
        verbose_name = "задача"
        verbose_name_plural = "задачи"
        ordering = ["company__name", "name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cycle_days__gt=0), name="task_cycle_days_gt_0"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.company})"

    @property
    def next_due_date(self) -> date | None:
        """Срок следующего выполнения; None, если задача ещё ни разу не выполнялась."""
        if self.last_done_date is None:
            return None
        return self.last_done_date + timedelta(days=self.cycle_days)

    def is_due(self, days_ahead: int, today: date | None = None) -> bool:
        """Попадает ли срок задачи в окно «сегодня .. сегодня + days_ahead».

        Правила:
        * граница включительна: срок ровно на today + days_ahead — due;
        * просроченная задача (срок раньше today) считается due;
        * ни разу не выполнявшаяся задача считается due (срок наступил сразу).
        Статус задачи здесь не учитывается — это решает вызывающий код.
        """
        if days_ahead < 0:
            raise ValueError("days_ahead не может быть отрицательным")
        due = self.next_due_date
        if due is None:
            return True
        today = today or timezone.localdate()
        return due <= today + timedelta(days=days_ahead)

    def mark_done(self, today: date | None = None) -> None:
        self.last_done_date = today or timezone.localdate()
        self.save(update_fields=["last_done_date"])


class DigestLog(models.Model):
    """Журнал отправленных дайджестов: один на (email, день)."""

    email = models.EmailField("email")
    sent_on = models.DateField("дата отправки")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "отправленный дайджест"
        verbose_name_plural = "отправленные дайджесты"
        constraints = [
            models.UniqueConstraint(
                fields=["email", "sent_on"], name="uniq_digest_email_date"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.email} · {self.sent_on}"
