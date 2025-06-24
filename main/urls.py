from django.urls import path
from . import views

# Define app_name for namespacing URLs
app_name = "main"

urlpatterns = [
    # Path for the staff dashboard
    path("dashboard/", views.staff_dashboard, name="staff_dashboard"),
    # Path for updating a guest request status
    path(
        "request/<int:request_id>/update_status/",
        views.update_request_status,
        name="update_request_status",
    ),
    # Path for the simulated guest interface
    path("guest/<str:room_number>/", views.guest_interface, name="guest_interface"),
    # API endpoint to process guest commands from the simulated device
    path(
        "api/process_command/",
        views.process_guest_command,
        name="process_guest_command_api",
    ),
]
