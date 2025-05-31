from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import requests
import os
import json
from datetime import datetime
from functools import wraps

API_BASE_URL = os.getenv("API_BASE_URL")

class Auth:
    @staticmethod
    def get_session_data(request):
        return {
            'token': request.session.get("access_token"),
            'user_id': request.session.get("user_id"),
            'user_role': request.session.get("user_role")
        }
    
    @staticmethod
    def is_logged_in(request):
        return bool(request.session.get("access_token"))
    
    @staticmethod
    def validate_session(request):
        required_keys = ['access_token', 'user_id', 'user_role']
        return all(request.session.get(key) for key in required_keys)
    
    @staticmethod
    def clear_session_and_redirect(request, message="Session expired. Please login again."):
        request.session.flush()
        messages.error(request, message)
        return redirect("main:login")

class APIClient:
    @staticmethod
    def request(method, endpoint, data=None, token=None, params=None):
        if not API_BASE_URL:
            raise Exception("API_BASE_URL environment variable not set")
        
        url = f"{API_BASE_URL}{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        try:
            kwargs = {"headers": headers, "timeout": 30}
            
            if method.upper() == "GET" and params:
                kwargs["params"] = params
            elif data is not None:
                kwargs["json"] = data
                
            response = requests.request(method, url, **kwargs)
            
            if response.status_code in [200, 201, 204]:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    return response.text if response.text else {"success": True}
            elif response.status_code == 401:
                raise PermissionError("Session expired. Please login again.")
            elif response.status_code == 403:
                raise PermissionError(f"Access denied: {response.text}")
            else:
                raise Exception(f"API error {response.status_code}: {response.text}")
                
        except requests.exceptions.Timeout:
            raise Exception("Request timeout - server may be down")
        except requests.exceptions.ConnectionError:
            raise Exception("Connection error - cannot reach server")
        except Exception as e:
            if isinstance(e, PermissionError):
                raise
            raise Exception(f"API Error: {str(e)}")

class ScheduleTransformer:
    @staticmethod
    def extract_schedules(response):
        if not response:
            return []
        
        if isinstance(response, list):
            return response
        
        if isinstance(response, dict):
            for key in ["data", "schedules", "results"]:
                if key in response and isinstance(response[key], list):
                    return response[key]
            return [response]
        
        return []
    
    @staticmethod
    def transform_schedule(schedule):
        try:
            return {
                'id': schedule.get('id', ''),
                'date': schedule.get('date', schedule.get('schedule_date', '')),
                'day': schedule.get('day', schedule.get('schedule_day', '')),
                'startTime': schedule.get('startTime', schedule.get('start_time', '')),
                'endTime': schedule.get('endTime', schedule.get('end_time', '')),
                'status': schedule.get('status', 'UNKNOWN').upper(),
            }
        except Exception:
            return None
    
    @staticmethod
    def transform_all(response):
        schedules = ScheduleTransformer.extract_schedules(response)
        return [s for s in [ScheduleTransformer.transform_schedule(sch) for sch in schedules] if s]

def require_caregiver_auth(view_func):
    @wraps(view_func)
    def wrapper(self, request, caregiver_id, *args, **kwargs):
        if not Auth.is_logged_in(request):
            if request.content_type == 'application/json':
                return JsonResponse({"error": "Please login first", "redirect": "/login/"}, status=401)
            return Auth.clear_session_and_redirect(request, "Please login first")
        
        if not Auth.validate_session(request):
            if request.content_type == 'application/json':
                return JsonResponse({"error": "Session expired", "redirect": "/login/"}, status=401)
            return Auth.clear_session_and_redirect(request)
        
        session_data = Auth.get_session_data(request)
        if (session_data['user_role'] != "caregiver" or str(session_data['user_id']) != str(caregiver_id)):
            if request.content_type == 'application/json':
                return JsonResponse({"error": "Access denied"}, status=403)
            messages.error(request, "Access denied")
            return redirect("main:home")
        
        return view_func(self, request, caregiver_id, *args, **kwargs)
    return wrapper

