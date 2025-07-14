from django.db import models
from django.utils import timezone
import json
from django.contrib.auth.models import User # Import Django's built-in User model

class Hotel(models.Model):
    name = models.CharField(max_length=255, unique=True)
    api_key = models.CharField(max_length=255, blank=True, null=True, help_text="Optional API key for external integrations if needed per hotel.")
    
    # NEW: Add total_rooms field to Hotel model
    total_rooms = models.PositiveIntegerField(default=100, help_text="Total number of rooms in this hotel.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

# NEW: UserProfile model to link Django's User to a Hotel
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='staff_profiles', blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.username}'s profile for {self.hotel.name if self.hotel else 'No Hotel'}"

class HotelConfiguration(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='configurations')
    key = models.CharField(max_length=255, help_text="e.g., 'checkout_time', 'wifi_password'")
    value = models.TextField(help_text="The configuration value.")

    class Meta:
        unique_together = ('hotel', 'key')
        verbose_name = "Hotel Configuration"
        verbose_name_plural = "Hotel Configurations"

    def __str__(self):
        return f"{self.hotel.name} - {self.key}: {self.value}"

class Amenity(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return self.name

class GuestRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='guest_requests')
    room_number = models.CharField(max_length=10) # e.g., "101", "suite_A"
    timestamp = models.DateTimeField(default=timezone.now)
    raw_text = models.TextField(help_text="The original raw text request(s) from the guest.")
    ai_intent = models.CharField(max_length=100, blank=True, null=True, help_text="AI-detected intent (e.g., request_amenity, get_info)")
    ai_entities = models.JSONField(default=dict, blank=True, null=True, help_text="AI-extracted entities (e.g., {'item': 'towel', 'quantity': 2})")
    conci_response_text = models.TextField(blank=True, null=True, help_text="Conci's full conversational response to the guest.")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    staff_notes = models.TextField(blank=True, null=True, help_text="Notes added by staff regarding this request.")
    last_updated_by_staff = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-timestamp'] # Default ordering for requests

    def __str__(self):
        return f"Room {self.room_number}: {self.ai_intent or 'N/A'} ({self.status}) - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

    def save(self, *args, **kwargs):
        # Update last_updated_by_staff whenever the status is changed by staff (or other means)
        if self.pk: # Only on update, not on creation
            original = GuestRequest.objects.get(pk=self.pk)
            if original.status != self.status:
                self.last_updated_by_staff = timezone.now()
        super().save(*args, **kwargs)

class GuestRoomAssignment(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='room_assignments')
    room_number = models.CharField(max_length=10, help_text="The physical room number or identifier.")
    
    guest_names = models.TextField(blank=True, null=True, help_text="Names of all guests assigned to this room (e.g., comma-separated).") 
    
    check_in_time = models.DateTimeField(help_text="Actual or scheduled check-in date and time.")
    check_out_time = models.DateTimeField(help_text="Actual or scheduled check-out date and time.")
    
    bill_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, # type: ignore
        help_text="Total bill amount for this assignment."
    )
    amount_paid = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, # type: ignore
        help_text="Amount paid by the guest so far."
    )

    class Meta:
        unique_together = ('hotel', 'room_number', 'check_in_time')
        ordering = ['-check_in_time']

    def __str__(self):
        return (f"{self.hotel.name} - Room {self.room_number} ({self.guest_names or 'No Guests'}) "
                f"from {self.check_in_time.strftime('%Y-%m-%d %H:%M')} to {self.check_out_time.strftime('%Y-%m-%d %H:%M')}")

