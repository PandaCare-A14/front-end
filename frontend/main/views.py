from django.shortcuts import render
from django.views import View

class HomePageView(View):
    template_name = 'homepage.html'
    
    def get(self, request):
        return render(request, self.template_name, {
            'is_logged_in': False,
            'user_role': 'guest'
        })

class PacilianDashboardView(View):
    template_name = 'homepage.html'
    
    def get(self, request):
        return render(request, self.template_name, {
            'is_logged_in': True,
            'user_role': 'pacilian'
        })

class CaregiverDashboardView(View):
    template_name = 'homepage_caregiver.html'
    
    def get(self, request):
        return render(request, self.template_name, {
            'is_logged_in': True,
            'user_role': 'caregiver'
        })