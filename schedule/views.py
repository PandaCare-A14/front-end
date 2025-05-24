from django.http import HttpResponseNotAllowed, JsonResponse
import requests
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
import calendar
from django.views.decorators.http import require_POST
import json
import logging

DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def schedule_list(request, caregiver_id):
    day_filter = request.GET.get("day", "")
    if day_filter:
        day_filter = day_filter.capitalize().lower().title()
    status_filter = request.GET.get("status")
    response = requests.get(f"http://localhost:8080/api/doctors/{caregiver_id}/schedules")
    schedules = response.json().get("data", [])
    context = {
        "schedules": schedules,
        "day_filter": day_filter,
        "status_filter": status_filter,
        "days": DAYS_OF_WEEK,
        "caregiver_id": caregiver_id,
    }
    return render(request, "schedule_list.html", context)

@csrf_exempt
def create_schedule(request, caregiver_id):
    if request.method == "GET":
        return render(request, "create_schedule.html", {"caregiver_id": caregiver_id})
    
    if request.method == "POST":
        body = json.loads(request.body.decode('utf-8'))

        res = requests.post(
            f"http://localhost:8080/api/doctors/{caregiver_id}/schedules",
            json=body
        )

        if res.status_code == 201:
            return JsonResponse({"status": 201, "message": "Created successfully", "success": True})
        return JsonResponse({"status": res.status_code, "message": res.text, "success": False})

@require_POST
@csrf_exempt
def delete_schedule(request, caregiver_id, schedule_id):
    try:
        url = f"http://localhost:8080/api/doctors/{caregiver_id}/schedules/{schedule_id}"
        response = requests.delete(url)

        if response.status_code == 200:
            return redirect("schedule_list", caregiver_id=caregiver_id)
        elif response.status_code == 404:
            return render(request, "error.html", {"message": "Schedule not found."})
        elif response.status_code == 409:
            return render(request, "error.html", {"message": "Cannot delete schedule due to conflict."})
        else:
            return render(request, "error.html", {"message": "Unexpected error occurred."})
    except requests.RequestException:
        return render(request, "error.html", {"message": "Failed to connect to backend."})

