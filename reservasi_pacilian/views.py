import os
import requests
import json
import base64
import datetime
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.conf import settings
from django.contrib import messages
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
import traceback

API_BASE_URL = os.getenv("API_BASE_URL")
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
    return {
        'is_logged_in': is_logged_in(request),
        'user_role': request.session.get("user_role", 'guest'),
        'user_id': request.session.get("user_id")
    }

def require_auth(view_func):
    def wrapper(request, *args, **kwargs):
        if not is_logged_in(request):
            if request.content_type == 'application/json':
                return JsonResponse({"error": "Authentication required"}, status=401)
            messages.error(request, "Please login first")
            return redirect("main:login")
        return view_func(request, *args, **kwargs)
    return wrapper

def require_pacilian_role(view_func):
    def wrapper(request, *args, **kwargs):
        user_context = get_user_context(request)
        if user_context.get('user_role') != 'pacilian':
            if request.content_type == 'application/json':
                return JsonResponse({"error": "Access denied"}, status=403)
            messages.error(request, "Access denied")
            return redirect("main:home")
        return view_func(request, *args, **kwargs)
    return wrapper

def require_pacilian_auth(view_func):
    return require_auth(require_pacilian_role(view_func))

class APIHandler:
    @staticmethod
    def request(method, endpoint, data=None, token=None, params=None):
        if not API_BASE_URL:
            raise Exception("API_BASE_URL environment variable not set")

        url = f"{API_BASE_URL}{endpoint}"
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            request_kwargs = {
                'method': method,
                'url': url,
                'headers': headers,
                'timeout': 30
            }
            
            if method.upper() == "GET" and params:
                request_kwargs['params'] = params
            elif data is not None:
                request_kwargs['json'] = data

            response = requests.request(**request_kwargs)
            return APIHandler._handle_response(response)

        except requests.exceptions.Timeout:
            raise Exception("Request timeout - server may be down")
        except requests.exceptions.ConnectionError:
            raise Exception("Connection error - cannot reach server")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network Error: {str(e)}")

    @staticmethod
    def _handle_response(response):
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

    @staticmethod
    def debug_request(endpoint, id_param=None, token=None):
        print(f"=== API REQUEST DEBUG ===")
        print(f"Endpoint: {endpoint}")
        print(f"Full URL: {API_BASE_URL}{endpoint}")
        print(f"Token exists: {bool(token)}")
        print(f"Token preview: {token[:50] if token else 'None'}...")
        if id_param:
            print(f"ID Parameter: {id_param}")
        
        try:
            test_response = requests.get(f"{API_BASE_URL}/health", timeout=5)
            print(f"Backend health check: {test_response.status_code}")
        except:
            print("Backend health check failed - backend may be down")

class ResponseHandler:
    @staticmethod
    def handle_api_error(e, request, fallback_redirect="main:home", context_data=None):
        print(f"API Error: {str(e)}")
        print(f"API Error Type: {type(e).__name__}")
        
        if "Unauthorized" in str(e) or "401" in str(e):
            print("AUTHENTICATION FAILED - Token may be expired or invalid")
            messages.error(request, "Authentication failed. Please login again.")
            return redirect("main:login")
        
        error_message = f"Failed to load data: {str(e)}"
        messages.error(request, error_message)
        
        if context_data:
            context_data.update({
                "error_message": str(e),
                **get_user_context(request)
            })
            return render(request, context_data.get('template', 'error.html'), context_data)
        
        return redirect(fallback_redirect)

    @staticmethod
    def json_response(success=True, message="", data=None, error=None, status=200):
        response_data = {"success": success}
        if message:
            response_data["message"] = message
        if data is not None:
            response_data["data"] = data
        if error:
            response_data["error"] = error
        return JsonResponse(response_data, status=status)

class PermissionChecker:
    @staticmethod
    def can_access_reservations(request, id_pacilian):
        user_context = get_user_context(request)
        session_user_id = user_context.get('user_id')
        
        if str(session_user_id) != str(id_pacilian):
            messages.error(request, "You can only view your own reservations")
            return False
        return True

@require_http_methods(["GET"])
@require_pacilian_auth
def list_reservasi(request, id_pacilian):
    print(f"FUNCTION CALLED: list_reservasi with id_pacilian={id_pacilian}")
    
    if not PermissionChecker.can_access_reservations(request, id_pacilian):
        return redirect("main:pacilian_dashboard")

    token = request.session.get("access_token")
    endpoint = f"/api/reservasi-konsultasi/{id_pacilian}"
    
    try:
        APIHandler.debug_request(endpoint, id_pacilian, token)
        data = APIHandler.request("GET", endpoint, token=token)
        
        print(f"=== API RESPONSE DEBUG ===")
        print(f"Response type: {type(data)}")
        print(f"Response data: {data}")
        
        context = {
            "reservasis": data,
            "user_id": id_pacilian,
            **get_user_context(request)
        }
        return render(request, "list.html", context)

    except Exception as e:
        context_data = {
            "reservasis": [],
            "user_id": id_pacilian,
            "template": "list.html"
        }
        return ResponseHandler.handle_api_error(e, request, "main:pacilian_dashboard", context_data)

