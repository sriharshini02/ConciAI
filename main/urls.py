# main/urls.py

from django.urls import path
from . import views
from django.contrib.auth import views as auth_views # Import Django's built-in auth views

app_name = 'main' # Set app namespace

urlpatterns = [
    # Existing Staff (Admin) Dashboard URLs
    path('dashboard/', views.staff_dashboard, {'main_tab': 'home'}, name='home_dashboard'),
    path('dashboard/requests/', views.staff_dashboard, {'main_tab': 'requests'}, name='guest_requests_dashboard'),
    path('dashboard/requests/active/', views.staff_dashboard, {'main_tab': 'requests', 'sub_tab': 'active'}, name='active_requests'),
    path('dashboard/requests/archive/', views.staff_dashboard, {'main_tab': 'requests', 'sub_tab': 'archive'}, name='archive_requests'),
    path('dashboard/requests/all/', views.staff_dashboard, {'main_tab': 'requests', 'sub_tab': 'all'}, name='all_requests'),
    path('dashboard/guests/', views.staff_dashboard, {'main_tab': 'guest_management'}, name='guest_management'),
    path('dashboard/amenities/', views.staff_dashboard, {'main_tab': 'amenities'}, name='amenity_management'),

    # API Endpoints for Staff (Admin) Dashboard
    path('api/check_new_requests/', views.check_new_requests, name='check_new_requests'),
    path('api/requests/<int:request_id>/update/', views.update_request_api, name='update_request_api'),
    path('api/requests/<int:request_id>/details/', views.request_details_api, name='request_details_api'),
    path('api/assignments/<int:assignment_id>/edit/', views.edit_assignment_api, name='edit_assignment_api'),
    path('api/assignments/<int:assignment_id>/delete/', views.delete_assignment_api, name='delete_assignment_api'),
    path('api/amenities/<int:amenity_id>/', views.amenity_detail_api, name='amenity_detail_api'),
    path('api/amenities/<int:amenity_id>/delete/', views.delete_amenity, name='delete_amenity_api'),
    path('api/amenities/save/', views.staff_dashboard, name='save_amenity_api'), # For new amenity creation/update

    # Guest Interface URLs (assuming these views exist and are correct)
    path('guest/<int:hotel_id>/room/<str:room_number>/', views.guest_interface, name='guest_interface'),
    path('api/process_command/', views.process_guest_command, name='process_guest_command'),
    path('api/guest/<int:hotel_id>/room/<str:room_number>/check_updates/', views.check_for_new_updates, name='check_for_new_updates'),

    # Authentication URLs
    path('logout/', views.user_logout, name='logout'),
    path('login/', auth_views.LoginView.as_view(template_name='main/login.html'), name='login'), # Ensure you have a login.html

    # --- NEW STAFF/EMPLOYEE DASHBOARD URLs ---
    path('employee/login/', views.employee_login_view, name='employee_login'),
    path('employee/dashboard/', views.employee_dashboard_view, name='employee_dashboard'),
    path('api/employee/requests/<int:request_id>/complete/', views.complete_employee_request_api, name='complete_employee_request_api'),
]
