# Doctor Profile App

This Django app provides a complete frontend implementation for doctor profile management in the PandaCare healthcare platform.

## Features Implemented

### Views
- **DoctorListView**: Display all available doctors with filtering and search
- **DoctorDetailView**: Show detailed information about a specific doctor
- **DoctorProfileView**: Allow doctors to manage their own profiles
- **DoctorRegistrationView**: New doctor registration and onboarding
- **DoctorSearchView**: Advanced search functionality with filters

### Templates
- **doctor_list.html**: Grid layout showing all doctors with basic info
- **doctor_detail.html**: Comprehensive doctor profile page with availability
- **doctor_profile.html**: Profile management form for doctors
- **doctor_register.html**: Registration form for new doctors
- **doctor_search.html**: Advanced search interface with specialization filters

### URL Patterns
- `/doctors/` - List all doctors
- `/doctors/search/` - Search doctors
- `/doctors/register/` - Doctor registration
- `/doctors/profile/` - Doctor profile management (authenticated)
- `/doctors/<int:doctor_id>/` - Individual doctor details

## API Integration

The views are designed to work with a Spring Boot backend API with the following expected endpoints:

### Doctor Endpoints
- `GET /api/doctors/` - Get all doctors
- `GET /api/doctors/{id}/` - Get specific doctor
- `GET /api/doctors/profile/{userId}/` - Get doctor profile (authenticated)
- `PUT /api/doctors/profile/{userId}/` - Update doctor profile (authenticated)
- `POST /api/doctors/register/` - Register new doctor
- `GET /api/doctors/search/` - Search doctors with parameters
- `GET /api/doctors/specializations/` - Get available specializations

### Expected Data Structure

```json
{
  "id": 1,
  "name": "John Doe",
  "specialization": "Cardiology",
  "experience": 10,
  "education": "Harvard Medical School",
  "hospital": "General Hospital",
  "bio": "Experienced cardiologist...",
  "consultationFee": 150000,
  "phone": "+62-xxx-xxxx-xxxx",
  "email": "doctor@example.com",
  "availableFromMonday": "09:00",
  "availableToMonday": "17:00",
  // ... availability for other days
}
```

## Authentication

The app integrates with the existing authentication system:
- Uses session-based authentication
- Checks for `access_token` in session
- Supports role-based access (doctor, patient, guest)
- Protected routes require authentication

## Styling

All templates use:
- Tailwind CSS for styling
- Font Awesome icons
- Responsive design (mobile-first)
- Consistent color scheme with the main app
- Modern UI components (cards, forms, buttons)

## Error Handling

- API connection errors are handled gracefully
- User-friendly error messages
- Fallback content when data is unavailable
- Form validation and feedback

## Environment Variables

Required environment variables:
- `API_BASE_URL`: Base URL for the Spring Boot API (default: http://localhost:8080)

## Installation

1. The app is already registered in `INSTALLED_APPS`
2. URLs are included in the main URL configuration
3. Templates are properly organized in the templates directory
4. No additional dependencies required beyond the main project

## Usage

### For Patients
- Browse and search for doctors
- View detailed doctor profiles
- See doctor availability and consultation fees
- Book appointments (integration needed)

### For Doctors
- Register as a new doctor
- Manage profile information
- Set availability schedule
- Update consultation fees

## Future Enhancements

- Doctor verification system
- Review and rating system
- Advanced filtering (location, languages, etc.)
- Online consultation booking
- Integration with calendar systems
- Photo upload for doctor profiles
- Specialization-specific fields
