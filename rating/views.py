from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import requests
import uuid
from datetime import datetime
from main.views import api_request, get_base_context, is_logged_in

class RatingListView(View):
    template_name = 'rating_list.html'

    def get(self, request, id_pacilian):
        context = get_base_context(request)

        # Check if user is logged in as patient
        if not is_logged_in(request) or request.session.get("user_role") != "pacilian":
            messages.error(request, "Anda harus login sebagai pasien untuk mengakses halaman ini")
            return redirect("main:login")

        patient_id = id_pacilian  # Get the patient ID from the URL

        try:
            # Get all reservations for the patient
            reservations_response = api_request(
                "GET",
                f"/api/reservasi-konsultasi/{patient_id}",
                token=request.session.get("access_token")
            )

            if not reservations_response:
                context['consultations'] = []
                return render(request, self.template_name, context)

            # Filter only APPROVED reservations
            approved_consultations = []
            for reservation in reservations_response:
                if reservation.get('statusReservasi') == 'APPROVED':
                    consultation_id = reservation.get('id')

                    # Check rating status for this consultation
                    rating_status_response = api_request(
                        "GET",
                        f"/api/async/consultations/{consultation_id}/rating/status",
                        token=request.session.get("access_token")
                    )

                    # Get existing rating if available
                    existing_rating = None
                    if rating_status_response and rating_status_response.get('data', {}).get('hasRated', False):
                        rating_response = api_request(
                            "GET",
                            f"/api/async/consultations/{consultation_id}/ratings",
                            token=request.session.get("access_token")
                        )
                        if rating_response:
                            existing_rating = rating_response.get('data', {}).get('rating')

                    # Get doctor info from schedule
                    schedule = reservation.get('idSchedule', {})
                    caregiver_id = schedule.get('caregiverId') if schedule else None
                    doctor_name = "Unknown Doctor"
                    doctor_speciality = ""

                    if caregiver_id:
                        doctor_response = api_request(
                            "GET",
                            f"/api/doctors/{caregiver_id}",
                            token=request.session.get("access_token")
                        )
                        if doctor_response:
                            doctor_name = f"Dr. {doctor_response.get('name', 'Unknown')}"
                            doctor_speciality = doctor_response.get('speciality', '')

                    consultation_data = {
                        'id': consultation_id,
                        'doctor_name': doctor_name,
                        'doctor_speciality': doctor_speciality,
                        'caregiver_id': caregiver_id,
                        'consultation_date': schedule.get('date') if schedule else None,
                        'consultation_time': f"{schedule.get('startTime', '')} - {schedule.get('endTime', '')}" if schedule else "",
                        'has_rating': rating_status_response.get('data', {}).get('hasRated', False) if rating_status_response else False,
                        'existing_rating': existing_rating,
                        'pacilian_note': reservation.get('pacilianNote', ''),
                        'status': reservation.get('statusReservasi')
                    }
                    approved_consultations.append(consultation_data)

            # Sort by consultation date (newest first)
            approved_consultations.sort(key=lambda x: x.get('consultation_date', ''), reverse=True)

            context['consultations'] = approved_consultations
            context['total_consultations'] = len(approved_consultations)

            return render(request, self.template_name, context)

        except Exception as e:
            messages.error(request, f"Error loading consultations: {str(e)}")
            context['consultations'] = []
            return render(request, self.template_name, context)

