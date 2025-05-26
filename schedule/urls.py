from django.urls import path
from .views import ScheduleListView, ScheduleCreateView, ScheduleDeleteView

app_name = 'schedule'

urlpatterns = [
    path('schedules/<uuid:caregiver_id>/', ScheduleListView.as_view(), name='schedule_list'),
    path('schedules/<uuid:caregiver_id>/create/', ScheduleCreateView.as_view(), name='schedule_create'),
    path('schedules/<uuid:caregiver_id>/<uuid:schedule_id>/delete/', ScheduleDeleteView.as_view(), name='schedule_delete'),
]