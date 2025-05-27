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
        raise Exception(f"API Error: {str(e)}")

def check_caregiver_access(request, caregiver_id=None):
    if not is_logged_in(request):
        return False, "Please login first"
    
    if not validate_session(request):
        return False, "Session expired"
    
    if request.session.get("user_role") != "caregiver":
        return False, "Access denied"
    
    if caregiver_id and str(request.session.get("user_id")) != str(caregiver_id):
        return False, "Access denied"
    
    return True, None

def transform_reservation_data(reservation):
    schedule_data = reservation.get('idSchedule', {})
    if not isinstance(schedule_data, dict):
        schedule_data = {}
    
    return {
        'id': reservation.get('id', ''),
        'idPacilian': reservation.get('idPacilian', reservation.get('patient_id', '')),
        'patientName': reservation.get('patientName', reservation.get('patient_name', reservation.get('idPacilian', ''))),
        'pacilianNote': reservation.get('pacilianNote', reservation.get('patient_note', '')),
        'statusReservasi': reservation.get('statusReservasi', reservation.get('status', 'UNKNOWN')).upper(),
        'idSchedule': {
            'id': schedule_data.get('id', ''),
            'date': schedule_data.get('date', ''),
            'day': schedule_data.get('day', ''),
            'startTime': schedule_data.get('startTime', ''),
            'endTime': schedule_data.get('endTime', ''),
        }
    }

def extract_reservations_from_response(response):
    if not response:
        return []
    
    if isinstance(response, list):
        return response
    
    if isinstance(response, dict):
        for key in ['data', 'reservations', 'results']:
            if key in response:
                return response[key]
        return [response]
    
    return []

@method_decorator(csrf_exempt, name='dispatch')
class CaregiverSchedulesView(View):
    def get(self, request, caregiver_id):
        is_valid, error_msg = check_caregiver_access(request, caregiver_id)
        if not is_valid:
            status_code = 401 if "login" in error_msg.lower() or "expired" in error_msg.lower() else 403
            return JsonResponse({"error": error_msg}, status=status_code)

        token = request.session.get("access_token")
        params = {}
        if request.GET.get('status'):
            params['status'] = request.GET.get('status')

        try:
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
        is_valid, error_msg = check_caregiver_access(request, caregiver_id)
        if not is_valid:
            if "login" in error_msg.lower() or "expired" in error_msg.lower():
                return clear_session_and_redirect(request, error_msg)
            messages.error(request, error_msg)
            return redirect("main:home")

        token = request.session.get("access_token")
        status_filter = request.GET.get('status', '').strip()
        day_filter = request.GET.get('day', '').strip()

        try:
            params = {}
            if status_filter:
                params['status'] = status_filter
            if day_filter:
                params['day'] = day_filter
            
            reservations_response = api_request(
                "GET",
                f"/api/caregivers/{caregiver_id}/reservations",
                params=params,
                token=token
            )

            reservations = extract_reservations_from_response(reservations_response)
            transformed_reservations = []
            
            for reservation in reservations:
                try:
                    transformed_reservations.append(transform_reservation_data(reservation))
                except Exception as e:
                    print(f"Warning: Failed to transform reservation {reservation.get('id', 'unknown')}: {e}")
                    transformed_reservations.append(reservation)

        except PermissionError as e:
            return clear_session_and_redirect(request, str(e))
        except Exception as e:
            messages.error(request, f"Error loading reservations: {str(e)}")
            transformed_reservations = []

        context = {
            "reservations": transformed_reservations,
            "caregiver_id": str(caregiver_id),
            "user_id": str(caregiver_id),
            "status_filter": status_filter,
            "day_filter": day_filter,
            "is_waiting": status_filter == 'WAITING',
            "is_approved": status_filter == 'APPROVED',
            "is_rejected": status_filter == 'REJECTED',
            "is_rescheduled": status_filter == 'ON_RESCHEDULE',
            "is_logged_in": True,
            "user_role": "caregiver",
            "total_reservations": len(transformed_reservations),
        }

        return render(request, self.template_name, context)

@method_decorator(csrf_exempt, name='dispatch')
class ReservationActionView(View):
    def post(self, request, reservation_id, action):
        is_valid, error_msg = check_caregiver_access(request)
        if not is_valid:
            status_code = 401 if "login" in error_msg.lower() or "expired" in error_msg.lower() else 403
            response_data = {"error": error_msg}
            if status_code == 401:
                response_data["redirect"] = "/login/"
            return JsonResponse(response_data, status=status_code)

        token = request.session.get("access_token")

        try:
            if action == "approve":
                data = {"status": "APPROVED"}
                message = "Reservation approved successfully"
            elif action == "reject":
                data = {"status": "REJECTED"}
                message = "Reservation rejected successfully"
            elif action == "reschedule":
                try:
                    body = json.loads(request.body.decode("utf-8"))
                    new_schedule_id = body.get('newScheduleId')
                    if not new_schedule_id:
                        return JsonResponse({"error": "New schedule ID is required"}, status=400)
                    data = {"status": "ON_RESCHEDULE", "newScheduleId": new_schedule_id}
                    message = "Reservation rescheduled successfully"
                except json.JSONDecodeError:
                    return JsonResponse({"error": "Invalid JSON input"}, status=400)
            else:
                return JsonResponse({"error": "Invalid action"}, status=400)

            api_request(
                "PATCH",
                f"/api/caregivers/reservations/{reservation_id}/status",
                data=data,
                token=token
            )

            return JsonResponse({"success": True, "message": message})

        except PermissionError as e:
            return JsonResponse({"error": str(e), "redirect": "/login/"}, status=401)
        except Exception as e:
            return JsonResponse({"error": f"Error {action}ing reservation: {str(e)}"}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class ApproveReservationView(ReservationActionView):
    def post(self, request, reservation_id):
        return super().post(request, reservation_id, "approve")

@method_decorator(csrf_exempt, name='dispatch')
class RejectReservationView(ReservationActionView):
    def post(self, request, reservation_id):
        return super().post(request, reservation_id, "reject")

@method_decorator(csrf_exempt, name='dispatch')
class RescheduleReservationView(ReservationActionView):
    def post(self, request, reservation_id):
        return super().post(request, reservation_id, "reschedule")