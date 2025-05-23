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

def api_request(method, endpoint, data=None, token=None):
    url = f"{API_BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.request(method, url, headers=headers, json=data)
        if response.status_code in [200, 201, 204]:
            try:
                return response.json()
            except:
                return response.text if response.text else {"success": True}
        elif response.status_code in [401, 403]:
            raise PermissionError("Unauthorized")
        else:
            raise Exception(f"API error: {response.status_code}")
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
            context = self._build_context(user_id, token, request)
            return render(request, self.template_name, context)
        except PermissionError:
            request.session.flush()
            messages.error(request, "Session expired. Please log in again.")
            return redirect("main:login")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return render(request, self.template_name, self._error_context(user_id))

    def _validate_session(self, request, required_role):
        return is_logged_in(request) and request.session.get("user_role") == required_role

    def _build_context(self, user_id, token, request):
        caregiver_profile = api_request("GET", f"/api/caregivers/{user_id}", token=token)
        today_date = datetime.now().strftime('%Y-%m-%d')
        approved_reservations = api_request("GET", f"/api/caregivers/{user_id}/reservations", {"status": "APPROVED"}, token)
        waiting_reservations = api_request("GET", f"/api/caregivers/{user_id}/reservations", {"status": "WAITING"}, token)
        available_schedules = api_request("GET", f"/api/caregivers/{user_id}/schedules", {"status": "AVAILABLE"}, token)
        base_context = {
            'caregiver_id': user_id,
            'caregiver_name': caregiver_profile.get("name", "Dr. Unknown"),
            'today_schedule': [res for res in approved_reservations if res.get("tanggal") == today_date],
            'pending_requests': waiting_reservations,
            'waiting_count': len(waiting_reservations),
            'available_schedules': available_schedules,
        }
        base_context.update(get_base_context(request))
        return base_context

    def _error_context(self, user_id):
        return {
            'caregiver_id': user_id,
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
        request.session.flush()
        return render(request, self.template_name)
    def post(self, request):
        email = request.POST.get('email')
        password = request.POST.get('password')
        try:
            response = api_request("POST", "/api/auth/login", {"email": email, "password": password})
            if isinstance(response, str):
                response = json.loads(response)
            access_token = response.get("access")
            if not access_token:
                raise Exception("Login failed, token not found")
            decoded = decode_jwt_with_jwks(access_token)
            if not decoded:
                raise Exception("Invalid token")
            request.session.update({
                "access_token": access_token,
                "user_id": decoded.get("user_id"),
                "user_role": decoded.get("role")
            })
            return self._redirect_by_role(decoded.get("role"), decoded.get("user_id"))
        except Exception as e:
            messages.error(request, f"Login failed: {str(e)}")
            return render(request, self.template_name)
    def _redirect_by_role(self, role, user_id):
        redirects = {
            'caregiver': lambda: redirect('main:caregiver_dashboard', caregiver_id=user_id),
            'pacilian': lambda: redirect('main:pacilian_dashboard'),
        }
        return redirects.get(role, lambda: redirect('main:home'))()

@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(View):
    template_name = 'register.html'
    def get(self, request):
        request.session.flush()
        return render(request, self.template_name, {"roles": ["pacilian", "caregiver"]})
    def post(self, request):
        role = request.POST.get('role', 'pacilian')
        profile_data = self._extract_profile_data(request.POST, role)
        try:
            api_request("POST", "/api/auth/register", {
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
                raise Exception("Failed to get access token")
            profile_payload = {
                "name": profile_data["name"],
                "nik": profile_data["nik"],
                "phone_number": profile_data["phone"]
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
            api_request("POST", "/api/profile", profile_payload, token=access_token)
            messages.success(request, f"Registration as {role} successful. Please log in.")
            return redirect("main:login")
        except Exception as e:
            messages.error(request, f"Registration failed: {str(e)}")
            return render(request, self.template_name, {"roles": ["pacilian", "caregiver"]})
    def _extract_profile_data(self, post_data, role):
        data = {field: post_data.get(field, '') for field in ['email', 'password', 'name', 'nik', 'phone']}
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
        messages.success(request, "Logged out successfully")
        return redirect("main:home")

def decode_jwt_with_jwks(token):
    try:
        jwk_client = PyJWKClient(JWKS_URL)
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        return jwt.decode(token, signing_key.key, algorithms=["RS256"], issuer="Pandacare")
    except Exception:
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None
            payload = base64.urlsafe_b64decode(parts[1] + '==')
            token_data = json.loads(payload)
            required_fields = ['iss', 'user_id', 'role', 'exp']
            if not all(field in token_data for field in required_fields):
                return None
            if (token_data.get('iss') != 'Pandacare' or 
                datetime.now().timestamp() > token_data.get('exp', 0) or
                token_data.get('role') not in ['pacilian', 'caregiver']):
                return None
            return token_data
        except Exception:
            return None