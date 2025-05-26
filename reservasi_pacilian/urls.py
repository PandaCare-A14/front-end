from django.urls import path
from . import views

app_name = 'reservasi_pacilian'

urlpatterns = [
    path('reservasi/<uuid:id_pacilian>/', views.list_reservasi, name='pacilian_reservasi_list'),
    path('reservasi/request/', views.ReservationRequestView.as_view(), name='request_reservasi'),
    path('reservasi/<uuid:id>/accept-change/', views.accept_change, name='pacilian_accept_change'),
    path('reservasi/<uuid:id>/reject-change/', views.reject_change, name='pacilian_reject_change'),
    path('schedules/<uuid:caregiver_id>/available/', views.AvailableScheduleListView.as_view(), name='available_schedules_html'),
]