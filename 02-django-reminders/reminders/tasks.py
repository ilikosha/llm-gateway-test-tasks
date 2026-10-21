from celery import shared_task

from . import services


@shared_task(name="reminders.send_due_digests")
def send_due_digests() -> int:
    return services.send_due_digests()
