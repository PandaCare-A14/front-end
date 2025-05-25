# reservasi_pacilian/views.py
import os
import requests
import json
import base64
import datetime
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.conf import settings
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.utils.decorators import method_decorator

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080")
SPRINGBOOT_API_URL = f"{API_BASE_URL}/api/reservasi-konsultasi"

def is_logged_in(request):
    return bool(request.session.get("access_token"))

def validate_session(request):
    required_keys = ['access_token', 'user_id', 'user_role']
    return all(request.session.get(key) for key in required_keys)

def clear_session_and_redirect(request, message="Session expired. Please login again."):
    request.session.flush()
    messages.error(request, message)
    return redirect("main:login")

def get_user_context(request):
    """Get user context from session"""
    return {
        'is_logged_in': is_logged_in(request),
        'user_role': request.session.get("user_role", 'guest'),
        'user_id': request.session.get("user_id")
    }

def api_request(method, endpoint, data=None, token=None, params=None):
    """Make API requests with proper error handling"""
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
            if not response.text or response.text.strip() == "":
                return None
            
            try:
                return response.json()
            except json.JSONDecodeError:
                return response.text if response.text else {"success": True}
        elif response.status_code in [401, 403]:
            raise PermissionError(f"Unauthorized: {response.text}")
        else:
            raise Exception(f"API error {response.status_code}: {response.text}")
            
    except requests.exceptions.Timeout:
        raise Exception("Request timeout - server may be down")
    except requests.exceptions.ConnectionError:
        raise Exception("Connection error - cannot reach server")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Network Error: {str(e)}")
    except PermissionError:
        raise
    except Exception as e:
        raise Exception(f"API Error: {str(e)}")


# GET: Lihat semua reservasi pasien (dari Spring Boot)
def list_reservasi(request, id_pacilian):
    # FIRST DEBUG - Check if function is called at all
    print(f"FUNCTION CALLED: list_reservasi with id_pacilian={id_pacilian}")
    print(f"REQUEST METHOD: {request.method}")
    print(f"REQUEST PATH: {request.path}")
    
    # Check if user is logged in and has proper permissions
    print(f"=== DEBUG: User trying to access reservations for Pacilian ID {id_pacilian} ===")
    if not is_logged_in(request):
        print("❌ User not logged in, redirecting to login")
        messages.error(request, "Please login first")
        return redirect("main:login")
    
    user_context = get_user_context(request)
    user_role = user_context.get('user_role')
    session_user_id = user_context.get('user_id')
    
    # Verify user has permission to view this data
    if user_role != 'pacilian':
        messages.error(request, "Access denied")
        return redirect("main:home")
    
    if user_role == 'pacilian':
        print(f"User {session_user_id} is viewing their own reservations")
      # For security, ensure user can only view their own reservations
    if str(session_user_id) != str(id_pacilian):
        messages.error(request, "You can only view your own reservations")
        return redirect("main:pacilian_dashboard")
    
    token = request.session.get("access_token")
    
    try:
        # Try to get data from API
        endpoint = f"/api/reservasi-konsultasi/{id_pacilian}"
          # Debug information
        print(f"=== API REQUEST DEBUG ===")
        print(f"Endpoint: {endpoint}")
        print(f"Full URL: {API_BASE_URL}{endpoint}")
        print(f"Token exists: {bool(token)}")
        print(f"Token preview: {token[:50] if token else 'None'}...")
        print(f"User ID: {session_user_id}")
        print(f"Pacilian ID: {id_pacilian}")
          # Test if Spring Boot backend is reachable
        try:
            test_response = requests.get(f"{API_BASE_URL}/health", timeout=5)
            print(f"Backend health check: {test_response.status_code}")
        except:
            print("Backend health check failed - backend may be down")
        
        data = api_request("GET", endpoint, token=token)
        
        # Debug the API response structure
        print(f"=== API RESPONSE DEBUG ===")
        print(f"Response type: {type(data)}")
        print(f"Response data: {data}")
        if isinstance(data, list) and len(data) > 0:
            print(f"First item structure: {data[0]}")
            print(f"First item keys: {list(data[0].keys()) if isinstance(data[0], dict) else 'Not a dict'}")
        
        context = {
            "reservasis": data,
            "user_id": id_pacilian,
            **user_context
        }
        return render(request, "list.html", context)
        
    except Exception as e:
        # Log the API error for debugging
        print(f"API Error: {str(e)}")
        print(f"API Error Type: {type(e).__name__}")
        
        # Check if this is an authentication issue
        if "Unauthorized" in str(e) or "401" in str(e):
            print("AUTHENTICATION FAILED - Token may be expired or invalid")
            messages.error(request, "Authentication failed. Please login again.")
            return redirect("main:login")
          # For other API errors, show error message
        messages.error(request, f"Failed to load reservations: {str(e)}")
        context = {
            "reservasis": [],
            "user_id": id_pacilian,
            "error_message": str(e),
            **user_context
        }
        return render(request, "list.html", context)


