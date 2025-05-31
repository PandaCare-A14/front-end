from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import requests
import uuid
from datetime import datetime
from functools import wraps
from main.views import api_request, get_base_context, is_logged_in


def require_pacilian_auth(view_func):
    """Decorator to ensure user is logged in as a patient"""
    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        if not is_logged_in(request) or request.session.get("user_role") != "pacilian":
            messages.error(request, "Anda harus login sebagai pasien untuk mengakses halaman ini")
            return redirect("main:login")
        return view_func(self, request, *args, **kwargs)
    return wrapper


class RatingUtils:
    """Utility functions for rating operations"""
    
    @staticmethod
    def get_session_data(request):
        """Extract session data needed for API calls"""
        return {
            'patient_id': request.session.get("user_id"),
            'token': request.session.get("access_token")
        }
    
    @staticmethod
    def validate_rating_score(rating_score):
        """Validate rating score is between 1-5"""
        try:
            score = int(rating_score)
            if 1 <= score <= 5:
                return score, None
            return None, "Rating score harus di antara 1 dan 5"
        except (ValueError, TypeError):
            return None, "Rating score harus berupa angka"
    
    @staticmethod
    def get_doctor_info(caregiver_id, token):
        """Get doctor name and speciality from API"""
        if not caregiver_id:
            return "Unknown Doctor", ""
        
        try:
            doctor_response = api_request("GET", f"/api/doctors/{caregiver_id}", token=token)
            if doctor_response:
                name = f"Dr. {doctor_response.get('name', 'Unknown')}"
                speciality = doctor_response.get('speciality', '')
                return name, speciality
        except Exception:
            pass
        return "Unknown Doctor", ""
    
    @staticmethod
    def format_consultation_time(schedule):
        """Format consultation time from schedule"""
        if not schedule:
            return ""
        start_time = schedule.get('startTime', '')
        end_time = schedule.get('endTime', '')
        return f"{start_time} - {end_time}" if start_time and end_time else ""
    
    @staticmethod
    def find_consultation(reservations, consultation_id):
        """Find specific consultation in reservations list"""
        if not reservations:
            return None
        for reservation in reservations:
            if reservation.get('id') == str(consultation_id):
                return reservation
        return None


class RatingAPI:
    """API wrapper for rating operations"""
    
    @staticmethod
    def get_reservations(patient_id, token):
        """Get all patient reservations"""
        return api_request("GET", f"/api/reservasi-konsultasi/{patient_id}", token=token)
    
    @staticmethod
    def check_rating_status(consultation_id, token):
        """Check if consultation already has a rating"""
        try:
            response = api_request("GET", f"/api/async/consultations/{consultation_id}/rating/status", token=token)
            return response.get('data', {}).get('hasRated', False) if response else False
        except Exception:
            return False
    
    @staticmethod
    def get_existing_rating(consultation_id, token):
        """Get existing rating for consultation"""
        try:
            response = api_request("GET", f"/api/async/consultations/{consultation_id}/ratings", token=token)
            return response.get('data', {}).get('rating') if response else None
        except Exception:
            return None
    
    @staticmethod
    def submit_rating(consultation_id, rating_score, ulasan, token):
        """Submit new rating"""
        return api_request(
            "POST",
            f"/api/async/consultations/{consultation_id}/ratings",
            data={
                "ratingScore": rating_score,
                "ulasan": ulasan.strip(),
                "idJadwalKonsultasi": str(consultation_id)
            },
            token=token
        )
    
    @staticmethod
    def update_rating(consultation_id, rating_score, ulasan, token):
        """Update existing rating"""
        return api_request(
            "PUT",
            f"/api/async/consultations/{consultation_id}/ratings",
            data={
                "ratingScore": rating_score,
                "ulasan": ulasan.strip(),
                "idJadwalKonsultasi": str(consultation_id)
            },
            token=token
        )
    
    @staticmethod
    def delete_rating(consultation_id, token):
        """Delete existing rating"""
        return api_request("DELETE", f"/api/async/consultations/{consultation_id}/ratings", token=token)


