from django.conf import settings
import requests
from functools import wraps

def get_tokens_from_session(request):
    """Get access and refresh tokens from session"""
    access_token = request.session.get('access_token')
    refresh_token = request.session.get('refresh_token')
    return access_token, refresh_token

class APIClient:
    @staticmethod
    def get_auth_headers(request):
        """Get authorization headers with JWT token"""
        access_token, _ = get_tokens_from_session(request)
        return {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
    
    @staticmethod
    def handle_token_refresh(request):
        """Refresh access token if expired"""
        _, refresh_token = get_tokens_from_session(request)
        if not refresh_token:
            return False
            
        try:
            # Call refresh token endpoint
            response = requests.post(
                f"{settings.API_BASE_URL}/api/auth/token/refresh",
                json={"refresh_token": refresh_token}
            )
            
            if response.status_code == 200:
                data = response.json()
                # Update tokens in session
                request.session['access_token'] = data.get('access')
                request.session['refresh_token'] = data.get('refresh')
                return True
            return False
        except Exception:
            return False
    
    @staticmethod
    def get(endpoint, request, params=None):
        """Make GET request to Spring Boot API with auto-refresh for expired tokens"""
        url = f"{settings.API_BASE_URL}{endpoint}"
        headers = APIClient.get_auth_headers(request)
        
        try:
            response = requests.get(url, headers=headers, params=params)
            
            # Handle token expiration
            if response.status_code == 401:
                # Try to refresh token
                if APIClient.handle_token_refresh(request):
                    # Retry with new token
                    headers = APIClient.get_auth_headers(request)
                    response = requests.get(url, headers=headers, params=params)
                else:
                    # If refresh fails, redirect to login
                    raise Exception("Authentication failed")
            
            return response.json()
        except Exception as e:
            raise Exception(f"API Error: {str(e)}")
    
    @staticmethod
    def post(endpoint, request, data):
        """Make POST request to Spring Boot API with auto-refresh for expired tokens"""
        url = f"{settings.API_BASE_URL}{endpoint}"
        headers = APIClient.get_auth_headers(request)
        
        try:
            response = requests.post(url, headers=headers, json=data)
            
            # Handle token expiration
            if response.status_code == 401:
                # Try to refresh token
                if APIClient.handle_token_refresh(request):
                    # Retry with new token
                    headers = APIClient.get_auth_headers(request)
                    response = requests.post(url, headers=headers, json=data)
                else:
                    # If refresh fails, redirect to login
                    raise Exception("Authentication failed")
            
            return response.json()
        except Exception as e:
            raise Exception(f"API Error: {str(e)}")
            
    @staticmethod
    def delete(endpoint, request):
        url = f"{settings.API_BASE_URL}{endpoint}"
        headers = APIClient.get_auth_headers(request)
        
        try:
            response = requests.delete(url, headers=headers)
            
            # Handle token expiration
            if response.status_code == 401:
                # Try to refresh token
                if APIClient.handle_token_refresh(request):
                    # Retry with new token
                    headers = APIClient.get_auth_headers(request)
                    response = requests.delete(url, headers=headers)
                else:
                    # If refresh fails, redirect to login
                    raise Exception("Authentication failed")
            
            # Check if response has JSON content
            if response.headers.get('content-type', '').startswith('application/json'):
                return response.json()
            return {'success': True, 'message': 'Operation successful'}
        except Exception as e:
            raise Exception(f"API Error: {str(e)}")