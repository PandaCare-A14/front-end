from django.urls import path
<<<<<<< HEAD
from .views import ReservationListView, ApproveReservationView, RejectReservationView, RescheduleReservationView, CaregiverSchedulesView

urlpatterns = [
    path("caregivers/<uuid:caregiver_id>/reservations/", ReservationListView.as_view(), name="reservation_list"),
    path("reservations/<uuid:reservation_id>/approve/", ApproveReservationView.as_view(), name="approve_reservation"),
    path("reservations/<uuid:reservation_id>/reject/", RejectReservationView.as_view(), name="reject_reservation"),
    path("reservations/<uuid:reservation_id>/reschedule/", RescheduleReservationView.as_view(), name="reschedule_reservation"),
    path('api/caregivers/<uuid:caregiver_id>/schedules', CaregiverSchedulesView.as_view(), name='caregiver_schedules'),
=======
from .views import ReservationListView

urlpatterns = [
    path("caregivers/<uuid:caregiver_id>/reservations/", ReservationListView.as_view(), name="reservation_list"),
>>>>>>> b8e80e7e461e92a9496322855b801a92032c5968
]