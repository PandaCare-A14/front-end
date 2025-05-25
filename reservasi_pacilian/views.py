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
from django.utils.decorators import method_decorator

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080")
SPRINGBOOT_API_URL = f"{API_BASE_URL}/api/reservasi-konsultasi"

def is_logged_in(request):
    """Check if user is logged in"""
    return bool(request.session.get("access_token"))

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
    
# # DEBUGGING: Test authentication with detailed token information
# def debug_auth_test(request, id_pacilian):
#     print("DEBUG AUTH TEST ENDPOINT CALLED")
    
#     # Check session data
#     print(f"=== SESSION DEBUG ===")
#     print(f"Session keys: {list(request.session.keys())}")
#     print(f"access_token exists: {'access_token' in request.session}")
#     print(f"user_id exists: {'user_id' in request.session}")
#     print(f"user_role exists: {'user_role' in request.session}")
    
#     token = request.session.get("access_token")
#     user_id = request.session.get("user_id")
#     user_role = request.session.get("user_role")
    
#     print(f"Token length: {len(token) if token else 'None'}")
#     print(f"Token preview: {token[:100] if token else 'None'}...")
#     print(f"User ID: {user_id}")
#     print(f"User Role: {user_role}")
    
#     # Test 1: Basic health check
#     print(f"\n=== TEST 1: Backend Health Check ===")
#     try:
#         health_response = requests.get(f"{API_BASE_URL}/health", timeout=5)
#         print(f"✅ Health check: {health_response.status_code}")
#         print(f"Health response: {health_response.text[:200]}")
#     except Exception as e:
#         print(f"❌ Health check failed: {e}")
    
#     # Test 2: API call without authentication
#     print(f"\n=== TEST 2: API Call WITHOUT Auth ===")
#     try:
#         endpoint = f"/api/reservasi-konsultasi/{id_pacilian}"
#         url = f"{API_BASE_URL}{endpoint}"
#         print(f"URL: {url}")
        
#         no_auth_response = requests.get(url, timeout=10)
#         print(f"No-auth response code: {no_auth_response.status_code}")
#         print(f"No-auth response: {no_auth_response.text[:500]}")
#     except Exception as e:
#         print(f"❌ No-auth test failed: {e}")
    
#     # Test 3: API call with authentication
#     print(f"\n=== TEST 3: API Call WITH Auth ===")
#     if token:
#         try:
#             headers = {
#                 "Content-Type": "application/json",
#                 "Authorization": f"Bearer {token}"
#             }
#             print(f"Headers: {headers}")
#             print(f"Authorization header: {headers['Authorization'][:100]}...")
            
#             auth_response = requests.get(url, headers=headers, timeout=10)
#             print(f"Auth response code: {auth_response.status_code}")
#             print(f"Auth response headers: {dict(auth_response.headers)}")
#             print(f"Auth response: {auth_response.text[:500]}")
            
#             # Test if it's a CORS issue
#             print(f"Response headers - CORS related:")
#             cors_headers = {k: v for k, v in auth_response.headers.items() if 'access-control' in k.lower() or 'cors' in k.lower()}
#             print(f"CORS headers: {cors_headers}")
            
#         except Exception as e:
#             print(f"❌ Auth test failed: {e}")
#     else:
#         print("❌ No token available for auth test")
    
#     # Test 4: Try different endpoints
#     print(f"\n=== TEST 4: Alternative Endpoints ===")
#     alternative_endpoints = [
#         "/api/reservasi-konsultasi",
#         "/api/reservations",
#         "/api/consultations",
#         f"/api/pacilian/{id_pacilian}/reservations"
#     ]
    
#     for alt_endpoint in alternative_endpoints:
#         try:
#             alt_url = f"{API_BASE_URL}{alt_endpoint}"
#             headers = {"Authorization": f"Bearer {token}"} if token else {}
#             alt_response = requests.get(alt_url, headers=headers, timeout=5)
#             print(f"Endpoint {alt_endpoint}: {alt_response.status_code} - {alt_response.text[:100]}")
#         except Exception as e:
#             print(f"Endpoint {alt_endpoint}: ERROR - {e}")
    
#     # Test 5: JWT Token details
#     print(f"\n=== TEST 5: JWT Token Analysis ===")
#     if token:
#         try:
#             parts = token.split('.')
#             print(f"JWT parts count: {len(parts)}")
            
#             if len(parts) == 3:
#                 # Decode header
#                 header_b64 = parts[0]
#                 padding = 4 - len(header_b64) % 4
#                 if padding != 4:
#                     header_b64 += '=' * padding
#                 header = json.loads(base64.urlsafe_b64decode(header_b64))
#                 print(f"JWT Header: {header}")
                
#                 # Decode payload
#                 payload_b64 = parts[1]
#                 padding = 4 - len(payload_b64) % 4
#                 if padding != 4:
#                     payload_b64 += '=' * padding
#                 payload = json.loads(base64.urlsafe_b64decode(payload_b64))
#                 print(f"JWT Payload: {payload}")
                
#                 # Check expiry
#                 if 'exp' in payload:
#                     import datetime
#                     exp_time = datetime.datetime.fromtimestamp(payload['exp'])
#                     current_time = datetime.datetime.now()
#                     print(f"Token expires: {exp_time}")
#                     print(f"Current time: {current_time}")
#                     print(f"Token expired: {current_time > exp_time}")
                
#         except Exception as e:
#             print(f"❌ JWT analysis failed: {e}")
    
#     # Return a debug response
#     return JsonResponse({
#         "debug": "Authentication debug test completed",
#         "session_data": {
#             "has_token": bool(token),
#             "token_length": len(token) if token else 0,
#             "user_id": user_id,
#             "user_role": user_role
#         },
#         "check_console": "Check Django console for detailed debug output"
#     })