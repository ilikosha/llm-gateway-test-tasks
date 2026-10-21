from django.contrib import admin
from django.urls import path

from reminders import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("upcoming/", views.upcoming, name="upcoming"),
    path("upcoming/<int:pk>/done/", views.mark_done, name="upcoming_done"),
]
