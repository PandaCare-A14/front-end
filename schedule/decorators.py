from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def login_required(view_func):
    """Decorator to check if user is logged in"""
    @wraps(view_func)
    def wrapped_view(self, request, *args, **kwargs):
        if not request.session.get('access_token'):
            messages.error(request, "Please login to continue")
            return redirect('login')
        return view_func(self, request, *args, **kwargs)
    return wrapped_view

def role_required(allowed_roles):
    """Decorator to check if user has required role"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(self, request, *args, **kwargs):
            if not request.session.get('access_token'):
                messages.error(request, "Please login to continue")
                return redirect('login')
            
            user_role = request.session.get('user_role')
            if not user_role or user_role not in allowed_roles:
                messages.error(request, "You don't have permission to access this page")
                return redirect('main:index')
            
            return view_func(self, request, *args, **kwargs)
        return wrapped_view
    return decorator