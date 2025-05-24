from django.urls import path
from . import views

urlpatterns = [
    path('caregivers/<uuid:caregiver_id>/schedules/', views.schedule_list, name="schedule_list"),
    path('caregivers/<uuid:caregiver_id>/schedules/create/', views.create_schedule, name="schedule_create"),
    path("<uuid:caregiver_id>/schedules/<uuid:schedule_id>/delete/", views.delete_schedule, name="schedule_delete"),
]
