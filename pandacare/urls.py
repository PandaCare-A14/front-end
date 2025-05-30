"""
URL configuration for pandacare project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path

from main.views import HomePageView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', HomePageView.as_view(), name='home'), 
    path('', include('main.urls')),
    path('', include('chat.urls')),
    path('caregiver-reservation/', include('reservasi_caregiver.urls')),
    path('schedule/', include('schedule.urls')),
    path('doctors/', include('doctor_profile.urls', namespace='doctor_profile')),
    path('pacillian-reservation/', include('reservasi_pacilian.urls')),
    path('rating/', include('rating.urls')),
]
