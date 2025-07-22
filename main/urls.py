# main/urls.py

from django.urls import path
from . import views

app_name = 'main' # Set app namespace

urlpatterns = [
    # Staff Dashboard URLs
    path('dashboard/', views.staff_dashboard, {'main_tab': 'home'}, name='home_dashboard'),
    path('dashboard/requests/', views.staff_dashboard, {'main_tab': 'requests'}, name='guest_requests_dashboard'),
    path('dashboard/requests/active/', views.staff_dashboard, {'main_tab': 'requests', 'sub_tab': 'active'}, name='active_requests'),
    path('dashboard/requests/archive/', views.staff_dashboard, {'main_tab': 'requests', 'sub_tab': 'archive'}, name='archive_requests'),
    path('dashboard/requests/all/', views.staff_dashboard, {'main_tab': 'requests', 'sub_tab': 'all'}, name='all_requests'),
    path('dashboard/guests/', views.staff_dashboard, {'main_tab': 'guest_management'}, name='guest_management'),
    
    # Amenity Management Dashboard URL (now points to staff_dashboard)
    path('dashboard/amenities/', views.staff_dashboard, {'main_tab': 'amenities'}, name='amenity_management'),

    # API Endpoints for Staff Dashboard
    path('api/check_new_requests/', views.check_new_requests, name='check_new_requests'), # Corrected view function name
    
    # NEW API: Update GuestRequest (replaces update_notes and update_status)
    path('api/requests/<int:request_id>/update/', views.update_request_api, name='update_request_api'),
    
    path('api/requests/<int:request_id>/details/', views.request_details_api, name='request_details_api'), # Corrected view function name
    path('api/assignments/<int:assignment_id>/edit/', views.edit_assignment_api, name='edit_assignment_api'), # Corrected view function name
    path('api/assignments/<int:assignment_id>/delete/', views.delete_assignment_api, name='delete_assignment_api'),
    
    # API Endpoint for Amenity Details (NEW)
    path('api/amenities/<int:amenity_id>/', views.amenity_detail_api, name='amenity_detail_api'),
    # API Endpoint for Amenity Deletion
    path('api/amenities/<int:amenity_id>/delete/', views.delete_amenity_api, name='delete_amenity_api'), # Corrected view function name


    # Guest Interface URLs (assuming these views exist and are correct)
    path('guest/<int:hotel_id>/room/<str:room_number>/', views.guest_interface, name='guest_interface'),
    path('api/process_command/', views.process_guest_command, name='process_guest_command'),
    path('api/guest/<int:hotel_id>/room/<str:room_number>/check_updates/', views.check_for_new_updates, name='check_for_new_updates'),

    # Authentication URLs (assuming these views exist and are correct)
    path('logout/', views.user_logout, name='logout'),
]
