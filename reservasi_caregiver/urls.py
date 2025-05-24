from django.urls import path
from .views import ReservationListView

urlpatterns = [
    path("caregivers/<uuid:caregiver_id>/reservations/", ReservationListView.as_view(), name="reservation_list"),
]