@require_http_methods(["POST"])
@require_pacilian_auth
def accept_change(request, id):
    return _handle_change_request(request, id, "accept-change", "Change accepted successfully")

@require_http_methods(["POST"])
@require_pacilian_auth
def reject_change(request, id):
    return _handle_change_request(request, id, "reject-change", "Change rejected successfully")

def _handle_change_request(request, id, action, success_message):
    try:
        token = request.session.get("access_token")
        endpoint = f"/api/reservasi-konsultasi/{id}/{action}"
        response = APIHandler.request("POST", endpoint, token=token)
        return ResponseHandler.json_response(message=success_message)
    except Exception as e:
        return ResponseHandler.json_response(success=False, error=str(e), status=500)

@require_pacilian_auth
def get_available_schedules(request, caregiver_id):
    try:
        token = request.session.get("access_token")
        print(f"Fetching available schedules for caregiver: {caregiver_id}")

        response = APIHandler.request("GET", f"/api/caregivers/{caregiver_id}/schedules", token=token)

        schedules = []
        if response and response.get('status') == 200:
            raw_schedules = response.get('data', [])
            schedules = [
                {
                    'id': schedule.get('id'),
                    'date': schedule.get('date'),
                    'day': schedule.get('day'),
                    'startTime': schedule.get('startTime'),
                    'endTime': schedule.get('endTime'),
                    'status': schedule.get('status'),
                    'caregiverId': str(caregiver_id)
                }
                for schedule in raw_schedules
                if schedule.get('status', '').upper() == 'AVAILABLE'
            ]

        return ResponseHandler.json_response(
            data=schedules,
            message=f"Found {len(schedules)} available schedules"
        )

    except Exception as e:
        print(f"Error in get_available_schedules: {e}")
        return ResponseHandler.json_response(success=False, error=str(e), status=500)

