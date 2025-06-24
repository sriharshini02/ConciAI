from django.contrib import admin
from .models import Hotel, Amenity, GuestRequest, HotelConfiguration


# Register the Hotel model for easy management in the Django admin.
@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    # Customize how Hotel objects are displayed in the list view
    list_display = ("name", "api_key", "created_at", "updated_at")
    # Add search capability by name
    search_fields = ("name",)
    # Allow filtering by API key presence (though less common)
    list_filter = ("api_key",)


# Register the Amenity model.
@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    # Display name, description, and price in the list view
    list_display = ("name", "description", "price")
    # Search by amenity name
    search_fields = ("name",)


# Register the GuestRequest model.
@admin.register(GuestRequest)
class GuestRequestAdmin(admin.ModelAdmin):
    # Display key information for each guest request
    list_display = (
        "hotel",
        "room_number",
        "timestamp",
        "ai_intent",
        "status",
        "last_updated_by_staff",
    )
    # Enable filtering by hotel, status, and AI intent
    list_filter = ("hotel", "status", "ai_intent")
    # Allow searching by room number, raw text, and staff notes
    search_fields = ("room_number", "raw_text", "staff_notes")
    # Fields to show on the detail page, making 'ai_entities' read-only
    readonly_fields = ("timestamp", "last_updated_by_staff")
    fieldsets = (
        (None, {"fields": ("hotel", "room_number", "raw_text", "conci_response_text")}),
        (
            "AI Processing Details",
            {
                "fields": ("ai_intent", "ai_entities"),
                "description": "Information extracted and processed by Conci AI.",
            },
        ),
        (
            "Request Status",
            {
                "fields": (
                    "status",
                    "staff_notes",
                    "timestamp",
                    "last_updated_by_staff",
                ),
                "description": "Current status and staff management notes.",
            },
        ),
    )


# Register the HotelConfiguration model.
@admin.register(HotelConfiguration)
class HotelConfigurationAdmin(admin.ModelAdmin):
    # Display hotel, key, and value in the list view
    list_display = ("hotel", "key", "value")
    # Filter by hotel and key
    list_filter = ("hotel", "key")
    # Search by key and value
    search_fields = ("key", "value")
