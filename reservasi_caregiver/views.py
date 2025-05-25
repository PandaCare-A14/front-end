from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views import View
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import requests
import json
import os

API_BASE_URL = os.getenv("API_BASE_URL")

def is_logged_in(request):
    return bool(request.session.get("access_token"))

def validate_session(request):
    required_keys = ['access_token', 'user_id', 'user_role']
    for key in required_keys:
        if not request.session.get(key):
            return False
    return True

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
class CaregiverSchedulesView(View):
    def get(self, request, caregiver_id):
        if not is_logged_in(request):
            return JsonResponse({"error": "Please login first"}, status=401)

        if not validate_session(request):
            return JsonResponse({"error": "Session expired"}, status=401)

        if request.session.get("user_role") != "caregiver":
            return JsonResponse({"error": "Access denied"}, status=403)
        
        token = request.session.get("access_token")
        
        try:
            params = {}
            if request.GET.get('status'):
                params['status'] = request.GET.get('status')
            
            response = api_request(
                "GET",
                f"/api/caregivers/{caregiver_id}/schedules",
                params=params,
                token=token
            )
            
            return JsonResponse(response, safe=False)
                
        except Exception as e:
            return JsonResponse({"error": f"Error fetching schedules: {str(e)}"}, status=500)
        
class ReservationListView(View):
    template_name = "reservation_list.html"

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
        status_filter = request.GET.get('status', '')
        date_from = request.GET.get('date_from', '')

        try:
            params = {}
            if status_filter:
                params['status'] = status_filter
            if date_from:
                params['date_from'] = date_from
            
            reservations_response = api_request(
                "GET", 
                f"/api/caregivers/{caregiver_id}/reservations",
                params=params,
                token=token
            )
            
            reservations = []
            if reservations_response:
                if isinstance(reservations_response, dict):
                    if "data" in reservations_response:
                        reservations = reservations_response["data"]
                    elif "reservations" in reservations_response:
                        reservations = reservations_response["reservations"]
                    elif "results" in reservations_response:
                        reservations = reservations_response["results"]
                    else:
                        reservations = [reservations_response]
                elif isinstance(reservations_response, list):
                    reservations = reservations_response
            
            if not isinstance(reservations, list):
                reservations = []
                        
            context = {
                "reservations": reservations,
                "caregiver_id": str(caregiver_id),
                "user_id": str(caregiver_id),
                "status_filter": status_filter,
                "date_from": date_from,
                "is_waiting": status_filter == 'WAITING',
                "is_approved": status_filter == 'APPROVED',
                "is_rejected": status_filter == 'REJECTED',
                "is_rescheduled": status_filter == 'ON_RESCHEDULE',
                "is_logged_in": True,
                "user_role": "caregiver",
                "total_reservations": len(reservations),
            }
            
            return render(request, self.template_name, context)
            
        except PermissionError as e:
            return clear_session_and_redirect(request, str(e))
        except Exception as e:
            messages.error(request, f"Error loading reservations: {str(e)}")
            
            context = {
                "reservations": [],
                "caregiver_id": str(caregiver_id),
                "user_id": str(caregiver_id),
                "status_filter": status_filter,
                "date_from": date_from,
                "is_waiting": False,
                "is_approved": False,
                "is_rejected": False,
                "is_rescheduled": False,
                "is_logged_in": True,
                "user_role": "caregiver",
                "total_reservations": 0,
                "error": str(e)
            }
            
            return render(request, self.template_name, context)

@method_decorator(csrf_exempt, name='dispatch')
class ApproveReservationView(View):
    def post(self, request, reservation_id):
        if not is_logged_in(request):
            return JsonResponse({"error": "Please login first", "redirect": "/login/"}, status=401)

        if not validate_session(request):
            return JsonResponse({"error": "Session expired", "redirect": "/login/"}, status=401)

        if request.session.get("user_role") != "caregiver":
            return JsonResponse({"error": "Access denied"}, status=403)
        
        token = request.session.get("access_token")
        
        try:
            response = api_request(
                "PATCH",
                f"/api/caregivers/reservations/{reservation_id}/status",
                data={"status": "APPROVED"},
                token=token
            )
            
            return JsonResponse({"success": True, "message": "Reservation approved successfully"})
                
        except PermissionError as e:
            return JsonResponse({
                "error": str(e),
                "redirect": "/login/"
            }, status=401)
        except Exception as e:
            return JsonResponse({
                "error": f"Error approving reservation: {str(e)}"
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class RejectReservationView(View):
    def post(self, request, reservation_id):
        if not is_logged_in(request):
            return JsonResponse({"error": "Please login first", "redirect": "/login/"}, status=401)

        if not validate_session(request):
            return JsonResponse({"error": "Session expired", "redirect": "/login/"}, status=401)

        if request.session.get("user_role") != "caregiver":
            return JsonResponse({"error": "Access denied"}, status=403)
        
        token = request.session.get("access_token")
        
        try:
            response = api_request(
                "PATCH",
                f"/api/caregivers/reservations/{reservation_id}/status",
                data={"status": "REJECTED"},
                token=token
            )
            
            return JsonResponse({"success": True, "message": "Reservation rejected successfully"})
                
        except PermissionError as e:
            return JsonResponse({
                "error": str(e),
                "redirect": "/login/"
            }, status=401)
        except Exception as e:
            return JsonResponse({
                "error": f"Error rejecting reservation: {str(e)}"
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class RescheduleReservationView(View):
    def post(self, request, reservation_id):
        if not is_logged_in(request):
            return JsonResponse({"error": "Please login first", "redirect": "/login/"}, status=401)

        if not validate_session(request):
            return JsonResponse({"error": "Session expired", "redirect": "/login/"}, status=401)

        if request.session.get("user_role") != "caregiver":
            return JsonResponse({"error": "Access denied"}, status=403)
        
        token = request.session.get("access_token")
        
        try:
            body = json.loads(request.body.decode("utf-8"))
            new_schedule_id = body.get('newScheduleId')
            
            if not new_schedule_id:
                return JsonResponse({"error": "New schedule ID is required"}, status=400)
            
            response = api_request(
                "PATCH",
                f"/api/caregivers/reservations/{reservation_id}/status",
                data={"status": "ON_RESCHEDULE", "newScheduleId": new_schedule_id},
                token=token
            )
            
            return JsonResponse({"success": True, "message": "Reservation rescheduled successfully"})
                
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON input"}, status=400)
        except PermissionError as e:
            return JsonResponse({
                "error": str(e),
                "redirect": "/login/"
            }, status=401)
        except Exception as e:
            return JsonResponse({
                "error": f"Error rescheduling reservation: {str(e)}"
            }, status=500)