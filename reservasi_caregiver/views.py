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
            return redirect("login")

        status_filter = request.GET.get("status")
        date_from = request.GET.get("date_from")
        date_to = request.GET.get("date_to")

        url = f"{API_BASE_URL}/api/doctors/{caregiver_id}/reservations"
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

            paginator = Paginator(all_reservations, 10)
            page_number = request.GET.get("page")
            reservations_page = paginator.get_page(page_number)

            stats = self.get_stats(all_reservations)

            return render(request, self.template_name, {
                "reservations": reservations_page,
                "stats": stats,
                "status_filter": status_filter,
                "date_from": date_from,
                "date_to": date_to,
            })
        except Exception as e:
            messages.error(request, f"Failed to load reservations: {str(e)}")
            return render(request, self.template_name, {
                "reservations": [],
                "stats": {},
                "status_filter": status_filter,
                "date_from": date_from,
                "date_to": date_to,
                "error": str(e)
            })

    def get_stats(self, reservations):
        from collections import Counter
        status_counts = Counter(res.get("status_reservasi") for res in reservations)
        return {
            "waiting": status_counts.get("WAITING", 0),
            "approved": status_counts.get("APPROVED", 0),
            "rejected": status_counts.get("REJECTED", 0),
            "rescheduled": status_counts.get("ON_RESCHEDULE", 0)
        }