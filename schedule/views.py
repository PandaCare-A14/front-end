from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import requests
import os
import json

API_BASE_URL = os.getenv("API_BASE_URL")

def is_logged_in(request):
    return bool(request.session.get("access_token"))

def validate_session(request):
    required_keys = ['access_token', 'user_id', 'user_role']
    return all(request.session.get(key) for key in required_keys)

def clear_session_and_redirect(request, message="Session expired. Please login again."):
    request.session.flush()
    messages.error(request, message)
    return redirect("main:login")

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
        raise Exception(f"API Error: {str(e)}")

@method_decorator(csrf_exempt, name='dispatch')
class ScheduleListView(View):
    template_name = 'schedule_list.html'
    
    def get(self, request, caregiver_id):
        if not is_logged_in(request):
            return clear_session_and_redirect(request, "Please login first")
        
        if not validate_session(request):
            return clear_session_and_redirect(request)
        
        if request.session.get("user_role") != "caregiver":
            messages.error(request, "Access denied")
            return redirect("main:home")
        
        if str(request.session.get("user_id")) != str(caregiver_id):
            messages.error(request, "Access denied")
            return redirect("main:home")
        
        token = request.session.get("access_token")
        status_filter = request.GET.get("status", "").strip()
        day_filter = request.GET.get("day", "").strip()
        
        try:
            params = {}
            if status_filter:
                params["status"] = status_filter
            if day_filter:
                params["day"] = day_filter
            
            schedules_response = api_request(
                "GET", 
                f"/api/caregivers/{caregiver_id}/schedules", 
                params=params,
                token=token
            )
            
            schedules = []
            if schedules_response:
                if isinstance(schedules_response, dict):
                    if "data" in schedules_response:
                        schedules = schedules_response["data"]
                    elif "schedules" in schedules_response:
                        schedules = schedules_response["schedules"]
                    elif "results" in schedules_response:
                        schedules = schedules_response["results"]
                    else:
                        schedules = [schedules_response]
                elif isinstance(schedules_response, list):
                    schedules = schedules_response
            
            if not isinstance(schedules, list):
                schedules = []
            
            transformed_schedules = []
            for schedule in schedules:
                try:
                    transformed_schedule = {
                        'id': schedule.get('id', ''),
                        'date': schedule.get('date', schedule.get('schedule_date', '')),
                        'day': schedule.get('day', schedule.get('schedule_day', '')),
                        'startTime': schedule.get('startTime', schedule.get('start_time', '')),
                        'endTime': schedule.get('endTime', schedule.get('end_time', '')),
                        'status': schedule.get('status', 'UNKNOWN').upper(),
                    }
                    transformed_schedules.append(transformed_schedule)
                except Exception:
                    continue
            
            context = {
                'schedules': transformed_schedules,
                'caregiver_id': str(caregiver_id),
                'user_id': str(caregiver_id),
                'status_filter': status_filter,  
                'day_filter': day_filter,
                'is_logged_in': True,
                'user_role': 'caregiver',
                'total_schedules': len(transformed_schedules),
            }
            
            return render(request, self.template_name, context)
            
        except PermissionError as e:
            return clear_session_and_redirect(request, str(e))
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
class ScheduleDeleteView(View):
    def post(self, request, caregiver_id, schedule_id):
        if not is_logged_in(request):
            return clear_session_and_redirect(request, "Please login first")
        
        if not validate_session(request):
            return clear_session_and_redirect(request)
        
        if (request.session.get("user_role") != "caregiver" or 
            str(request.session.get("user_id")) != str(caregiver_id)):
            messages.error(request, "Access denied")
            return redirect("main:home")
        
        token = request.session.get("access_token")
        
        try:
            api_request(
                "DELETE", 
                f"/api/caregivers/{caregiver_id}/schedules/{schedule_id}",
                token=token
            )
            
            messages.success(request, "Schedule deleted successfully")
            
        except PermissionError as e:
            return clear_session_and_redirect(request, str(e))
        except Exception as e:
            messages.error(request, f"Error deleting schedule: {str(e)}")
        
        return redirect("schedule:schedule_list", caregiver_id=caregiver_id)
    
@method_decorator(csrf_exempt, name='dispatch')
class ScheduleCreateView(View):
    template_name = 'create_schedule.html'
    
    def get(self, request, caregiver_id):
        if not is_logged_in(request):
            return clear_session_and_redirect(request, "Please login first")
        
        if not validate_session(request):
            return clear_session_and_redirect(request)
        
        if (request.session.get("user_role") != "caregiver" or 
            str(request.session.get("user_id")) != str(caregiver_id)):
            messages.error(request, "Access denied")
            return redirect("main:home")
        
        context = {
            'caregiver_id': str(caregiver_id),
            'user_id': str(caregiver_id),
            'is_logged_in': True,
            'user_role': 'caregiver',
            'days': ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']
        }
        
        return render(request, self.template_name, context)

    def post(self, request, caregiver_id):
        if not is_logged_in(request):
            return JsonResponse({"error": "Please login first", "redirect": "/login/"}, status=401)

        if not validate_session(request):
            return JsonResponse({"error": "Session expired", "redirect": "/login/"}, status=401)

        if (request.session.get("user_role") != "caregiver" or 
            str(request.session.get("user_id")) != str(caregiver_id)):
            return JsonResponse({"error": "Access denied"}, status=403)

        try:
            body = json.loads(request.body.decode("utf-8"))
            day = body.get('day')
            start_time = body.get('startTime')
            end_time = body.get('endTime')
            weeks = body.get('weeks', '')
            create_multiple = body.get('isInterval', False)
        except Exception as e:
            return JsonResponse({"error": f"Invalid JSON input: {str(e)}"}, status=400)
        
        if not all([day, start_time, end_time]):
            return JsonResponse({"error": "Please fill in all required fields"}, status=400)

        try:
            from datetime import datetime
            datetime.strptime(start_time, '%H:%M')
            datetime.strptime(end_time, '%H:%M')
        except ValueError:
            return JsonResponse({"error": "Please enter valid time format (HH:MM)"}, status=400)

        if start_time >= end_time:
            return JsonResponse({"error": "Start time must be before end time"}, status=400)

        try:
            schedule_data = {
                "day": day.upper(),
                "startTime": start_time,
                "endTime": end_time,
                "status": "AVAILABLE"
            }
            if weeks and str(weeks).isdigit() and int(weeks) > 0:
                schedule_data["weeks"] = int(weeks)

            endpoint = f"/api/caregivers/{caregiver_id}/schedules"
            if create_multiple and weeks:
                endpoint += "/interval"

            response = api_request(
                "POST", 
                endpoint, 
                data=schedule_data, 
                token=request.session.get("access_token")
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