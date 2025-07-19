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
    
    # New Amenity Management URL
    path('dashboard/amenities/', views.amenity_management, name='amenity_management'),

    # API Endpoints for Staff Dashboard
    path('api/check_new_requests/', views.check_for_new_requests, name='check_new_requests'),
    path('request/<int:request_id>/update_notes/', views.update_staff_notes, name='update_staff_notes'),
    path('request/<int:request_id>/update_status/', views.update_request_status, name='update_request_status'),
    path('api/requests/<int:request_id>/details/', views.get_request_details, name='get_request_details'),
    path('api/assignments/<int:assignment_id>/edit/', views.edit_guest_assignment, name='edit_guest_assignment'),
    path('api/assignments/<int:assignment_id>/delete/', views.delete_guest_assignment, name='delete_guest_assignment'),
    
    # API Endpoint for Amenity Deletion (New)
    path('api/amenities/<int:amenity_id>/delete/', views.delete_amenity, name='delete_amenity'),


    # Guest Interface URLs
    path('guest/<int:hotel_id>/room/<str:room_number>/', views.guest_interface, name='guest_interface'),
    path('api/process_command/', views.process_guest_command, name='process_guest_command'),
    path('api/guest/<int:hotel_id>/room/<str:room_number>/check_updates/', views.check_for_new_updates, name='check_for_new_updates'),

    # Authentication URLs
    path('logout/', views.user_logout, name='logout'),
]
