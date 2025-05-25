from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import requests
import uuid
from datetime import datetime
from urllib.parse import urlencode
from main.views import api_request, get_base_context, is_logged_in

class DoctorListView(View):
    template_name = 'doctor_list.html'

    def get(self, request):
        if not is_logged_in(request):
            messages.error(request, "Please login first")
            return redirect("main:login")
        
        context = get_base_context(request)
        search_type = request.GET.get('search_type')
        query = request.GET.get('query')
        day = request.GET.get('day')
        start_time = request.GET.get('start_time')
        end_time = request.GET.get('end_time')

        context.update({
            'search_type': search_type or 'name',
            'query': query or '',
            'day': day or '',
            'start_time': start_time or '',
            'end_time': end_time or ''
        })
        
        try:
            if search_type:
                if search_type == 'schedule':
                    endpoint = self._get_search_endpoint(
                        search_type=search_type,
                        day=day,
                        start_time=start_time,
                        end_time=end_time,
                    )
                else:
                    endpoint = self._get_search_endpoint(
                        search_type=search_type,
                        query=query
                    )
                
                response = api_request("GET", endpoint, token=request.session.get("access_token"))
                
                if response and 'doctorProfiles' in response:
                    context.update({
                        'doctors': response['doctorProfiles'],
                        'total_items': response.get('totalItems', len(response['doctorProfiles'])),
                        'search_type': search_type,
                        'query': query,
                        'search_performed': True
                    })
                else:
                    context.update({
                        'doctors': [],
                        'total_items': 0,
                        'search_performed': True,
                        'no_results': True
                    })
            else:
                # Get all doctors if no search parameters
                response = api_request("GET", "/api/doctors", token=request.session.get("access_token"))
                if response and 'doctorProfiles' in response:
                    context.update({
                        'doctors': response['doctorProfiles'],
                        'total_items': response.get('totalItems', len(response['doctorProfiles']))
                    })
            
            return render(request, self.template_name, context)
            
        except Exception as e:
            messages.error(request, f"Error fetching doctors: {str(e)}")
            return render(request, self.template_name, context)
    
    def _get_search_endpoint(self, search_type, query=None, day=None, start_time=None, end_time=None):
        if search_type == 'name':
            return f"/api/doctors/search/by-name?name={query}"
        elif search_type == 'speciality':
            return f"/api/doctors/search/by-speciality?speciality={query}"
        elif search_type == 'schedule':
            try:
                params = {
                    'day': day.strip().upper() if day else '',
                    'startTime': start_time.strip() if start_time else '',
                    'endTime': end_time.strip() if end_time else ''
                }
                return f"/api/doctors/search/by-schedule?day={params['day']}&startTime={params['startTime']}&endTime={params['endTime']}"
            except Exception as e:
                raise ValueError(f"Invalid schedule parameters: {str(e)}")
        else:
            raise ValueError("Invalid search type")

class DoctorProfileView(View):
    template_name = 'doctor_profile.html'
    
    def get(self, request, doctor_id):
        if not is_logged_in(request):
            messages.error(request, "Please login first")
            return redirect("main:login")
        
        context = get_base_context(request)
        patient_id = request.session.get("user_id")
        
        try:
            # Validate UUID format
            uuid.UUID(str(doctor_id))
            uuid.UUID(str(patient_id))
            
            # Get basic doctor profile
            doctor_response = api_request(
                "GET", 
                f"/api/doctors/{doctor_id}", 
                token=request.session.get("access_token")
            )
            
            if not doctor_response:
                messages.error(request, "Doctor not found")
                return redirect("doctor_profile:search")
            
            # Get profile with action buttons if patient_id is available
            if patient_id and request.session.get("user_role") == "pacilian":
                actions_response = api_request(
                    "GET", 
                    f"/api/doctors/{doctor_id}/actions?patientId={patient_id}", 
                    token=request.session.get("access_token")
                )
                
                if actions_response:
                    doctor_response.update({
                        'can_chat': True,
                        'can_appointment': True
                    })
            
            context.update({
                'doctor': doctor_response,
                'patient_id': patient_id
            })
            
            return render(request, self.template_name, context)
            
        except ValueError as e:
            messages.error(request, f"Invalid ID format: {str(e)}")
            return redirect("doctor_profile:search")
        except Exception as e:
            messages.error(request, f"Error loading doctor profile: {str(e)}")
            return redirect("doctor_profile:search")

@method_decorator(csrf_exempt, name='dispatch')
class DoctorActionView(View):
    def post(self, request, doctor_id):
        if not is_logged_in(request) or request.session.get("user_role") != "pacilian":
            messages.error(request, "Unauthorized action")
            return redirect("main:login")
        
        action = request.POST.get('action')
        patient_id = request.session.get("user_id")
        
        try:
            if action == 'start_chat':
                # Call chat initiation API
                response = api_request(
                    "POST",
                    f"/api/chat/start",
                    data={
                        "caregiverId": doctor_id,
                        "patientId": patient_id
                    },
                    token=request.session.get("access_token")
                )
                if response:
                    return redirect("chat:detail", chat_id=response.get('chatId'))
            
            elif action == 'create_appointment':
                # Call appointment creation API
                appointment_time = request.POST.get('appointment_time')
                response = api_request(
                    "POST",
                    f"/api/appointments",
                    data={
                        "caregiverId": doctor_id,
                        "patientId": patient_id,
                        "time": appointment_time
                    },
                    token=request.session.get("access_token")
                )
                if response:
                    messages.success(request, "Appointment created successfully")
                    return redirect("appointment:detail", appointment_id=response.get('appointmentId'))
            
            return redirect("doctor_profile:detail", doctor_id=doctor_id)
            
        except Exception as e:
            messages.error(request, f"Failed to perform action: {str(e)}")
            return redirect("doctor_profile:detail", doctor_id=doctor_id)