class AddRatingView(View):
    template_name = 'rating_form.html'

    def get(self, request, consultation_id):
        context = get_base_context(request)

        if not is_logged_in(request) or request.session.get("user_role") != "pacilian":
            messages.error(request, "Unauthorized access")
            return redirect("main:login")

        try:
            # Validate consultation exists and belongs to patient
            patient_id = request.session.get("user_id")

            # Check if consultation has already been rated
            rating_status_response = api_request(
                "GET",
                f"/api/async/consultations/{consultation_id}/rating/status",
                token=request.session.get("access_token")
            )

            if rating_status_response and rating_status_response.get('data', {}).get('hasRated', False):
                messages.warning(request, "Konsultasi ini sudah memiliki rating. Gunakan fitur edit untuk mengubah.")
                return redirect("rating:list")

            # Get consultation details for display
            reservations_response = api_request(
                "GET",
                f"/api/reservasi-konsultasi/{patient_id}",
                token=request.session.get("access_token")
            )

            consultation = None
            if reservations_response:
                for reservation in reservations_response:
                    if reservation.get('id') == str(consultation_id):
                        consultation = reservation
                        break

            if not consultation:
                messages.error(request, "Consultation not found")
                return redirect("rating:list")

            # Get doctor info
            schedule = consultation.get('idSchedule', {})
            caregiver_id = schedule.get('caregiverId') if schedule else None
            doctor_name = "Unknown Doctor"

            if caregiver_id:
                doctor_response = api_request(
                    "GET",
                    f"/api/doctors/{caregiver_id}",
                    token=request.session.get("access_token")
                )
                if doctor_response:
                    doctor_name = f"Dr. {doctor_response.get('name', 'Unknown')}"

            context.update({
                'consultation_id': consultation_id,
                'doctor_name': doctor_name,
                'consultation_date': schedule.get('date') if schedule else None,
                'consultation_time': f"{schedule.get('startTime', '')} - {schedule.get('endTime', '')}" if schedule else "",
                'mode': 'add'
            })

            return render(request, self.template_name, context)

        except Exception as e:
            messages.error(request, f"Error loading consultation: {str(e)}")
            return redirect("rating:list")

    def post(self, request, consultation_id):
        if not is_logged_in(request) or request.session.get("user_role") != "pacilian":
            messages.error(request, "Unauthorized access")
            return redirect("main:login")

        try:
            rating_score = request.POST.get('rating_score')
            ulasan = request.POST.get('ulasan')

            if not rating_score or not ulasan:
                messages.error(request, "Rating score dan ulasan harus diisi")
                return redirect("rating:add", consultation_id=consultation_id)

            # Validate rating score
            try:
                rating_score = int(rating_score)
                if rating_score < 1 or rating_score > 5:
                    raise ValueError()
            except ValueError:
                messages.error(request, "Rating score harus di antara 1 dan 5")
                return redirect("rating:add", consultation_id=consultation_id)

            # Submit rating
            response = api_request(
                "POST",
                f"/api/async/consultations/{consultation_id}/ratings",
                data={
                    "ratingScore": rating_score,
                    "ulasan": ulasan.strip(),
                    "idJadwalKonsultasi": str(consultation_id)
                },
                token=request.session.get("access_token")
            )

            if response and response.get('status') == 'success':
                messages.success(request, "Rating berhasil ditambahkan!")
                return redirect("rating:list")
            else:
                error_msg = response.get('message', 'Failed to add rating') if response else 'Failed to add rating'
                messages.error(request, f"Gagal menambahkan rating: {error_msg}")
                return redirect("rating:add", consultation_id=consultation_id)

        except Exception as e:
            messages.error(request, f"Error adding rating: {str(e)}")
            return redirect("rating:add", consultation_id=consultation_id)

class EditRatingView(View):
    template_name = 'rating_form.html'

    def get(self, request, consultation_id):
        context = get_base_context(request)

        if not is_logged_in(request) or request.session.get("user_role") != "pacilian":
            messages.error(request, "Unauthorized access")
            return redirect("main:login")

        try:
            # Get existing rating
            rating_response = api_request(
                "GET",
                f"/api/async/consultations/{consultation_id}/ratings",
                token=request.session.get("access_token")
            )

            if not rating_response or not rating_response.get('data', {}).get('rating'):
                messages.error(request, "Rating not found")
                return redirect("rating:list")

            existing_rating = rating_response['data']['rating']

            # Get consultation details
            patient_id = request.session.get("user_id")
            reservations_response = api_request(
                "GET",
                f"/api/reservasi-konsultasi/{patient_id}",
                token=request.session.get("access_token")
            )

            consultation = None
            if reservations_response:
                for reservation in reservations_response:
                    if reservation.get('id') == str(consultation_id):
                        consultation = reservation
                        break

            if not consultation:
                messages.error(request, "Consultation not found")
                return redirect("rating:list")

            # Get doctor info
            schedule = consultation.get('idSchedule', {})
            caregiver_id = schedule.get('caregiverId') if schedule else None
            doctor_name = "Unknown Doctor"

            if caregiver_id:
                doctor_response = api_request(
                    "GET",
                    f"/api/doctors/{caregiver_id}",
                    token=request.session.get("access_token")
                )
                if doctor_response:
                    doctor_name = f"Dr. {doctor_response.get('name', 'Unknown')}"

            context.update({
                'consultation_id': consultation_id,
                'doctor_name': doctor_name,
                'consultation_date': schedule.get('date') if schedule else None,
                'consultation_time': f"{schedule.get('startTime', '')} - {schedule.get('endTime', '')}" if schedule else "",
                'existing_rating': existing_rating,
                'mode': 'edit'
            })

            return render(request, self.template_name, context)

        except Exception as e:
            messages.error(request, f"Error loading rating: {str(e)}")
            return redirect("rating:list")

    def post(self, request, consultation_id):
        if not is_logged_in(request) or request.session.get("user_role") != "pacilian":
            messages.error(request, "Unauthorized access")
            return redirect("main:login")

        try:
            rating_score = request.POST.get('rating_score')
            ulasan = request.POST.get('ulasan')

            if not rating_score or not ulasan:
                messages.error(request, "Rating score dan ulasan harus diisi")
                return redirect("rating:edit", consultation_id=consultation_id)

            # Validate rating score
            try:
                rating_score = int(rating_score)
                if rating_score < 1 or rating_score > 5:
                    raise ValueError()
            except ValueError:
                messages.error(request, "Rating score harus di antara 1 dan 5")
                return redirect("rating:edit", consultation_id=consultation_id)

            # Update rating
            response = api_request(
                "PUT",
                f"/api/async/consultations/{consultation_id}/ratings",
                data={
                    "ratingScore": rating_score,
                    "ulasan": ulasan.strip(),
                    "idJadwalKonsultasi": str(consultation_id)
                },
                token=request.session.get("access_token")
            )

            if response and response.get('status') == 'success':
                messages.success(request, "Rating berhasil diperbarui!")
                return redirect("rating:list")
            else:
                error_msg = response.get('message', 'Failed to update rating') if response else 'Failed to update rating'
                messages.error(request, f"Gagal memperbarui rating: {error_msg}")
                return redirect("rating:edit", consultation_id=consultation_id)

        except Exception as e:
            messages.error(request, f"Error updating rating: {str(e)}")
            return redirect("rating:edit", consultation_id=consultation_id)

