from django.urls import path
from .views import HomePageView, PacilianDashboardView, CaregiverDashboardView

app_name = 'main'

urlpatterns = [
    path('', HomePageView.as_view(), name='home'),
    path('pacilian/dashboard/', PacilianDashboardView.as_view(), name='pacilian_dashboard'),
    path('caregiver/dashboard/', CaregiverDashboardView.as_view(), name='caregiver_dashboard'),
]