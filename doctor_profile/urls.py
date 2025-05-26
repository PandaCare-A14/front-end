from django.urls import path
from doctor_profile import views

app_name = 'doctor_profile'

urlpatterns = [
    path('', views.DoctorListView.as_view(), name='search'),
    path('<uuid:doctor_id>/', views.DoctorProfileView.as_view(), name='detail'),
]