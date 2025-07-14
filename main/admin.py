from django.contrib import admin
from .models import Hotel, Amenity, GuestRequest, HotelConfiguration, GuestRoomAssignment, UserProfile # Import UserProfile

# Register the Hotel model for easy management in the Django admin.
@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = ('name', 'total_rooms', 'api_key', 'created_at', 'updated_at') # Added total_rooms
    search_fields = ('name',)
    list_filter = ('api_key',)
    fieldsets = ( # Added fieldsets to organize fields, including total_rooms
        (None, {
            'fields': ('name', 'total_rooms', 'api_key')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',), # Makes this section collapsible
        }),
    )
    readonly_fields = ('created_at', 'updated_at')


# NEW: Register the UserProfile model
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'hotel')
    list_filter = ('hotel',)
    search_fields = ('user__username', 'hotel__name')

# Register the Amenity model.
@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'price')
    search_fields = ('name',)

# Register the GuestRequest model.
@admin.register(GuestRequest)
class GuestRequestAdmin(admin.ModelAdmin):
    list_display = ('hotel', 'room_number', 'timestamp', 'ai_intent', 'status', 'last_updated_by_staff')
    list_filter = ('hotel', 'status', 'ai_intent')
    search_fields = ('room_number', 'raw_text', 'staff_notes')
    readonly_fields = ('timestamp', 'last_updated_by_staff')
    fieldsets = (
        (None, {
            'fields': ('hotel', 'room_number', 'raw_text', 'conci_response_text')
        }),
        ('AI Processing Details', {
            'fields': ('ai_intent', 'ai_entities'),
            'description': 'Information extracted and processed by Conci AI.'
        }),
        ('Request Status', {
            'fields': ('status', 'staff_notes', 'timestamp', 'last_updated_by_staff'),
            'description': 'Current status and staff management notes.'
        }),
    )

# Register the HotelConfiguration model.
@admin.register(HotelConfiguration)
class HotelConfigurationAdmin(admin.ModelAdmin):
    list_display = ('hotel', 'key', 'value')
    list_filter = ('hotel', 'key')
    search_fields = ('key', 'value')

# Register the GuestRoomAssignment model with new fields
@admin.register(GuestRoomAssignment)
class GuestRoomAssignmentAdmin(admin.ModelAdmin):
    list_display = ('hotel', 'room_number', 'guest_names', 'check_in_time', 'check_out_time', 'bill_amount', 'amount_paid')
    list_filter = ('hotel', 'room_number', 'check_in_time', 'check_out_time')
    search_fields = ('room_number', 'guest_names')
    ordering = ('room_number', '-check_in_time')
    fieldsets = (
        (None, {
            'fields': ('hotel', 'room_number', 'guest_names')
        }),
        ('Assignment Times', {
            'fields': ('check_in_time', 'check_out_time'),
            'description': 'Specify the exact check-in and check-out date/times for this guest in this room.'
        }),
        ('Billing Details', {
            'fields': ('bill_amount', 'amount_paid'),
            'description': 'Financial information for this room assignment.'
        }),
    )