# GET/POST: Create new reservation
def request_reservasi(request):
    if not is_logged_in(request):
        messages.error(request, "Please login first")
        return redirect("main:login")
    
    user_context = get_user_context(request)
    if user_context.get('user_role') != 'pacilian':
        messages.error(request, "Access denied")
        return redirect("main:home")
    
    if request.method == "POST":
        id_schedule = request.POST.get("idSchedule")
        id_pacilian = user_context.get('user_id') # Use session user_id for security
        
        if not id_schedule:
            messages.error(request, "Schedule is required")
            return render(request, "request.html", user_context)
        
        data = {
            "idSchedule": id_schedule,
            "idPacilian": id_pacilian,
        }
        
        try:
            token = request.session.get("access_token")
            endpoint = "/api/reservasi-konsultasi/request"
            response = api_request("POST", endpoint, data=data, token=token)
            
            messages.success(request, "Reservation created successfully")
            return redirect("pacilian_reservasi_list", id_pacilian=id_pacilian)
            
        except Exception as e:
            messages.error(request, f"Failed to create reservation: {str(e)}")
            return render(request, "request.html", user_context)
    
    # GET request - show form
    return render(request, "request.html", user_context)

# GET: List available doctors/caregivers
def list_doctors(request):
    if not is_logged_in(request):
        messages.error(request, "Please login first")
        return redirect("main:login")
    
    user_context = get_user_context(request)
    if user_context.get('user_role') != 'pacilian':
        messages.error(request, "Access denied")
        return redirect("main:home")
    
    token = request.session.get("access_token")
    
    try:
        # Get list of doctors/caregivers from API
        endpoint = "/api/caregivers"
        doctors_response = api_request("GET", endpoint, token=token)
        
        doctors = []
        if doctors_response:
            if isinstance(doctors_response, dict):
                if "data" in doctors_response:
                    doctors = doctors_response["data"]
                elif "caregivers" in doctors_response:
                    doctors = doctors_response["caregivers"]
                elif "results" in doctors_response:
                    doctors = doctors_response["results"]
                else:
                    doctors = [doctors_response]
            elif isinstance(doctors_response, list):
                doctors = doctors_response
        
        if not isinstance(doctors, list):
            doctors = []
        
        context = {
            "doctors": doctors,
            **user_context
        }
        return render(request, "doctor_list.html", context)
        
    except Exception as e:
        print(f"API Error loading doctors: {str(e)}")
        messages.error(request, f"Failed to load doctors: {str(e)}")
        context = {
            "doctors": [],
            "error_message": str(e),
            **user_context
        }
        return render(request, "doctor_list.html", context)

# POST: Accept schedule change
@csrf_exempt
def accept_change(request, id):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    if not is_logged_in(request):
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    user_context = get_user_context(request)
    if user_context.get('user_role') != 'pacilian':
        return JsonResponse({"error": "Access denied"}, status=403)
    
    try:
        token = request.session.get("access_token")
        endpoint = f"/api/reservasi-konsultasi/{id}/accept-change"
        response = api_request("POST", endpoint, token=token)
        
        return JsonResponse({"success": True, "message": "Change accepted successfully"})
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

