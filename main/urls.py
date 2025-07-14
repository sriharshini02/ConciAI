from django.urls import path
from . import views

# Define app_name for namespacing URLs
app_name = 'main'

urlpatterns = [
    # Path for the staff dashboard
    path('dashboard/', views.staff_dashboard, name='staff_dashboard'),
    
    # Specific paths for different request tabs
    path('dashboard/requests/active/', views.staff_dashboard, {'status_filter': ['pending', 'in_progress']}, name='active_requests'),
    path('dashboard/requests/archive/', views.staff_dashboard, {'status_filter': ['completed', 'cancelled']}, name='archive_requests'),

    # Path for updating a guest request status
    path(
        'request/<int:request_id>/update_status/',
        views.update_request_status,
        name='update_request_status'
    ),

    # Path for the simulated guest interface - now includes hotel_id
    path('guest/<int:hotel_id>/<str:room_number>/', views.guest_interface, name='guest_interface'),

    # API endpoint to process guest commands (AI processing only, no direct DB save for actionable intents)
    path('api/process_command/', views.process_guest_command, name='process_guest_command_api'),

    # API endpoint to submit confirmed draft requests to the database
    path('api/submit_draft_requests/', views.submit_draft_requests, name='submit_draft_requests_api'),

    # Path for guest management (adding new room assignments)
    path('dashboard/guests/manage/', views.guest_management_view, name='guest_management'),

    # NEW: Paths for editing and deleting guest assignments
    path('api/assignments/<int:assignment_id>/edit/', views.edit_guest_assignment, name='edit_guest_assignment_api'),
    path('api/assignments/<int:assignment_id>/delete/', views.delete_guest_assignment, name='delete_guest_assignment_api'),
]
