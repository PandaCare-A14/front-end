from django.urls import path
from . import views

urlpatterns = [
    path('reservasi/<uuid:id_pacilian>/', views.list_reservasi, name='pacilian_reservasi_list'), 
    path('reservasi/request/', views.request_reservasi, name='pacilian_request_reservasi'),
    # path('reservasi/<uuid:id>/edit/', views.edit_reservasi, name='pacilian_edit_reservasi'),
    path('reservasi/<uuid:id>/accept-change/', views.accept_change, name='pacilian_accept_change'),
    path('reservasi/<uuid:id>/reject-change/', views.reject_change, name='pacilian_reject_change'),

    # Doctor selection flow
    path('doctors/', views.list_doctors, name='pacilian_doctor_list'),
    path('schedules/<uuid:caregiver_id>/', views.DoctorScheduleListView.as_view(), name='doctor_schedules'),
]