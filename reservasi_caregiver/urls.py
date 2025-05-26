from django.urls import path
from .views import ReservationListView, ApproveReservationView, RejectReservationView, RescheduleReservationView, CaregiverSchedulesView

app_name = 'reservasi_caregiver'

urlpatterns = [
    path("caregivers/<uuid:caregiver_id>/reservations/", ReservationListView.as_view(), name="reservation_list"),
    path("reservations/<uuid:reservation_id>/approve/", ApproveReservationView.as_view(), name="approve_reservation"),
    path("reservations/<uuid:reservation_id>/reject/", RejectReservationView.as_view(), name="reject_reservation"),
    path("reservations/<uuid:reservation_id>/reschedule/", RescheduleReservationView.as_view(), name="reschedule_reservation"),
    path('api/caregivers/<uuid:caregiver_id>/schedules', CaregiverSchedulesView.as_view(), name='caregiver_schedules'),
]