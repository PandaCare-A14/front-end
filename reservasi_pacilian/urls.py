from django.urls import path
from . import views

urlpatterns = [
    path('reservasi/<uuid:id_pacilian>/', views.list_reservasi, name='pacilian_reservasi_list'), 
    path('reservasi/request/', views.request_reservasi, name='pacilian_request_reservasi'),
    # path('reservasi/<uuid:id>/edit/', views.edit_reservasi, name='pacilian_edit_reservasi'),
    path('reservasi/<uuid:id>/accept-change/', views.accept_change, name='pacilian_accept_change'),
    path('reservasi/<uuid:id>/reject-change/', views.reject_change, name='pacilian_reject_change'),

    # NEW: Edit reservation endpoint
    path('reservasi/<uuid:id>/edit/', views.edit_reservation, name='pacilian_edit_reservation'),
    # Alternative JSON API endpoint
    path('api/schedules/<uuid:caregiver_id>/available/', views.get_available_schedules, name='api_available_schedules'),
    # HTML page for schedule selection (NEW)
    path('schedules/<uuid:caregiver_id>/available/', views.AvailableScheduleListView.as_view(), name='available_schedules_html'),
]