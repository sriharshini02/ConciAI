# main/models.py
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
import json
from django.conf import settings 

class Hotel(models.Model):
    name = models.CharField(max_length=255)
    total_rooms = models.IntegerField(default=0)
    # Add other hotel-specific fields as needed

    def __str__(self):
        return self.name

class UserProfile(models.Model):
    # Use settings.AUTH_USER_MODEL to correctly reference the user model
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
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE)
    room_number = models.CharField(max_length=10)
    # Statuses for room availability/readiness
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('cleaning', 'Cleaning'),
        ('maintenance', 'Maintenance'),
        ('out_of_service', 'Out of Service'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')

    class Meta:
        unique_together = ('hotel', 'room_number')

    def __str__(self):
        return f"{self.room_number} ({self.hotel.name})"

class GuestRoomAssignment(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE)
    room_number = models.CharField(max_length=10) # Assuming this is a CharField, not ForeignKey to Room
    guest_names = models.TextField()
    check_in_time = models.DateTimeField() # These are required fields by default
    check_out_time = models.DateTimeField() # These are required fields by default
    bill_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)# type: ignore
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) # type: ignore
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    STATUS_CHOICES = [
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')

    class Meta:
        ordering = ['-check_in_time'] # Order by check-in time descending

    def __str__(self):
        return f"{self.guest_names} in Room {self.room_number} ({self.hotel.name})"

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
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE)
    room_number = models.CharField(max_length=10)
    raw_text = models.TextField()
    ai_intent = models.CharField(max_length=255, null=True, blank=True)
    ai_entities = models.JSONField(null=True, blank=True) # Stores structured data from AI
    conci_response_text = models.TextField(null=True, blank=True) # Conci's last response to this request
    timestamp = models.DateTimeField(auto_now_add=True)
    staff_notes = models.TextField(blank=True, null=True)

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Stores the full chat history for this specific request
    chat_history = models.JSONField(null=True, blank=True, default=list) 

    class Meta:
        ordering = ['-timestamp'] # Order by most recent first

    def __str__(self):
        return f"Request from Room {self.room_number}: {self.raw_text[:50]}..."
