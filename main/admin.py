# main/admin.py

from django.contrib import admin
from .models import  Hotel, UserProfile, HotelConfiguration, Room, GuestRoomAssignment, GuestRequest, Amenity # Import Amenity

# Register your models here.


@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = ('name',  'total_rooms')
    search_fields = ('name', 'address')

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'hotel')
    list_filter = ('hotel',)
    search_fields = ('user__username', 'hotel__name')

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('room_number', 'hotel', 'room_type', 'status')
    list_filter = ('hotel', 'status', 'room_type')
    search_fields = ('room_number', 'hotel__name')
    list_editable = ('status',) # Allow editing status directly from list view

@admin.register(GuestRoomAssignment)
class GuestRoomAssignmentAdmin(admin.ModelAdmin):
    # Corrected list_display to use base_bill_amount and total_bill_amount
    list_display = ('room_number', 'guest_names', 'check_in_time', 'check_out_time',
                    'base_bill_amount', 'total_bill_amount', 'amount_paid', 'status', 'created_at') # Updated fields
    list_filter = ('hotel', 'status', 'check_in_time', 'check_out_time')
    search_fields = ('room_number', 'guest_names', 'hotel__name')
    date_hierarchy = 'check_in_time'
    ordering = ('-check_in_time',)
    # Add fields to fieldsets for better organization in detail view
    fieldsets = (
        (None, {
            'fields': ('hotel', 'room_number', 'guest_names', 'status')
        }),
        ('Booking Details', {
            'fields': ('check_in_time', 'check_out_time')
        }),
        ('Financials', {
            'fields': ('base_bill_amount', 'total_bill_amount', 'amount_paid') # Updated fields
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',) # Collapse this section by default
        }),
    )
    readonly_fields = ('created_at', 'updated_at', 'total_bill_amount') # total_bill_amount is calculated

@admin.register(GuestRequest)
class GuestRequestAdmin(admin.ModelAdmin):
    list_display = ('room_number', 'raw_text', 'request_type', 'status', 'timestamp',
                    'amenity_requested', 'amenity_quantity', 'bill_added') # Added amenity fields
    list_filter = ('hotel', 'status', 'request_type', 'timestamp', 'amenity_requested') # Added request_type and amenity_requested to filter
    search_fields = ('room_number', 'raw_text', 'staff_notes')
    date_hierarchy = 'timestamp'
    ordering = ('-timestamp',)
    # Add fields to fieldsets for better organization in detail view
    fieldsets = (
        (None, {
            'fields': ('hotel', 'room_number', 'raw_text', 'status', 'request_type', 'staff_notes') # Added request_type
        }),
        ('AI Analysis', {
            'fields': ('ai_intent', 'ai_entities', 'conci_response_text'),
            'classes': ('collapse',)
        }),
        ('Amenity Details', { # New fieldset for amenity details
            'fields': ('amenity_requested', 'amenity_quantity', 'bill_added'),
            'classes': ('collapse',)
        }),
        ('Chat History', {
            'fields': ('chat_history',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('timestamp', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('timestamp', 'updated_at', 'ai_entities', 'chat_history') # ai_entities and chat_history are JSONFields

@admin.register(Amenity) # Register the new Amenity model
class AmenityAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'is_available', 'created_at')
    list_filter = ('is_available',)
    search_fields = ('name', 'description')
    ordering = ('name',)

@admin.register(HotelConfiguration)
class HotelConfigurationAdmin(admin.ModelAdmin):
    list_display = ('hotel', 'key', 'value')
    list_filter = ('hotel', 'key')
    search_fields = ('key', 'value')
