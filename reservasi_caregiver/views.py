from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.views import View
import requests

API_BASE_URL = "http://localhost:8080"

class ReservationListView(View):
    template_name = "reservation_list.html"

    def get(self, request, caregiver_id):
        token = request.session.get("access_token")
        if not token:
            return redirect("main:login")

        status_filter = request.GET.get("status", "")  # Default empty string
        date_from = request.GET.get("date_from", "")
        date_to = request.GET.get("date_to", "")

        # FIX: Pakai caregivers bukan doctors
        url = f"{API_BASE_URL}/api/caregivers/{caregiver_id}/reservations"
        params = {}
        if status_filter:
            params["status"] = status_filter
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to

        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 401:
                request.session.flush()
                return redirect("login")
            
            response.raise_for_status()
            all_reservations = response.json()

            # Pastikan all_reservations adalah list
            if not isinstance(all_reservations, list):
                all_reservations = []

            paginator = Paginator(all_reservations, 10)
            page_number = request.GET.get("page")
            reservations_page = paginator.get_page(page_number)

            stats = self.get_stats(all_reservations)
            waiting_count = stats.get("waiting", 0)

            context = {
                "reservations": reservations_page,
                "stats": stats,
                "status_filter": status_filter,
                "date_from": date_from,
                "date_to": date_to,
                "waiting_count": waiting_count,
                "user_id": caregiver_id,
                # Untuk template conditionals
                "is_waiting": status_filter == "WAITING",
                "is_approved": status_filter == "APPROVED", 
                "is_rejected": status_filter == "REJECTED",
                "is_rescheduled": status_filter == "ON_RESCHEDULE",
            }
            
            return render(request, self.template_name, context)

        except Exception as e:
            messages.error(request, f"Failed to load reservations: {str(e)}")
            return render(request, self.template_name, {
                "reservations": [],
                "stats": {"waiting": 0, "approved": 0, "rejected": 0, "rescheduled": 0},
                "status_filter": status_filter,
                "date_from": date_from,
                "date_to": date_to,
                "waiting_count": 0,
                "caregiver_id": caregiver_id,
                "is_waiting": False,
                "is_approved": False,
                "is_rejected": False,
                "is_rescheduled": False,
                "error": str(e)
            })

    def get_stats(self, reservations):
        from collections import Counter
        status_counts = Counter(res.get("status_reservasi", "") for res in reservations if res)
        return {
            "waiting": status_counts.get("WAITING", 0),
            "approved": status_counts.get("APPROVED", 0),
            "rejected": status_counts.get("REJECTED", 0),
            "rescheduled": status_counts.get("ON_RESCHEDULE", 0)
        }