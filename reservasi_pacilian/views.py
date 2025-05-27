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
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

# API Configuration
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
        print("User not logged in, redirecting to login")
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

# POST: Accept schedule change
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

def get_available_schedules(request, caregiver_id):
    """Function-based view untuk mengambil available schedules"""
    # Authentication checks
    if not is_logged_in(request):
        return JsonResponse({"error": "Authentication required"}, status=401)

    user_context = get_user_context(request)
    if user_context.get('user_role') != 'pacilian':
        return JsonResponse({"error": "Access denied"}, status=403)

    try:
        token = request.session.get("access_token")

        print(f"Fetching available schedules for caregiver: {caregiver_id}")

        # Call Spring Boot API - get all schedules
        response = api_request(
            "GET",
            f"/api/caregivers/{caregiver_id}/schedules",
            token=token
        )

        # Process and return the schedules
        schedules = []
        if response and response.get('status') == 200:
            raw_schedules = response.get('data', [])

            for schedule in raw_schedules:
                if schedule.get('status', '').upper() == 'AVAILABLE':
                    schedules.append({
                        'id': schedule.get('id'),
                        'date': schedule.get('date'),
                        'day': schedule.get('day'),
                        'startTime': schedule.get('startTime'),
                        'endTime': schedule.get('endTime'),
                        'status': schedule.get('status'),
                        'caregiverId': str(caregiver_id)
                    })

        return JsonResponse({
            "success": True,
            "data": schedules,
            "total": len(schedules),
            "message": f"Found {len(schedules)} available schedules"
        })

    except Exception as e:
        print(f"Error in get_available_schedules: {e}")
        return JsonResponse({"error": str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class AvailableScheduleListView(View):
    template_name = 'available_schedules.html'

    def get(self, request, caregiver_id):
        """HTML view for displaying available schedules"""
        # Authentication checks
        if not is_logged_in(request):
            messages.error(request, "Please login first")
            return redirect("main:login")

        user_context = get_user_context(request)
        if user_context.get('user_role') != 'pacilian':
            messages.error(request, "Access denied")
            return redirect("main:home")

        # Get reservation_id if this is for editing
        reservation_id = request.GET.get('reservation_id')

        try:
            token = request.session.get("access_token")

            # Call the Spring Boot API - GET ALL schedules first, then filter
            # Don't filter by status in API call, do it in Python
            print(f"=== FETCHING ALL SCHEDULES FOR CAREGIVER ===")
            print(f"Caregiver ID: {caregiver_id}")
            print(f"Reservation ID (for edit): {reservation_id}")

            response = api_request(
                "GET",
                f"/api/caregivers/{caregiver_id}/schedules",
                token=token
            )

            print(f"=== RAW API RESPONSE ===")
            print(f"Response: {response}")
            print(f"Response type: {type(response)}")

            # Process schedules from Spring Boot API response
            schedules = []
            if response:
                # Handle Spring Boot API response structure: {status, message, data}
                if isinstance(response, dict):
                    if response.get('status') == 200 and 'data' in response:
                        raw_schedules = response['data']
                        print(f"Found {len(raw_schedules)} total schedules")

                        # Filter for AVAILABLE schedules only
                        for schedule in raw_schedules:
                            if schedule.get('status', '').upper() == 'AVAILABLE':
                                processed_schedule = {
                                    'id': schedule.get('id'),
                                    'date': schedule.get('date'),
                                    'day': schedule.get('day'),
                                    'startTime': schedule.get('startTime'),
                                    'endTime': schedule.get('endTime'),
                                    'status': schedule.get('status'),
                                    'caregiverId': str(caregiver_id)
                                }
                                schedules.append(processed_schedule)
                                print(f"Added AVAILABLE schedule: {processed_schedule}")
                    else:
                        print(f"API response status: {response.get('status')}")
                        print(f"API response message: {response.get('message')}")
                else:
                    print("API response is not a dictionary")

            print(f"=== FINAL PROCESSED SCHEDULES ===")
            print(f"Total AVAILABLE schedules: {len(schedules)}")
            for i, schedule in enumerate(schedules):
                print(f"Schedule {i+1}: {schedule}")

            # Get caregiver info if needed
            caregiver_info = None
            try:
                caregiver_response = api_request("GET", f"/api/caregivers/{caregiver_id}", token=token)
                if caregiver_response and caregiver_response.get('status') == 200:
                    caregiver_info = caregiver_response.get('data', caregiver_response)
            except Exception as e:
                print(f"Could not fetch caregiver info: {e}")

            context = {
                'schedules': schedules,
                'caregiver_id': str(caregiver_id),
                'caregiver_info': caregiver_info,
                'reservation_id': reservation_id,
                'is_edit_mode': bool(reservation_id),
                'total_schedules': len(schedules),
                **user_context
            }

            print(f"=== TEMPLATE CONTEXT ===")
            print(f"Schedules count: {len(context['schedules'])}")
            print(f"Is edit mode: {context['is_edit_mode']}")
            print(f"Caregiver ID: {context['caregiver_id']}")

            return render(request, self.template_name, context)

        except Exception as e:
            print(f"=== ERROR in AvailableScheduleListView ===")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")

            messages.error(request, f"Error loading schedules: {str(e)}")

            context = {
                'schedules': [],
                'caregiver_id': str(caregiver_id),
                'error_message': str(e),
                'reservation_id': reservation_id,
                'is_edit_mode': bool(reservation_id),
                'total_schedules': 0,
                **user_context
            }

    def post(self, request, caregiver_id):
        """Handle schedule selection for both new reservations and edits"""
        print(f"=== POST REQUEST TO AvailableScheduleListView ===")
        print(f"Caregiver ID: {caregiver_id}")
        print(f"Request method: {request.method}")
        print(f"POST data: {request.POST}")

        if not is_logged_in(request):
            return JsonResponse({"error": "Authentication required"}, status=401)

        user_context = get_user_context(request)
        if user_context.get('user_role') != 'pacilian':
            return JsonResponse({"error": "Access denied"}, status=403)

        schedule_id = request.POST.get('schedule_id')
        reservation_id = request.POST.get('reservation_id')

        print(f"Schedule ID from form: {schedule_id}")
        print(f"Reservation ID from form: {reservation_id}")

        if not schedule_id:
            messages.error(request, "Please select a schedule")
            return redirect('available_schedules_html', caregiver_id=caregiver_id)

        token = request.session.get("access_token")
        pacilian_id = user_context.get('user_id')

        try:
            if reservation_id:
                # Edit existing reservation
                print(f"=== EDITING RESERVATION ===")
                print(f"Reservation ID: {reservation_id}")
                print(f"New Schedule ID: {schedule_id}")

                # Directly call Spring Boot API instead of using RequestFactory
                data = {
                    "idSchedule": str(schedule_id)
                }

                endpoint = f"/api/reservasi-konsultasi/{reservation_id}/edit"

                print(f"=== CALLING SPRING BOOT DIRECTLY ===")
                print(f"Endpoint: {endpoint}")
                print(f"Data: {data}")

                response = api_request("POST", endpoint, data=data, token=token)

                print(f"=== SPRING BOOT EDIT RESPONSE ===")
                print(f"Response: {response}")
                print(f"Response type: {type(response)}")

                if response and isinstance(response, dict):
                    if response.get('message') and 'updated successfully' in response.get('message', '').lower():
                        print("SUCCESS: Reservation updated successfully")
                        messages.success(request, "Reservation schedule updated successfully!")
                    else:
                        error_msg = response.get('error', 'Unknown error occurred')
                        print(f"ERROR from Spring Boot: {error_msg}")
                        messages.error(request, f"Failed to update reservation: {error_msg}")
                else:
                    print("ERROR: Invalid response from Spring Boot")
                    messages.error(request, 'Failed to update reservation: Invalid response')

            else:
                # Create new reservation
                print(f"=== CREATING NEW RESERVATION ===")
                endpoint = "/api/reservasi-konsultasi/request"
                data = {
                    "idSchedule": schedule_id,
                    "idPacilian": pacilian_id,
                }
                response = api_request("POST", endpoint, data=data, token=token)

                messages.success(request, "Reservation created successfully!")

            print(f"Redirecting to reservation list for pacilian: {pacilian_id}")
            return redirect("reservasi_pacilian:pacilian_reservasi_list", id_pacilian=pacilian_id)

        except Exception as e:
            print(f"=== EXCEPTION in post method ===")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")

            messages.error(request, f"Failed to process request: {str(e)}")
            return redirect('available_schedules_html', caregiver_id=caregiver_id)

    def post(self, request, caregiver_id):
        print(f"=== POST REQUEST TO AvailableScheduleListView ===")
        print(f"Caregiver ID: {caregiver_id}")
        print(f"Request method: {request.method}")
        print(f"POST data: {request.POST}")

        if not is_logged_in(request):
            return JsonResponse({"error": "Authentication required"}, status=401)

        user_context = get_user_context(request)
        if user_context.get('user_role') != 'pacilian':
            return JsonResponse({"error": "Access denied"}, status=403)

        schedule_id = request.POST.get('schedule_id')
        reservation_id = request.POST.get('reservation_id')

        print(f"Schedule ID from form: {schedule_id}")
        print(f"Reservation ID from form: {reservation_id}")

        if not schedule_id:
            messages.error(request, "Please select a schedule")
            return redirect('available_schedules_html', caregiver_id=caregiver_id)

        token = request.session.get("access_token")
        pacilian_id = user_context.get('user_id')

        try:
            if reservation_id:
                print(f"=== EDITING RESERVATION ===")
                print(f"Reservation ID: {reservation_id}")
                print(f"New Schedule ID: {schedule_id}")

                data = {
                    "idSchedule": str(schedule_id)
                }

                endpoint = f"/api/reservasi-konsultasi/{reservation_id}/edit"

                print(f"=== CALLING SPRING BOOT EDIT API ===")
                print(f"Endpoint: {endpoint}")
                print(f"Data: {data}")

                response = api_request("POST", endpoint, data=data, token=token)

                print(f"=== SPRING BOOT EDIT RESPONSE ===")
                print(f"Response: {response}")
                print(f"Response type: {type(response)}")

                if response and isinstance(response, dict):
                    if response.get('message') and 'updated successfully' in response.get('message', '').lower():
                        print("SUCCESS: Reservation updated successfully")
                        messages.success(request, "Reservation schedule updated successfully!")
                    else:
                        error_msg = response.get('error', 'Unknown error occurred')
                        print(f"ERROR from Spring Boot: {error_msg}")
                        messages.error(request, f"Failed to update reservation: {error_msg}")
                else:
                    print("ERROR: Invalid response from Spring Boot")
                    messages.error(request, 'Failed to update reservation: Invalid response')

            else:
                print(f"=== CREATING NEW RESERVATION ===")
                print(f"Schedule ID: {schedule_id}")
                print(f"Pacilian ID: {pacilian_id}")

                endpoint = "/api/reservasi-konsultasi/request"
                data = {
                    "idSchedule": str(schedule_id),
                    "idPacilian": str(pacilian_id),
                }

                print(f"=== CALLING SPRING BOOT CREATE API ===")
                print(f"Endpoint: {endpoint}")
                print(f"Data: {data}")

                response = api_request("POST", endpoint, data=data, token=token)

                print(f"=== SPRING BOOT CREATE RESPONSE ===")
                print(f"Response: {response}")
                print(f"Response type: {type(response)}")

                if response and isinstance(response, dict):
                    if response.get('message') and ('berhasil diajukan' in response.get('message', '').lower() or 'success' in response.get('message', '').lower()):
                        print("SUCCESS: Reservation created successfully")
                        messages.success(request, "Reservation created successfully!")
                    else:
                        error_msg = response.get('error', 'Unknown error occurred')
                        print(f"ERROR from Spring Boot: {error_msg}")
                        messages.error(request, f"Failed to create reservation: {error_msg}")
                else:
                    print("SUCCESS: Default success for create")
                    messages.success(request, "Reservation created successfully!")

            print(f"Redirecting to reservation list for pacilian: {pacilian_id}")
            return redirect("reservasi_pacilian:pacilian_reservasi_list", id_pacilian=pacilian_id)

        except Exception as e:
            print(f"=== EXCEPTION in post method ===")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")

            if "not available" in str(e).lower() or "tidak tersedia" in str(e).lower():
                messages.error(request, "Selected schedule is not available")
            elif "not found" in str(e).lower() or "tidak ditemukan" in str(e).lower():
                messages.error(request, "Schedule not found")
            elif "sudah disetujui" in str(e).lower() or "already approved" in str(e).lower():
                messages.error(request, "Cannot edit reservation that has already been approved")
            elif "Unauthorized" in str(e) or "401" in str(e):
                messages.error(request, "Authentication failed. Please login again.")
            else:
                messages.error(request, f"Failed to process request: {str(e)}")

            return redirect('available_schedules_html', caregiver_id=caregiver_id)
        
class ReservationRequestView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        if not is_logged_in(request):
            messages.error(request, "You need to login first")
            return redirect("main:login")
        
        try:
            data = {
                "idSchedule": request.POST.get("schedule_id"),
                "idPacilian": request.session.get("user_id")
            }
            print(f"{data.get('idSchedule')=}, {data.get('idPacilian')=}")
            
            response = api_request(
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