@method_decorator(csrf_exempt, name='dispatch')
class AvailableScheduleListView(View):
    template_name = 'available_schedules.html'

    @method_decorator(require_pacilian_auth)
    def get(self, request, caregiver_id):
        reservation_id = request.GET.get('reservation_id')
        
        try:
            schedules, caregiver_info = self._fetch_schedules_and_caregiver(request, caregiver_id)
            
            context = {
                'schedules': schedules,
                'caregiver_id': str(caregiver_id),
                'caregiver_info': caregiver_info,
                'reservation_id': reservation_id,
                'is_edit_mode': bool(reservation_id),
                'total_schedules': len(schedules),
                **get_user_context(request)
            }
            
            self._debug_context(context)
            return render(request, self.template_name, context)

        except Exception as e:
            self._debug_error(e)
            context_data = {
                'schedules': [],
                'caregiver_id': str(caregiver_id),
                'reservation_id': reservation_id,
                'is_edit_mode': bool(reservation_id),
                'total_schedules': 0,
                'template': self.template_name
            }
            return ResponseHandler.handle_api_error(e, request, "main:home", context_data)

    @method_decorator(require_pacilian_auth)
    def post(self, request, caregiver_id):
        print(f"=== POST REQUEST TO AvailableScheduleListView ===")
        
        schedule_id = request.POST.get('schedule_id')
        reservation_id = request.POST.get('reservation_id')
        
        if not schedule_id:
            messages.error(request, "Please select a schedule")
            return redirect('available_schedules_html', caregiver_id=caregiver_id)

        try:
            if reservation_id:
                success = self._edit_reservation(request, reservation_id, schedule_id)
            else:
                success = self._create_reservation(request, schedule_id)
            
            if success:
                pacilian_id = get_user_context(request).get('user_id')
                return redirect("reservasi_pacilian:pacilian_reservasi_list", id_pacilian=pacilian_id)
            
        except Exception as e:
            self._handle_post_error(e, request)
        
        return redirect('available_schedules_html', caregiver_id=caregiver_id)

    def _fetch_schedules_and_caregiver(self, request, caregiver_id):
        token = request.session.get("access_token")
        
        response = APIHandler.request("GET", f"/api/caregivers/{caregiver_id}/schedules", token=token)
        
        schedules = []
        if response and response.get('status') == 200:
            raw_schedules = response.get('data', [])
            schedules = [
                {
                    'id': schedule.get('id'),
                    'date': schedule.get('date'),
                    'day': schedule.get('day'),
                    'startTime': schedule.get('startTime'),
                    'endTime': schedule.get('endTime'),
                    'status': schedule.get('status'),
                    'caregiverId': str(caregiver_id)
                }
                for schedule in raw_schedules
                if schedule.get('status', '').upper() == 'AVAILABLE'
            ]
        
        caregiver_info = None
        try:
            caregiver_response = APIHandler.request("GET", f"/api/caregivers/{caregiver_id}", token=token)
            if caregiver_response and caregiver_response.get('status') == 200:
                caregiver_info = caregiver_response.get('data', caregiver_response)
        except Exception as e:
            print(f"Could not fetch caregiver info: {e}")
        
        return schedules, caregiver_info

    def _edit_reservation(self, request, reservation_id, schedule_id):
        print(f"=== EDITING RESERVATION {reservation_id} ===")
        
        data = {"idSchedule": str(schedule_id)}
        endpoint = f"/api/reservasi-konsultasi/{reservation_id}/edit"
        token = request.session.get("access_token")
        
        response = APIHandler.request("POST", endpoint, data=data, token=token)
        
        if response and isinstance(response, dict):
            if response.get('message') and 'updated successfully' in response.get('message', '').lower():
                messages.success(request, "Reservation schedule updated successfully!")
                return True
            else:
                error_msg = response.get('error', 'Unknown error occurred')
                messages.error(request, f"Failed to update reservation: {error_msg}")
        else:
            messages.error(request, 'Failed to update reservation: Invalid response')
        
        return False

    def _create_reservation(self, request, schedule_id):
        print(f"=== CREATING NEW RESERVATION ===")
        
        pacilian_id = get_user_context(request).get('user_id')
        data = {
            "idSchedule": str(schedule_id),
            "idPacilian": str(pacilian_id),
        }
        endpoint = "/api/reservasi-konsultasi/request"
        token = request.session.get("access_token")
        
        response = APIHandler.request("POST", endpoint, data=data, token=token)
        
        if response and isinstance(response, dict):
            message = response.get('message', '').lower()
            if 'berhasil diajukan' in message or 'success' in message:
                messages.success(request, "Reservation created successfully!")
                return True
            else:
                error_msg = response.get('error', 'Unknown error occurred')
                messages.error(request, f"Failed to create reservation: {error_msg}")
        else:
            messages.success(request, "Reservation created successfully!")
            return True
        
        return False

    def _handle_post_error(self, e, request):
        error_str = str(e).lower()
        
        if "not available" in error_str or "tidak tersedia" in error_str:
            messages.error(request, "Selected schedule is not available")
        elif "not found" in error_str or "tidak ditemukan" in error_str:
            messages.error(request, "Schedule not found")
        elif "sudah disetujui" in error_str or "already approved" in error_str:
            messages.error(request, "Cannot edit reservation that has already been approved")
        elif "unauthorized" in error_str or "401" in error_str:
            messages.error(request, "Authentication failed. Please login again.")
        else:
            messages.error(request, f"Failed to process request: {str(e)}")

    def _debug_context(self, context):
        print(f"=== TEMPLATE CONTEXT ===")
        print(f"Schedules count: {len(context['schedules'])}")
        print(f"Is edit mode: {context['is_edit_mode']}")
        print(f"Caregiver ID: {context['caregiver_id']}")

    def _debug_error(self, e):
        print(f"=== ERROR in AvailableScheduleListView ===")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")

class ReservationRequestView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    @method_decorator(require_auth)
    def post(self, request):
        try:
            data = {
                "idSchedule": request.POST.get("schedule_id"),
                "idPacilian": request.session.get("user_id")
            }
            print(f"{data.get('idSchedule')=}, {data.get('idPacilian')=}")
            
            response = APIHandler.request(
                "POST",
                "/api/reservasi-konsultasi/request",
                data=data,
                token=request.session.get("access_token")
            )
            
            if response and "reservasi" in response:
                messages.success(request, response.get("message", "Reservation requested successfully"))
                return redirect("doctor_profile:reservation_detail", reservation_id=response["reservasi"]["idReservasi"])
            else:
                messages.error(request, response.get("error", "Failed to request reservation"))
                return redirect(request.META.get('HTTP_REFERER', 'doctor_profile:search'))
                
        except Exception as e:
            messages.error(request, f"Error requesting reservation: {str(e)}")
            print(f"Error in ReservationRequestView: {str(e)}")
            return redirect(request.META.get('HTTP_REFERER', 'doctor_profile:search'))