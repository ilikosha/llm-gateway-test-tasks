from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from reminders.models import Company, Task


class Command(BaseCommand):
    help = "Создать демо-данные (идемпотентно)."

    def handle(self, *args, **options):
        today = timezone.localdate()
        alpha, _ = Company.objects.get_or_create(name="Альфа")
        beta, _ = Company.objects.get_or_create(name="Бета")
        # (компания, название, email, период, дней с последнего выполнения)
        rows = [
            (alpha, "Сдать отчёт по НДС", "ivanov@example.com", 30, 28),  # срок через 2 дня
            (alpha, "Проверить огнетушители", "ivanov@example.com", 90, 100),  # просрочена
            (alpha, "Обновить пароли", "petrova@example.com", 60, 10),  # не скоро
            (beta, "Резервное копирование", "petrova@example.com", 7, 5),  # через 2 дня
            (beta, "Инвентаризация", "sidorov@example.com", 365, None),  # ни разу
        ]
        created = 0
        for company, name, email, cycle, ago in rows:
            _, was_created = Task.objects.get_or_create(
                company=company,
                name=name,
                defaults={
                    "responsible_email": email,
                    "cycle_days": cycle,
                    "last_done_date": today - timedelta(days=ago) if ago is not None else None,
                },
            )
            created += was_created
        self.stdout.write(self.style.SUCCESS(f"Демо-данные готовы, создано задач: {created}"))
