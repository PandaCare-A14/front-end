from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
import uuid
from urllib.parse import urlencode
from main.views import api_request, get_base_context, is_logged_in

class DoctorListView(View):
    template_name = 'doctor_list.html'

    def get(self, request):
        context = get_base_context(request)
        name = request.GET.get('name')
        speciality = request.GET.get('speciality')
        day = request.GET.get('day')
        start_time = request.GET.get('start_time')
        end_time = request.GET.get('end_time')

        context.update({
            'name': name or '',
            'speciality': speciality or '',
            'day': day or '',
            'start_time': start_time or '',
            'end_time': end_time or ''
        })

        try:
            params = {}
            if name:
                params.update({
                    'name': name.strip(),
                })
            if speciality:
                params.update({
                    'speciality': speciality.strip(),
                })
            if day and start_time and end_time:
                params.update({
                    'day': day.strip().upper(),
                    'startTime': start_time.strip(),
                    'endTime': end_time.strip()
                })

            if params:
                # Use the new combined search endpoint
                endpoint = "/api/doctors/search?" + urlencode(params)
                response = api_request("GET", endpoint, token=request.session.get("access_token"))
            else:
                # Get all doctors if no search parameters
                response = api_request("GET", "/api/doctors", token=request.session.get("access_token"))
            
            if response and 'doctorProfiles' in response:
                context.update({
                    'doctors': response['doctorProfiles'],
                    'total_items': response.get('totalItems', len(response['doctorProfiles'])),
                    'search_performed': bool(params)
                })
            else:
                context.update({
                    'doctors': [],
                    'total_items': 0,
                    'search_performed': bool(params),
                    'no_results': True
                })
            
            return render(request, self.template_name, context)
            
        except Exception as e:
            messages.error(request, f"Error fetching doctors: {str(e)}")
            return render(request, self.template_name, context)

class DoctorProfileView(View):
    template_name = 'doctor_profile.html'
    
    def get(self, request, doctor_id):
        context = get_base_context(request)
        patient_id = request.session.get("user_id")
        
        try:
            uuid.UUID(str(doctor_id))
            
            doctor_response = api_request(
                "GET", 
                f"/api/doctors/{doctor_id}", 
                token=request.session.get("access_token")
            )

            if not doctor_response:
                messages.error(request, "Doctor not found")
                return redirect("doctor_profile:search")
            print(f"{doctor_response}")
            context.update({
                'doctor': doctor_response,
                'patient_id': patient_id
            })

            return render(request, self.template_name, context)
            
        except ValueError as e:
            messages.error(request, f"Invalid ID format: {str(e)}")
            print(f"Value error loading doctor profile: {str(e)}")
            return redirect("doctor_profile:search")
        except Exception as e:
            messages.error(request, f"Error loading doctor profile: {str(e)}")
            print(f"Exception error loading doctor profile: {str(e)}")
            return redirect("doctor_profile:search")