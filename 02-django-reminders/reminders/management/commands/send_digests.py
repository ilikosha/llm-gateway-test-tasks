from django.core.management.base import BaseCommand

from reminders.services import send_due_digests


class Command(BaseCommand):
    help = "Синхронно отправить дайджесты (то же, что делает ежедневная celery-задача)."

    def handle(self, *args, **options):
        sent = send_due_digests()
        self.stdout.write(self.style.SUCCESS(f"Отправлено дайджестов: {sent}"))
