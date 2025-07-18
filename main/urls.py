# main/urls.py

from django.urls import path
from . import views

# Define app_name for namespacing URLs
app_name = 'main'

urlpatterns = [
    # Main Dashboard Home page (default)
    path('dashboard/', views.staff_dashboard, {'main_tab': 'home'}, name='home_dashboard'),
    
    # Guest Requests Dashboard (default to active requests)
    path('dashboard/requests/', views.staff_dashboard, {'main_tab': 'requests', 'sub_tab': 'active'}, name='guest_requests_dashboard'),

    # Sub-filters for Guest Requests
    path('dashboard/requests/active/', views.staff_dashboard, {'main_tab': 'requests', 'sub_tab': 'active'}, name='active_requests'),
    path('dashboard/requests/archive/', views.staff_dashboard, {'main_tab': 'requests', 'sub_tab': 'archive'}, name='archive_requests'),
    path('dashboard/requests/all/', views.staff_dashboard, {'main_tab': 'requests', 'sub_tab': 'all'}, name='all_requests'),

    # Guest Management
    path('dashboard/guests/manage/', views.staff_dashboard, {'main_tab': 'guest_management'}, name='guest_management'),

    # API endpoints for staff dashboard
    path('request/<int:request_id>/update_status/', views.update_request_status, name='update_request_status'),
    path('request/<int:request_id>/update_notes/', views.update_staff_notes, name='update_staff_notes'),
    path('api/check_new_requests/', views.check_for_new_requests, name='check_for_new_requests'),
    path('api/requests/<int:request_id>/details/', views.get_request_details, name='get_request_details'),
    path('api/assignments/<int:assignment_id>/edit/', views.edit_guest_assignment, name='edit_guest_assignment_api'),
    path('api/assignments/<int:assignment_id>/delete/', views.delete_guest_assignment, name='delete_guest_assignment_api'),

    # Guest Interface and its API endpoints
    path('guest/<int:hotel_id>/<str:room_number>/', views.guest_interface, name='guest_interface'),
    path('api/process_command/', views.process_guest_command, name='process_guest_command_api'),
    path('api/submit_draft_requests/', views.submit_draft_requests, name='submit_draft_requests_api'),
    # This is the URL that was giving 404, ensure it's exactly as below
    path('api/guest/<int:hotel_id>/room/<str:room_number>/check_updates/', views.check_for_new_updates, name='check_for_new_updates'),
]