@method_decorator(csrf_exempt, name='dispatch')
class DeleteRatingView(View):
    def post(self, request, consultation_id):
        if not is_logged_in(request) or request.session.get("user_role") != "pacilian":
            messages.error(request, "Unauthorized access")
            return redirect("main:login")

        try:
            # Delete rating
            response = api_request(
                "DELETE",
                f"/api/async/consultations/{consultation_id}/ratings",
                token=request.session.get("access_token")
            )

            if response and response.get('status') == 'success':
                messages.success(request, "Rating berhasil dihapus!")
            else:
                error_msg = response.get('message', 'Failed to delete rating') if response else 'Failed to delete rating'
                messages.error(request, f"Gagal menghapus rating: {error_msg}")

        except Exception as e:
            messages.error(request, f"Error deleting rating: {str(e)}")

        return redirect("rating:list")

class ViewRatingView(View):
    template_name = 'rating_detail.html'

    def get(self, request, consultation_id):
        context = get_base_context(request)

        if not is_logged_in(request) or request.session.get("user_role") != "pacilian":
            messages.error(request, "Unauthorized access")
            return redirect("main:login")

        try:
            # Get rating details
            rating_response = api_request(
                "GET",
                f"/api/async/consultations/{consultation_id}/ratings",
                token=request.session.get("access_token")
            )

            if not rating_response or not rating_response.get('data', {}).get('rating'):
                messages.error(request, "Rating not found")
                return redirect("rating:list")

            rating = rating_response['data']['rating']

            # Get consultation details
            patient_id = request.session.get("user_id")
            reservations_response = api_request(
                "GET",
                f"/api/reservasi-konsultasi/{patient_id}",
                token=request.session.get("access_token")
            )

            consultation = None
            if reservations_response:
                for reservation in reservations_response:
                    if reservation.get('id') == str(consultation_id):
                        consultation = reservation
                        break

            if not consultation:
                messages.error(request, "Consultation not found")
                return redirect("rating:list")

            # Get doctor info
            schedule = consultation.get('idSchedule', {})
            caregiver_id = schedule.get('caregiverId') if schedule else None
            doctor_name = "Unknown Doctor"
            doctor_speciality = ""

            if caregiver_id:
                doctor_response = api_request(
                    "GET",
                    f"/api/doctors/{caregiver_id}",
                    token=request.session.get("access_token")
                )
                if doctor_response:
                    doctor_name = f"Dr. {doctor_response.get('name', 'Unknown')}"
                    doctor_speciality = doctor_response.get('speciality', '')

            context.update({
                'consultation_id': consultation_id,
                'doctor_name': doctor_name,
                'doctor_speciality': doctor_speciality,
                'consultation_date': schedule.get('date') if schedule else None,
                'consultation_time': f"{schedule.get('startTime', '')} - {schedule.get('endTime', '')}" if schedule else "",
                'rating': rating
            })

            return render(request, self.template_name, context)

        except Exception as e:
            messages.error(request, f"Error loading rating details: {str(e)}")
            return redirect("rating:list")