class RatingContextBuilder:
    """Builder for creating context data for different views"""
    
    @staticmethod
    def build_consultation_data(reservation, token):
        """Build consultation data for list view"""
        consultation_id = reservation.get('id')
        schedule = reservation.get('idSchedule', {})
        caregiver_id = schedule.get('caregiverId') if schedule else None
        doctor_name, doctor_speciality = RatingUtils.get_doctor_info(caregiver_id, token)
        
        has_rating = RatingAPI.check_rating_status(consultation_id, token)
        existing_rating = RatingAPI.get_existing_rating(consultation_id, token) if has_rating else None
        
        return {
            'id': consultation_id,
            'doctor_name': doctor_name,
            'doctor_speciality': doctor_speciality,
            'caregiver_id': caregiver_id,
            'consultation_date': schedule.get('date') if schedule else None,
            'consultation_time': RatingUtils.format_consultation_time(schedule),
            'has_rating': has_rating,
            'existing_rating': existing_rating,
            'pacilian_note': reservation.get('pacilianNote', ''),
            'status': reservation.get('statusReservasi')
        }
    
    @staticmethod
    def build_form_context(consultation, patient_id, token, mode='add', existing_rating=None):
        """Build context for form views (add/edit)"""
        schedule = consultation.get('idSchedule', {})
        caregiver_id = schedule.get('caregiverId') if schedule else None
        doctor_name, _ = RatingUtils.get_doctor_info(caregiver_id, token)
        
        context = {
            'consultation_id': consultation.get('id'),
            'id_pacilian': patient_id,
            'doctor_name': doctor_name,
            'consultation_date': schedule.get('date') if schedule else None,
            'consultation_time': RatingUtils.format_consultation_time(schedule),
            'mode': mode
        }
        
        if existing_rating:
            context['existing_rating'] = existing_rating
            
        return context
    
    @staticmethod
    def build_detail_context(consultation, patient_id, token, rating):
        """Build context for detail view"""
        schedule = consultation.get('idSchedule', {})
        caregiver_id = schedule.get('caregiverId') if schedule else None
        doctor_name, doctor_speciality = RatingUtils.get_doctor_info(caregiver_id, token)
        
        return {
            'consultation_id': consultation.get('id'),
            'id_pacilian': patient_id,
            'doctor_name': doctor_name,
            'doctor_speciality': doctor_speciality,
            'consultation_date': schedule.get('date') if schedule else None,
            'consultation_time': RatingUtils.format_consultation_time(schedule),
            'rating': rating
        }


class RatingListView(View):
    """View for listing all consultations with rating status"""
    template_name = 'rating_list.html'

    @require_pacilian_auth
    def get(self, request, id_pacilian):
        context = get_base_context(request)
        session_data = RatingUtils.get_session_data(request)
        
        try:
            reservations_response = RatingAPI.get_reservations(id_pacilian, session_data['token'])
            
            if not reservations_response:
                context['consultations'] = []
                return render(request, self.template_name, context)

            # Filter approved consultations and build data
            approved_consultations = [
                RatingContextBuilder.build_consultation_data(reservation, session_data['token'])
                for reservation in reservations_response
                if reservation.get('statusReservasi') == 'APPROVED'
            ]

            # Sort by consultation date (newest first)
            approved_consultations.sort(key=lambda x: x.get('consultation_date') or '', reverse=True)
            
            context.update({
                'consultations': approved_consultations,
                'total_consultations': len(approved_consultations)
            })

        except Exception as e:
            messages.error(request, f"Error loading consultations: {str(e)}")
            context['consultations'] = []
            print(f"Error loading consultations: {str(e)}")

        return render(request, self.template_name, context)


class RatingFormMixin:
    """Mixin for form-based rating views (add/edit)"""
    template_name = 'rating_form.html'
    
    def get_consultation_context(self, request, consultation_id, mode='add'):
        """Get consultation context for form views"""
        session_data = RatingUtils.get_session_data(request)
        
        reservations = RatingAPI.get_reservations(session_data['patient_id'], session_data['token'])
        consultation = RatingUtils.find_consultation(reservations, consultation_id)
        
        if not consultation:
            return None, "Consultation not found"
        
        existing_rating = None
        if mode == 'edit':
            existing_rating = RatingAPI.get_existing_rating(consultation_id, session_data['token'])
            if not existing_rating:
                return None, "Rating not found"
        
        context = RatingContextBuilder.build_form_context(
            consultation, session_data['patient_id'], session_data['token'], mode, existing_rating
        )
        
        return context, None
    
    def handle_form_submission(self, request, consultation_id, is_update=False):
        """Handle form submission for both add and edit"""
        session_data = RatingUtils.get_session_data(request)
        
        rating_score = request.POST.get('rating_score')
        ulasan = request.POST.get('ulasan')
        
        # Validate required fields
        if not rating_score or not ulasan:
            messages.error(request, "Rating score dan ulasan harus diisi")
            return False
        
        # Validate rating score
        validated_score, error_msg = RatingUtils.validate_rating_score(rating_score)
        if error_msg:
            messages.error(request, error_msg)
            return False
        
        try:
            # Choose API method based on operation type
            if is_update:
                response = RatingAPI.update_rating(consultation_id, validated_score, ulasan, session_data['token'])
                success_msg = "Rating berhasil diperbarui!"
                error_prefix = "Gagal memperbarui rating:"
            else:
                response = RatingAPI.submit_rating(consultation_id, validated_score, ulasan, session_data['token'])
                success_msg = "Rating berhasil ditambahkan!"
                error_prefix = "Gagal menambahkan rating:"
            
            # Handle response
            if response and response.get('status') == 'success':
                messages.success(request, success_msg)
                return True
            else:
                error_msg = response.get('message', 'Unknown error') if response else 'Unknown error'
                messages.error(request, f"{error_prefix} {error_msg}")
                return False
                
        except Exception as e:
            messages.error(request, f"Error processing rating: {str(e)}")
            return False