# POST: Reject schedule change
@csrf_exempt
def reject_change(request, id):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    if not is_logged_in(request):
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    user_context = get_user_context(request)
    if user_context.get('user_role') != 'pacilian':
        return JsonResponse({"error": "Access denied"}, status=403)
    
    try:
        token = request.session.get("access_token")
        endpoint = f"/api/reservasi-konsultasi/{id}/reject-change"
        response = api_request("POST", endpoint, token=token)
        
        return JsonResponse({"success": True, "message": "Change rejected successfully"})
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    
# Update your DoctorScheduleListView in views.py
@method_decorator(csrf_exempt, name='dispatch')
class DoctorScheduleListView(View):
    template_name = 'doctor_schedules.html'
    
    def get(self, request, caregiver_id):
        if not is_logged_in(request):
            messages.error(request, "Please login first")
            return redirect("main:login")
        
        user_context = get_user_context(request)
        if user_context.get('user_role') != 'pacilian':
            messages.error(request, "Access denied")
            return redirect("main:home")
        
        token = request.session.get("access_token")
        reservation_id = request.GET.get('reservation_id')
        
        try:
            # Call the Spring Boot API endpoint with AVAILABLE status filter
            # This matches your controller: /api/caregivers/{idCaregiver}/schedules?status=AVAILABLE
            params = {"status": "AVAILABLE"}
            
            print(f"=== SCHEDULE API DEBUG ===")
            print(f"Caregiver ID: {caregiver_id}")
            print(f"API Endpoint: /api/caregivers/{caregiver_id}/schedules")
            print(f"Params: {params}")
            print(f"Token exists: {bool(token)}")
            
            schedules_response = api_request(
                "GET", 
                f"/api/caregivers/{caregiver_id}/schedules", 
                params=params,
                token=token
            )
            
            print(f"API Response: {schedules_response}")
            
            # Parse the response based on your Spring Boot ApiResponse structure
            schedules = []
            if schedules_response:
                if isinstance(schedules_response, dict):
                    # Your Spring Boot returns ApiResponse with 'data' field
                    if "data" in schedules_response:
                        schedules = schedules_response["data"]
                    else:
                        schedules = [schedules_response]
                elif isinstance(schedules_response, list):
                    schedules = schedules_response
            
            # Ensure schedules is a list
            if not isinstance(schedules, list):
                schedules = []
            
            print(f"Parsed schedules count: {len(schedules)}")
            
            # Transform the schedule data to match your template expectations
            available_schedules = []
            for schedule in schedules:
                try:
                    transformed_schedule = {
                        'id': schedule.get('id', ''),
                        'date': schedule.get('date', ''),
                        'day': schedule.get('day', ''),
                        'startTime': schedule.get('startTime', ''),
                        'endTime': schedule.get('endTime', ''),
                        'status': schedule.get('status', 'UNKNOWN').upper(),
                    }
                    available_schedules.append(transformed_schedule)
                    print(f"Schedule: {transformed_schedule}")
                except Exception as e:
                    print(f"Error processing schedule: {e}")
                    continue
            
            context = {
                'schedules': available_schedules,
                'caregiver_id': str(caregiver_id),
                'reservation_id': reservation_id,
                'is_edit_mode': bool(reservation_id),
                'total_schedules': len(available_schedules),
                **user_context
            }
            
            return render(request, self.template_name, context)
            
        except Exception as e:
            print(f"Error loading doctor schedules: {str(e)}")
            messages.error(request, f"Error loading doctor schedules: {str(e)}")
            
            context = {
                'schedules': [],
                'caregiver_id': str(caregiver_id),
                'reservation_id': reservation_id,
                'is_edit_mode': bool(reservation_id),
                'total_schedules': 0,
                'error': str(e),
                **user_context
            }
            
            return render(request, self.template_name, context)