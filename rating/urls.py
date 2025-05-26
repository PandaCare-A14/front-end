from django.urls import path
from .views import AddRatingView, UpdateRatingView, DeleteRatingView, GetRatingsByDoctorView, CheckRatingStatusView

urlpatterns = [
    # Rating Views
    path('doctors/<uuid:doctor_id>/ratings/add/', AddRatingView.as_view(), name='add_rating'),  # Add rating to a consultation
    path('doctors/<uuid:doctor_id>/ratings/update/', UpdateRatingView.as_view(), name='update_rating'),  # Update rating
    path('doctors/<uuid:doctor_id>/ratings/delete/', DeleteRatingView.as_view(), name='delete_rating'),  # Delete rating

    # Fetch Ratings by Doctor
    path('doctors/<uuid:id_dokter>/ratings/', GetRatingsByDoctorView.as_view(), name='get_ratings_by_doctor'),  # Get all ratings for a doctor

    # Check if a rating has been given for a specific consultation
    path('consultations/<uuid:id_jadwal_konsultasi>/rating/status/', CheckRatingStatusView.as_view(), name='check_rating_status'),
]