@method_decorator(csrf_exempt, name='dispatch')
class ScheduleListView(View, Auth):
    template_name = 'schedule_list.html'
    
    @require_caregiver_auth
    def get(self, request, caregiver_id):
        session_data = self.get_session_data(request)
        status_filter = request.GET.get("status", "").strip()
        day_filter = request.GET.get("day", "").strip()
        
        try:
            params = {}
            if status_filter:
                params["status"] = status_filter
            if day_filter:
                params["day"] = day_filter
            
            schedules_response = APIClient.request(
                "GET", 
                f"/api/caregivers/{caregiver_id}/schedules", 
                params=params,
                token=session_data['token']
            )
            
            schedules = ScheduleTransformer.transform_all(schedules_response)
            
            context = {
                'schedules': schedules,
                'caregiver_id': str(caregiver_id),
                'user_id': str(caregiver_id),
                'status_filter': status_filter,  
                'day_filter': day_filter,
                'is_logged_in': True,
                'user_role': 'caregiver',
                'total_schedules': len(schedules),
            }
            
            return render(request, self.template_name, context)
            
        except PermissionError as e:
            return self.clear_session_and_redirect(request, str(e))
        except Exception as e:
            messages.error(request, f"Error loading schedules: {str(e)}")
            
            context = {
                'schedules': [],
                'caregiver_id': str(caregiver_id),
                'user_id': str(caregiver_id),
                'status_filter': status_filter,
                'day_filter': day_filter,
                'is_logged_in': True,
                'user_role': 'caregiver',
                'total_schedules': 0,
                'error': str(e)
            }
            
            return render(request, self.template_name, context)

@method_decorator(csrf_exempt, name='dispatch')
class ScheduleDeleteView(View, Auth):
    @require_caregiver_auth
    def post(self, request, caregiver_id, schedule_id):
        session_data = self.get_session_data(request)
        
        try:
            APIClient.request(
                "DELETE", 
                f"/api/caregivers/{caregiver_id}/schedules/{schedule_id}",
                token=session_data['token']
            )
            
            messages.success(request, "Schedule deleted successfully")
            
        except PermissionError as e:
            return self.clear_session_and_redirect(request, str(e))
        except Exception as e:
            messages.error(request, f"Error deleting schedule: {str(e)}")
        
        return redirect("schedule:schedule_list", caregiver_id=caregiver_id)

class ScheduleValidator:
    @staticmethod
    def validate_json_data(body):
        day = body.get('day')
        start_time = body.get('startTime')
        end_time = body.get('endTime')
        
        if not all([day, start_time, end_time]):
            return False, "Please fill in all required fields"
        
        try:
            datetime.strptime(start_time, '%H:%M')
            datetime.strptime(end_time, '%H:%M')
        except ValueError:
            return False, "Please enter valid time format (HH:MM)"
        
        if start_time >= end_time:
            return False, "Start time must be before end time"
        
        return True, None

@method_decorator(csrf_exempt, name='dispatch')
class ScheduleCreateView(View, Auth):
    template_name = 'create_schedule.html'
    
    @require_caregiver_auth
    def get(self, request, caregiver_id):
        context = {
            'caregiver_id': str(caregiver_id),
            'user_id': str(caregiver_id),
            'is_logged_in': True,
            'user_role': 'caregiver',
            'days': ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']
        }
        
        return render(request, self.template_name, context)

    @require_caregiver_auth
    def post(self, request, caregiver_id):
        session_data = self.get_session_data(request)
        
        try:
            body = json.loads(request.body.decode("utf-8"))
        except Exception as e:
            return JsonResponse({"error": f"Invalid JSON input: {str(e)}"}, status=400)
        
        is_valid, error_message = ScheduleValidator.validate_json_data(body)
        if not is_valid:
            return JsonResponse({"error": error_message}, status=400)
        
        try:
            schedule_data = {
                "day": body.get('day').upper(),
                "startTime": body.get('startTime'),
                "endTime": body.get('endTime'),
                "status": "AVAILABLE"
            }
            
            weeks = body.get('weeks', '')
            if weeks and str(weeks).isdigit() and int(weeks) > 0:
                schedule_data["weeks"] = int(weeks)

            endpoint = f"/api/caregivers/{caregiver_id}/schedules"
            create_multiple = body.get('isInterval', False)
            if create_multiple and weeks:
                endpoint += "/interval"

            response = APIClient.request(
                "POST", 
                endpoint, 
                data=schedule_data, 
                token=session_data['token']
            )

            success_message = "Schedule created successfully"
            if create_multiple and weeks:
                success_message = f"Schedule created for {weeks} weeks successfully"

            return JsonResponse({
                "success": True,
                "message": success_message,
                "data": response
            }, status=201)

        except PermissionError as e:
            return JsonResponse({
                "error": str(e),
                "redirect": "/login/"
            }, status=401)
        except Exception as e:
            return JsonResponse({
                "error": f"Error creating schedule: {str(e)}"
            }, status=500)