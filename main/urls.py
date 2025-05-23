from django.urls import path
from .views import (
    HomePageView, 
    PacilianDashboardView, 
    CaregiverDashboardView, 
    LoginView, 
    RegisterView, 
    LogoutView
)

app_name = 'main'

urlpatterns = [
    path('', HomePageView.as_view(), name='home'),
    path('pacilian/dashboard/', PacilianDashboardView.as_view(), name='pacilian_dashboard'),
    path('caregiver/dashboard/<str:caregiver_id>/', CaregiverDashboardView.as_view(), name='caregiver_dashboard'),
    path('register/', RegisterView.as_view(), name='register'), 
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
]