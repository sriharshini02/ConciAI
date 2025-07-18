from django.contrib import admin
from .models import Hotel, GuestRequest, HotelConfiguration, GuestRoomAssignment, UserProfile, Room # Added Room


# Register the Hotel model for easy management in the Django admin.
@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = ('name', 'total_rooms')
    search_fields = ('name',)


# Register the UserProfile model
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'hotel')
    list_filter = ('hotel',)
    search_fields = ('user__username', 'hotel__name')


# Register the GuestRequest model.
@admin.register(GuestRequest)
class GuestRequestAdmin(admin.ModelAdmin):
    list_display = ('room_number', 'hotel', 'raw_text', 'status', 'timestamp', 'ai_intent')
    list_filter = ('status', 'hotel', 'timestamp')
    search_fields = ('room_number', 'raw_text', 'staff_notes')
    readonly_fields = ('timestamp', 'ai_intent', 'ai_entities', 'conci_response_text', 'chat_history') 
    fieldsets = (
        (None, {
            'fields': ('hotel', 'room_number', 'raw_text', 'status', 'staff_notes')
        }),
        ('AI Analysis & Response', {
            'fields': ('ai_intent', 'ai_entities', 'conci_response_text', 'chat_history'), 
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('timestamp',),
            'classes': ('collapse',)
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
    list_display = ('hotel', 'room_number', 'guest_names', 'check_in_time', 'check_out_time', 'bill_amount', 'amount_paid', 'status', 'created_at')
    list_filter = ('hotel', 'room_number', 'check_in_time', 'check_out_time', 'status') 
    search_fields = ('room_number', 'guest_names')
    ordering = ('room_number', '-check_in_time')
    readonly_fields = ('created_at',) 
    fieldsets = (
        (None, {
            'fields': ('hotel', 'room_number', 'guest_names', 'status') 
        }),
        ('Assignment Times', {
            'fields': ('check_in_time', 'check_out_time'),
            'description': 'Specify the exact check-in and check-out date/times for this guest in this room.'
        }),
        ('Billing Details', {
            'fields': ('bill_amount', 'amount_paid'),
            'description': 'Financial information for this room assignment.'
        }),
        ('System Info', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )

# NEW: Register the Room model
@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('hotel', 'room_number', 'status')
    list_filter = ('hotel', 'status')
    search_fields = ('room_number',)
    list_editable = ('status',) # Allow editing status directly from list view