class AddRatingView(RatingFormMixin, View):
    """View for adding new rating"""
    
    @require_pacilian_auth
    def get(self, request, consultation_id):
        context = get_base_context(request)
        session_data = RatingUtils.get_session_data(request)
        
        # Check if rating already exists
        if RatingAPI.check_rating_status(consultation_id, session_data['token']):
            messages.warning(request, "Konsultasi ini sudah memiliki rating. Gunakan fitur edit untuk mengubah.")
            return redirect("rating:list", id_pacilian=session_data['patient_id'])
        
        consultation_context, error = self.get_consultation_context(request, consultation_id, 'add')
        if error:
            messages.error(request, error)
            return redirect("rating:list", id_pacilian=session_data['patient_id'])
        
        context.update(consultation_context)
        return render(request, self.template_name, context)

    @require_pacilian_auth
    def post(self, request, consultation_id):
        session_data = RatingUtils.get_session_data(request)
        
        if self.handle_form_submission(request, consultation_id, is_update=False):
            return redirect("rating:list", id_pacilian=session_data['patient_id'])
        
        return redirect("rating:add", consultation_id=consultation_id)


class EditRatingView(RatingFormMixin, View):
    """View for editing existing rating"""
    
    @require_pacilian_auth
    def get(self, request, consultation_id):
        context = get_base_context(request)
        session_data = RatingUtils.get_session_data(request)
        
        consultation_context, error = self.get_consultation_context(request, consultation_id, 'edit')
        if error:
            messages.error(request, error)
            return redirect("rating:list", id_pacilian=session_data['patient_id'])
        
        context.update(consultation_context)
        return render(request, self.template_name, context)

    @require_pacilian_auth
    def post(self, request, consultation_id):
        session_data = RatingUtils.get_session_data(request)
        
        if self.handle_form_submission(request, consultation_id, is_update=True):
            return redirect("rating:list", id_pacilian=session_data['patient_id'])
        
        return redirect("rating:edit", consultation_id=consultation_id)


@method_decorator(csrf_exempt, name='dispatch')
class DeleteRatingView(View):
    """View for deleting rating"""
    
    @require_pacilian_auth
    def post(self, request, consultation_id):
        session_data = RatingUtils.get_session_data(request)

        try:
            response = RatingAPI.delete_rating(consultation_id, session_data['token'])
            
            if response and response.get('status') == 'success':
                messages.success(request, "Rating berhasil dihapus!")
            else:
                error_msg = response.get('message', 'Failed to delete rating') if response else 'Failed to delete rating'
                messages.error(request, f"Gagal menghapus rating: {error_msg}")
                
        except Exception as e:
            messages.error(request, f"Error deleting rating: {str(e)}")

        return redirect("rating:list", id_pacilian=session_data['patient_id'])


class ViewRatingView(View):
    """View for viewing rating details"""
    template_name = 'rating_detail.html'

    @require_pacilian_auth
    def get(self, request, consultation_id):
        context = get_base_context(request)
        session_data = RatingUtils.get_session_data(request)

        try:
            # Get rating and consultation data
            rating = RatingAPI.get_existing_rating(consultation_id, session_data['token'])
            if not rating:
                messages.error(request, "Rating not found")
                return redirect("rating:list", id_pacilian=session_data['patient_id'])

            reservations = RatingAPI.get_reservations(session_data['patient_id'], session_data['token'])
            consultation = RatingUtils.find_consultation(reservations, consultation_id)
            
            if not consultation:
                messages.error(request, "Consultation not found")
                return redirect("rating:list", id_pacilian=session_data['patient_id'])

            detail_context = RatingContextBuilder.build_detail_context(
                consultation, session_data['patient_id'], session_data['token'], rating
            )
            
            context.update(detail_context)
            return render(request, self.template_name, context)

        except Exception as e:
            messages.error(request, f"Error loading rating details: {str(e)}")
            print(f"Error loading rating details: {str(e)}")
            return redirect("rating:list", id_pacilian=session_data['patient_id'])