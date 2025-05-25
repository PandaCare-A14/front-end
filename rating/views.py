from django.shortcuts import render, redirect
from django.contrib import messages
from django.views import View
from main.views import api_request, get_base_context
import uuid
from django.http import JsonResponse

class AddRatingView(View):
    def post(self, request, id_jadwal_konsultasi):
        context = get_base_context(request)
        try:
            rating_request = request.POST  # Assuming form submission with rating score and review text
            patient_id = request.session.get("user_id")

            # Validate UUID format
            uuid.UUID(str(id_jadwal_konsultasi))

            # Set the consultation ID in the request
            rating_request['idJadwalKonsultasi'] = id_jadwal_konsultasi

            # Call the backend service to add the rating
            response = api_request(
                "POST",
                f"/api/consultations/{id_jadwal_konsultasi}/ratings",
                data=rating_request,
                token=request.session.get("access_token")
            )

            if response.get('status') == 'success':
                messages.success(request, 'Rating submitted successfully!')
                return redirect("doctor_profile:detail", doctor_id=id_jadwal_konsultasi)
            else:
                messages.error(request, f"Error: {response.get('message')}")

        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")

        return render(request, 'doctor_profile.html', context)

class UpdateRatingView(View):
    def post(self, request, id_jadwal_konsultasi):
        context = get_base_context(request)
        try:
            rating_request = request.POST
            patient_id = request.session.get("user_id")

            # Validate UUID format
            uuid.UUID(str(id_jadwal_konsultasi))

            # Set the consultation ID in the request
            rating_request['idJadwalKonsultasi'] = id_jadwal_konsultasi

            # Call the backend service to update the rating
            response = api_request(
                "PUT",
                f"/api/consultations/{id_jadwal_konsultasi}/ratings",
                data=rating_request,
                token=request.session.get("access_token")
            )

            if response.get('status') == 'success':
                messages.success(request, 'Rating updated successfully!')
            else:
                messages.error(request, f"Error: {response.get('message')}")

        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")

        return render(request, 'doctor_profile.html', context)

class DeleteRatingView(View):
    def post(self, request, id_jadwal_konsultasi):
        context = get_base_context(request)
        try:
            patient_id = request.session.get("user_id")

            # Validate UUID format
            uuid.UUID(str(id_jadwal_konsultasi))

            # Call the backend service to delete the rating
            response = api_request(
                "DELETE",
                f"/api/consultations/{id_jadwal_konsultasi}/ratings",
                token=request.session.get("access_token")
            )

            if response.get('status') == 'success':
                messages.success(request, 'Rating deleted successfully!')
            else:
                messages.error(request, f"Error: {response.get('message')}")

        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")

        return render(request, 'doctor_profile.html', context)

class GetRatingsByDoctorView(View):
    def get(self, request, id_dokter):
        context = get_base_context(request)
        try:
            # Fetch doctor ratings from backend API
            response = api_request(
                "GET",
                f"/api/caregivers/{id_dokter}/ratings",
                token=request.session.get("access_token")
            )

            if response.get('status') == 'success':
                context.update({
                    'ratings': response['data']['ratings'],
                    'total_ratings': response['data']['totalRatings'],
                })
            else:
                messages.error(request, "Error fetching ratings.")

        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")

        return render(request, 'doctor_ratings.html', context)

class CheckRatingStatusView(View):
    def get(self, request, id_jadwal_konsultasi):
        try:
            # Check if the consultation has been rated by the patient
            response = api_request(
                "GET",
                f"/api/consultations/{id_jadwal_konsultasi}/rating/status",
                token=request.session.get("access_token")
            )

            if response.get('status') == 'success':
                has_rated = response['data']['hasRated']
                return JsonResponse({"hasRated": has_rated})
            else:
                return JsonResponse({"error": "Unable to check rating status"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
