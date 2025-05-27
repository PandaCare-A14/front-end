from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import requests
from datetime import datetime
import jwt
from jwt import PyJWKClient
import base64
import json
import os

API_BASE_URL = os.getenv("API_BASE_URL")
JWKS_URL = os.getenv("JWKS_URL")

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

def get_base_context(request):
    return {
        'is_logged_in': is_logged_in(request),
        'user_role': request.session.get("user_role", 'guest'),
        'user_id': request.session.get("user_id")
    }

def decode_jwt_manually(token):
    """Manual JWT decode without signature verification"""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None

        payload_b64 = parts[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += '=' * padding

        payload = base64.urlsafe_b64decode(payload_b64)
        return json.loads(payload)

    except Exception:
        return None

def decode_jwt_with_jwks(token):
    manual_decoded = decode_jwt_manually(token)

    try:
        if JWKS_URL:
            jwk_client = PyJWKClient(JWKS_URL)
            signing_key = jwk_client.get_signing_key_from_jwt(token)
            decoded = jwt.decode(token, signing_key.key, algorithms=["RS256"], issuer="Pandacare")
            if 'roles' in decoded and isinstance(decoded['roles'], list) and decoded['roles']:
                decoded['role'] = decoded['roles'][0]
            return decoded
    except Exception:
        pass

    if manual_decoded:
        if 'roles' in manual_decoded and isinstance(manual_decoded['roles'], list):
            if manual_decoded['roles']:
                manual_decoded['role'] = manual_decoded['roles'][0]
            else:
                return None
        elif 'role' not in manual_decoded:
            return None

        required_fields = ['iss', 'user_id', 'exp']
        if not all(field in manual_decoded for field in required_fields):
            return None

        current_time = datetime.now().timestamp()
        if (manual_decoded.get('iss') != 'Pandacare' or
                current_time > manual_decoded.get('exp', 0)):
            return None

        if manual_decoded.get('role') not in ['pacilian', 'caregiver']:
            return None

        return manual_decoded

    return None

class HomePageView(View):
    template_name = 'homepage.html'

    def get(self, request):
        return render(request, self.template_name, get_base_context(request))

class PacilianDashboardView(View):
    template_name = 'homepage.html'

    def get(self, request):
        if not is_logged_in(request):
            request.session.flush()
            messages.error(request, "Please login first")
            return redirect("main:login")
        return render(request, self.template_name, get_base_context(request))

@method_decorator(csrf_exempt, name='dispatch')
class CaregiverDashboardView(View):
    template_name = 'homepage_caregiver.html'

    def get(self, request, caregiver_id=None):
        if not self._validate_session(request, "caregiver"):
            return redirect("main:login")

        user_id = request.session.get("user_id")
        token = request.session.get("access_token")

        try:
            context = self._build_context(user_id, token)
            context['user_id'] = user_id
            return render(request, self.template_name, context)
        except Exception as e:
            messages.error(request, "Error loading dashboard")
            return render(request, self.template_name, self._error_context(user_id))

    def _validate_session(self, request, required_role):
        return is_logged_in(request) and request.session.get("user_role") == required_role

    def _build_context(self, user_id, token):
        caregiver_name = f"Dr. {str(user_id)[:8]}"

        caregiver_data = self._fetch_caregiver_profile(user_id, token)
        if caregiver_data and caregiver_data.get("name"):
            caregiver_name = f"Dr. {caregiver_data['name']}"

        approved_reservations = self._get_reservations(user_id, "APPROVED", token)
        waiting_reservations = self._get_reservations(user_id, "WAITING", token)

        today_schedule = self._filter_today_schedule(approved_reservations)

        return {
            'caregiver_id': user_id,
            'caregiver_name': caregiver_name,
            'today_schedule': today_schedule,
            'pending_requests': waiting_reservations[:10] if waiting_reservations else [],
            'waiting_count': len(waiting_reservations) if waiting_reservations else 0,
            'available_schedules': [],
            'is_logged_in': True,
            'user_role': 'caregiver'
        }

    def _fetch_caregiver_profile(self, user_id, token):
        endpoints_to_try = [
            f"/api/caregivers/{user_id}/profile",
            f"/api/doctors/{user_id}",
        ]

        for endpoint in endpoints_to_try:
            try:
                profile_data = api_request("GET", endpoint, token=token)
                if profile_data:
                    return profile_data
            except Exception:
                continue

        return None

    def _get_reservations(self, user_id, status, token):
        try:
            endpoint = f"/api/caregivers/{user_id}/reservations"
            reservations = api_request("GET", endpoint, params={"status": status}, token=token)

            if reservations is None:
                return []

            if isinstance(reservations, list):
                return reservations
            elif isinstance(reservations, dict):
                if 'data' in reservations:
                    return reservations['data'] if isinstance(reservations['data'], list) else []
                elif 'reservations' in reservations:
                    return reservations['reservations'] if isinstance(reservations['reservations'], list) else []

            return []

        except Exception:
            return []

    def _filter_today_schedule(self, reservations):
        if not reservations:
            return []

        today = datetime.now().strftime('%Y-%m-%d')
        today_schedule = []

        for res in reservations:
            try:
                schedule = res.get("idSchedule", {})
                if not schedule:
                    continue

                schedule_date = schedule.get("date", "")

                if schedule_date and schedule_date.startswith(today):
                    today_schedule.append(res)
                        
            except Exception:
                continue

        return today_schedule

    def _error_context(self, user_id):
        return {
            'caregiver_id': user_id,
            'user_id': user_id,
            'caregiver_name': 'Dr. Unknown',
            'today_schedule': [],
            'pending_requests': [],
            'waiting_count': 0,
            'available_schedules': [],
            'is_logged_in': True,
            'user_role': 'caregiver'
        }

@method_decorator(csrf_exempt, name='dispatch')
class LoginView(View):
    template_name = 'login.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        request.session.flush()
        request.session.clear()

        email = request.POST.get('email')
        password = request.POST.get('password')

        if not email or not password:
            messages.error(request, "Email and password are required")
            return render(request, self.template_name)

        if not API_BASE_URL:
            messages.error(request, "Server configuration error")
            return render(request, self.template_name)

        try:
            response = api_request("POST", "/api/auth/login", {
                "email": email,
                "password": password
            })

            if isinstance(response, str):
                try:
                    response = json.loads(response)
                except json.JSONDecodeError:
                    raise Exception("Invalid response format from server")

            access_token = response.get("access") if isinstance(response, dict) else None
            if not access_token:
                raise Exception("Login failed, token not found")

            decoded = decode_jwt_with_jwks(access_token)
            if not decoded:
                raise Exception("Invalid token received")

            user_id = decoded.get("user_id")
            role = decoded.get("role")

            request.session.update({
                "access_token": access_token,
                "user_id": user_id,
                "user_role": role
            })

            return self._redirect_by_role(role, user_id)

        except Exception as e:
            error_str = str(e).lower()
            if "unauthorized" in error_str or "401" in error_str:
                messages.error(request, "Invalid email or password. Please try again.")
            elif "connection" in error_str:
                messages.error(request, "Connection problem. Please check your internet connection.")
            elif "timeout" in error_str:
                messages.error(request, "Server timeout. Please try again later.")
            elif "token not found" in error_str:
                messages.error(request, "Login failed. Please try again.")
            elif "invalid token" in error_str:
                messages.error(request, "Authentication failed. Please try again.")
            else:
                messages.error(request, "Login failed. Please try again or contact support.")

            return render(request, self.template_name)

    def _redirect_by_role(self, role, user_id):
        if role == 'caregiver':
            return redirect('main:caregiver_dashboard', caregiver_id=user_id)
        elif role == 'pacilian':
            return redirect('main:pacilian_dashboard')
        else:
            return redirect('main:home')

class RegisterView(View):
    template_name = 'register.html'

    def get(self, request):
        request.session.flush()
        return render(request, self.template_name, {"roles": ["pacilian", "caregiver"]})

    def post(self, request):
        role = request.POST.get('role', 'pacilian')
        profile_data = self._extract_profile_data(request.POST, role)

        try:
            register_response = api_request("POST", "/api/auth/register", {
                "email": profile_data["email"],
                "password": profile_data["password"],
                "role": role
            })

            login_response = api_request("POST", "/api/auth/login", {
                "email": profile_data["email"],
                "password": profile_data["password"]
            })

            access_token = login_response.get("access")
            if not access_token:
                raise Exception("Failed to get access token after registration")

            profile_payload = {
                "name": profile_data["name"],
                "nik": profile_data["nik"],
                "phone_number": profile_data["phone"],
                "email": profile_data["email"],
            }

            if role == 'pacilian':
                profile_payload.update({
                    "address": profile_data.get("address", ""),
                    "medical_history": profile_data.get("medical_history", "")
                })
            else:
                profile_payload.update({
                    "work_address": profile_data.get("work_address", ""),
                    "speciality": profile_data.get("speciality", "")
                })

            profile_endpoints = ["/api/profile", "/api/caregivers/profile", "/api/doctors/profile"]
            profile_created = False
            for endpoint in profile_endpoints:
                try:
                    profile_response = api_request("POST", endpoint, profile_payload, token=access_token)
                    profile_created = True
                    break
                except Exception:
                    continue

            messages.success(request, "Registration successful! You can now sign in with your account.")
            return redirect("main:login")

        except requests.exceptions.ConnectionError:
            messages.error(request, "Unable to connect to server. Please try again later.")
        
        except Exception as e:
            error_str = str(e).lower()

            if "email" in error_str and ("exist" in error_str or "duplicate" in error_str):
                messages.error(request, "Email already registered. Please use a different email or try logging in.")
            elif "nik" in error_str and ("exist" in error_str or "duplicate" in error_str):
                messages.error(request, "NIK already registered. Please check your NIK or contact support.")
            elif "unauthorized" in error_str:
                messages.error(request, "Registration failed. Please try again.")
            elif "connection" in error_str:
                messages.error(request, "Connection problem. Please check your internet connection.")
            elif "timeout" in error_str:
                messages.error(request, "Server timeout. Please try again later.")
            else:
                messages.error(request, "Registration failed. Please check your information and try again.")

        return render(request, self.template_name, {"roles": ["pacilian", "caregiver"]})

    def _extract_profile_data(self, post_data, role):
        data = {
            'email': post_data.get('email', ''),
            'password': post_data.get('password', ''),
            'name': post_data.get('name', ''),
            'nik': post_data.get('nik', ''),
            'phone': post_data.get('phone', '')
        }
        if role == 'pacilian':
            data.update({
                'address': post_data.get('address', ''),
                'medical_history': post_data.get('medical_history', '')
            })
        else:
            data.update({
                'work_address': post_data.get('work_address', ''),
                'speciality': post_data.get('speciality', '')
            })
        return data

class LogoutView(View):
    def get(self, request):
        request.session.flush()
        request.session.clear()
        request.session.cycle_key()
        messages.success(request, "Logged out successfully")
        return redirect("main:home")