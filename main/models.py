# main/models.py

from django.db import models
from django.core.exceptions import ValidationError
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
    # Add other profile specific fields if needed

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
    room_number = models.CharField(max_length=10)
    room_type = models.CharField(max_length=50, blank=True, null=True) # e.g., "Standard", "Deluxe", "Suite"
    status = models.CharField(max_length=20, choices=ROOM_STATUS_CHOICES, default='available')
    # Add other room details like capacity, amenities etc.

    class Meta:
        unique_together = ('hotel', 'room_number') # Ensures room numbers are unique per hotel

    def __str__(self):
        return f"{self.room_number} ({self.hotel.name})"

class GuestRoomAssignment(models.Model):
    STATUS_CHOICES = [
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='guest_assignments')
    room_number = models.CharField(max_length=10) # Denormalized for easy lookup, should match a Room object
    guest_names = models.TextField(help_text="Full names of guests, separated by commas if more than one.")
    check_in_time = models.DateTimeField()
    check_out_time = models.DateTimeField()
    bill_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) # type: ignore
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) # type: ignore
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['check_in_time'] # Default ordering

    def __str__(self):
        return f"Assignment for Room {self.room_number} - {self.guest_names} ({self.hotel.name})"

    def clean(self):
        super().clean()

        # Ensure all necessary fields for the overlap check are present
        # If these are None at this stage, it means the form validation
        # (specifically the form's clean method) failed to provide them,
        # or they are not marked as required in the form.
        if not self.room_number or not self.check_in_time or not self.check_out_time or not self.hotel:
            # If any of these are missing, the overlap check cannot proceed meaningfully.
            # Django's form validation (due to `required=True` in form fields or model defaults)
            # should ideally catch this earlier. If it reaches here, it's a safeguard.
            # We raise a ValidationError here if essential fields are missing for the overlap logic.
            # If the fields are required in the model, Django will also raise an error during save()
            # if they are still None.
            # For the specific "Cannot use None as a query value" error, this check prevents it.
            # However, the form's clean method should be the primary place to enforce required fields
            # and combine date/time.
            if not self.room_number:
                raise ValidationError("Room number is required for overlap check.")
            if not self.check_in_time:
                raise ValidationError("Check-in time is required for overlap check.")
            if not self.check_out_time:
                raise ValidationError("Check-out time is required for overlap check.")
            if not self.hotel:
                raise ValidationError("Hotel is required for overlap check.")
            return # Should not be reached if ValidationErrors are raised above.

        if self.check_in_time >= self.check_out_time:
            raise ValidationError("Check-out time must be after check-in time.")

        # Check for overlapping assignments in the same room and hotel
        # Exclude the current instance itself when editing
        overlapping_assignments = GuestRoomAssignment.objects.filter(
            hotel=self.hotel,
            room_number=self.room_number,
            check_in_time__lt=self.check_out_time,
            check_out_time__gt=self.check_in_time
        )

        if self.pk: # If updating an existing instance, exclude self
            overlapping_assignments = overlapping_assignments.exclude(pk=self.pk)

        if overlapping_assignments.exists():
            raise ValidationError(
                f"Room {self.room_number} is already booked for an overlapping period."
            )



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
        ('general_inquiry', 'General Inquiry'),
        ('casual_chat', 'Casual Chat'), # New type for non-actionable messages
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
                                    help_text="Categorized type of the guest request.") # New field
    staff_notes = models.TextField(blank=True, null=True,
                                   help_text="Internal notes added by staff regarding this request.")
    timestamp = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # chat_history will store the full conversation for this request, as a list of dicts
    # e.g., [{"role": "user", "parts": [{"text": "hi"}]}, {"role": "model", "parts": [{"text": "hello"}]}]
    chat_history = models.JSONField(blank=True, null=True,
                                    help_text="Full JSON chat history for this specific request.")

    class Meta:
        ordering = ['-timestamp'] # Order by newest first

    def __str__(self):
        return f"Request from Room {self.room_number} - {self.raw_text[:50]}... ({self.get_status_display()})" # type: ignore

