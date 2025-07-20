# main/models.py
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.conf import settings 
import json # Import json for JSONField handling

class Hotel(models.Model):
    name = models.CharField(max_length=255)
    total_rooms = models.IntegerField(default=0)
    # Add other hotel-specific settings as needed

    def __str__(self):
        return self.name

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    hotel = models.ForeignKey(Hotel, on_delete=models.SET_NULL, null=True, blank=True)
    def __str__(self):
        return f"{self.user.username}'s profile ({self.hotel.name if self.hotel else 'No Hotel'})"
class HotelConfiguration(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='configurations')
    key = models.CharField(max_length=255) # e.g., 'wifi_password', 'checkout_time'
    value = models.TextField()

    class Meta:
        unique_together = ('hotel', 'key')

    def __str__(self):
        return f"{self.hotel.name} - {self.key}: {self.value[:50]}..."



class Room(models.Model):
    ROOM_STATUS_CHOICES = [
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('cleaning', 'Cleaning Required'),
        ('maintenance', 'Under Maintenance'),
        ('out_of_service', 'Out of Service'),
    ]
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='rooms')
    room_number = models.CharField(max_length=1000)
    room_type = models.CharField(max_length=50, blank=True, null=True) # e.g., "Standard", "Deluxe", "Suite"
    status = models.CharField(max_length=20, choices=ROOM_STATUS_CHOICES, default='available')
    # Add other room details like capacity, amenities etc.

    class Meta:
        unique_together = ('hotel', 'room_number') # Ensures room numbers are unique per hotel

    def __str__(self):
        return f"{self.room_number} ({self.hotel.name})"

# New Amenity Model
class Amenity(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Cost per unit of this amenity.")
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Amenities" # Correct pluralization in admin
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (${self.price:.2f})"

class GuestRoomAssignment(models.Model):
    STATUS_CHOICES = [
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='guest_assignments')
    room_number = models.CharField(max_length=1000) # Denormalized for easy lookup, should match a Room object
    guest_names = models.TextField(help_text="Full names of guests, separated by commas if more than one.")
    check_in_time = models.DateTimeField()
    check_out_time = models.DateTimeField()
    # Renamed bill_amount to base_bill_amount for clarity, and added total_bill_amount
    base_bill_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00,  # type: ignore
                                           help_text="Base room charges for the stay.")
    total_bill_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00,  # type: ignore
                                            help_text="Total bill including room charges and amenities.")
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # type: ignore
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['check_in_time'] # Default ordering

    def __str__(self):
        return f"Assignment for Room {self.room_number} - {self.guest_names} ({self.hotel.name})"

    # Override save to ensure total_bill_amount is at least base_bill_amount initially
    def save(self, *args, **kwargs):
        if self.pk is None: # Only on creation
            self.total_bill_amount = self.base_bill_amount
        super().save(*args, **kwargs)


class GuestRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    REQUEST_TYPE_CHOICES = [
        ('maintenance', 'Maintenance'),
        ('repairs', 'Repairs'),
        ('housekeeping', 'Housekeeping'),
        ('room_service', 'Room Service'),
        ('concierge', 'Concierge'),
        ('amenity_request', 'Amenity Request'), # New type for amenities
        ('general_inquiry', 'General Inquiry'),
        ('casual_chat', 'Casual Chat'), # For non-actionable messages
    ]

    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='guest_requests')
    room_number = models.CharField(max_length=10) # Denormalized
    raw_text = models.TextField(help_text="The original raw text message from the guest.")
    ai_intent = models.CharField(max_length=255, blank=True, null=True,
                                 help_text="AI's determined intent of the request.")
    ai_entities = models.JSONField(blank=True, null=True,
                                   help_text="JSON representation of entities extracted by AI.")
    conci_response_text = models.TextField(blank=True, null=True,
                                           help_text="The response sent by Conci to the guest.")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    request_type = models.CharField(max_length=50, choices=REQUEST_TYPE_CHOICES, default='general_inquiry',
                                    help_text="Categorized type of the guest request.")
    staff_notes = models.TextField(blank=True, null=True,
                                   help_text="Internal notes added by staff regarding this request.")
    timestamp = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # New fields for amenity requests
    amenity_requested = models.ForeignKey(Amenity, on_delete=models.SET_NULL, null=True, blank=True,
                                          help_text="The amenity requested, if applicable.")
    amenity_quantity = models.IntegerField(default=1, help_text="Quantity of the amenity requested.")
    bill_added = models.BooleanField(default=False,
                                     help_text="True if the amenity cost has been added to guest's bill.")

    chat_history = models.JSONField(blank=True, null=True,
                                    help_text="Full JSON chat history for this specific request.")

    class Meta:
        ordering = ['-timestamp'] # Order by newest first

    def __str__(self):
        return f"Request from Room {self.room_number} - {self.raw_text[:50]}... ({self.get_status_display()})" # type: ignore

