from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import requests
import os

API_BASE_URL = os.getenv("API_BASE_URL")

def is_logged_in(request):
    return bool(request.session.get("access_token"))

def api_request(method, endpoint, data=None, token=None, params=None):
    if not API_BASE_URL:
        raise Exception("API_BASE_URL environment variable not set")
    
    url = f"{API_BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        if method.upper() == "GET" and params:
            response = requests.request(method, url, headers=headers, params=params, timeout=30)
        elif data is not None:
            response = requests.request(method, url, headers=headers, json=data, timeout=30)
        else:
            response = requests.request(method, url, headers=headers, timeout=30)
        
        if response.status_code in [200, 201, 204]:
            try:
                return response.json()
            except:
                return response.text if response.text else {"success": True}
        elif response.status_code in [401, 403]:
            raise PermissionError(f"Unauthorized: {response.text}")
        else:
            raise Exception(f"API error {response.status_code}: {response.text}")
            
    except requests.exceptions.Timeout:
        raise Exception("Request timeout - server may be down")
    except requests.exceptions.ConnectionError:
        raise Exception("Connection error - cannot reach server")
    except Exception as e:
        raise Exception(f"API Error: {str(e)}")

@method_decorator(csrf_exempt, name='dispatch')
class ScheduleListView(View):
    template_name = 'schedule_list.html'
    
    def get(self, request, caregiver_id):
        if not is_logged_in(request):
            messages.error(request, "Please login first")
            return redirect("main:login")
        
        # Check if user is caregiver and matches caregiver_id
        if request.session.get("user_role") != "caregiver":
            messages.error(request, "Access denied")
            return redirect("main:home")
        
        if request.session.get("user_id") != caregiver_id:
            messages.error(request, "Access denied")
            return redirect("main:home")
        
        token = request.session.get("access_token")
        
        # Get filter parameters
        status_filter = request.GET.get("status", "")
        day_filter = request.GET.get("day", "")
        
        try:
            # Build API parameters
            params = {}
            if status_filter:
                params["status"] = status_filter
            if day_filter:
                params["day"] = day_filter
            
            # Get schedules from API
            schedules = api_request(
                "GET", 
                f"/api/caregivers/{caregiver_id}/schedules", 
                params=params,
                token=None  # No token since endpoints are permitAll
            ) or []
            
            # Handle API response structure
            if isinstance(schedules, dict):
                if "data" in schedules:
                    schedules = schedules["data"]
                elif "schedules" in schedules:
                    schedules = schedules["schedules"]
                else:
                    schedules = []
            
            if not isinstance(schedules, list):
                schedules = []
            
            # Transform schedule data for template
            transformed_schedules = []
            for schedule in schedules:
                try:
                    transformed_schedule = {
                        'id': schedule.get('id'),
                        'date': schedule.get('date', 'N/A'),
                        'day': schedule.get('day', 'N/A'),
                        'startTime': schedule.get('startTime', schedule.get('start_time', 'N/A')),
                        'endTime': schedule.get('endTime', schedule.get('end_time', 'N/A')),
                        'status': schedule.get('status', 'UNKNOWN').upper(),
                    }
                    transformed_schedules.append(transformed_schedule)
                except Exception as e:
                    print(f"Error transforming schedule: {e}")
                    continue
            
            context = {
                'schedules': transformed_schedules,
                'caregiver_id': caregiver_id,
                'status_filter': status_filter,
                'day_filter': day_filter,
                'is_logged_in': True,
                'user_role': 'caregiver',
                'user_id': caregiver_id,
                'total_schedules': len(transformed_schedules),
            }
            
            return render(request, self.template_name, context)
            
        except Exception as e:
            print(f"Error loading schedules: {e}")
            messages.error(request, f"Error loading schedules: {str(e)}")
            
            context = {
                'schedules': [],
                'caregiver_id': caregiver_id,
                'status_filter': status_filter,
                'day_filter': day_filter,
                'is_logged_in': True,
                'user_role': 'caregiver',
                'user_id': caregiver_id,
                'total_schedules': 0,
                'error': str(e)
            }
            
            return render(request, self.template_name, context)

@method_decorator(csrf_exempt, name='dispatch')
class ScheduleDeleteView(View):
    def post(self, request, caregiver_id, schedule_id):
        if not is_logged_in(request):
            messages.error(request, "Please login first")
            return redirect("main:login")
        
        # Check if user is caregiver and matches caregiver_id
        if (request.session.get("user_role") != "caregiver" or 
            request.session.get("user_id") != caregiver_id):
            messages.error(request, "Access denied")
            return redirect("main:home")
        
        token = request.session.get("access_token")
        
        try:
            # Delete schedule via API
            response = api_request(
                "DELETE", 
                f"/api/caregivers/{caregiver_id}/schedules/{schedule_id}",
                token=None  # No token since endpoints are permitAll
            )
            
            messages.success(request, "Schedule deleted successfully")
            
        except Exception as e:
            print(f"Error deleting schedule: {e}")
            messages.error(request, f"Error deleting schedule: {str(e)}")
        
        return redirect("schedule_list", caregiver_id=caregiver_id)

@method_decorator(csrf_exempt, name='dispatch')
class ScheduleCreateView(View):
    template_name = 'schedule_create.html'
    
    def get(self, request, caregiver_id):
        if not is_logged_in(request):
            messages.error(request, "Please login first")
            return redirect("main:login")
        
        # Check if user is caregiver and matches caregiver_id
        if (request.session.get("user_role") != "caregiver" or 
            request.session.get("user_id") != caregiver_id):
            messages.error(request, "Access denied")
            return redirect("main:home")
        
        context = {
            'caregiver_id': caregiver_id,
            'is_logged_in': True,
            'user_role': 'caregiver',
            'user_id': caregiver_id,
            'days': ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request, caregiver_id):
        if not is_logged_in(request):
            messages.error(request, "Please login first")
            return redirect("main:login")
        
        # Check if user is caregiver and matches caregiver_id
        if (request.session.get("user_role") != "caregiver" or 
            request.session.get("user_id") != caregiver_id):
            messages.error(request, "Access denied")
            return redirect("main:home")
        
        token = request.session.get("access_token")
        
        # Get form data
        day = request.POST.get('day')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        weeks = request.POST.get('weeks', '')
        create_multiple = request.POST.get('create_multiple', '') == 'on'
        
        # Validation
        if not all([day, start_time, end_time]):
            messages.error(request, "Please fill in all required fields")
            return redirect("schedule_create", caregiver_id=caregiver_id)
        
        try:
            # Prepare API data
            schedule_data = {
                "day": day.upper(),
                "startTime": start_time,
                "endTime": end_time
            }
            
            if weeks and weeks.isdigit():
                schedule_data["weeks"] = int(weeks)
            
            # Choose endpoint based on create_multiple option
            endpoint = f"/api/caregivers/{caregiver_id}/schedules"
            if create_multiple:
                endpoint += "/interval"
            
            # Create schedule via API
            response = api_request(
                "POST", 
                endpoint,
                data=schedule_data,
                token=None  # No token since endpoints are permitAll
            )
            
            messages.success(request, "Schedule created successfully")
            return redirect("schedule_list", caregiver_id=caregiver_id)
            
        except Exception as e:
            print(f"Error creating schedule: {e}")
            messages.error(request, f"Error creating schedule: {str(e)}")
            return redirect("schedule_create", caregiver_id=caregiver_id)