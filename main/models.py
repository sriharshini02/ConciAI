from django.db import models
from django.conf import settings # Import settings
from django.utils import timezone
import json 
from django.core.exceptions import ValidationError

# Create your models here.

class Hotel(models.Model):
    name = models.CharField(max_length=255, unique=True)
    total_rooms = models.IntegerField(default=0)

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

# NEW: Room Model
class Room(models.Model):
    ROOM_STATUS_CHOICES = [
        ('available', 'Available'),
        ('occupied', 'Occupied'), # Can be occupied by a GuestRoomAssignment
        ('cleaning', 'Cleaning'),
        ('maintenance', 'Maintenance'),
        ('out_of_service', 'Out of Service'),
    ]
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='rooms')
    room_number = models.CharField(max_length=10)
    status = models.CharField(max_length=20, choices=ROOM_STATUS_CHOICES, default='available')
    # Add other room-specific fields like room_type, capacity, etc.

    class Meta:
        unique_together = ('hotel', 'room_number') # Each room number is unique per hotel
        ordering = ['room_number']

    def __str__(self):
        return f"{self.hotel.name} - Room {self.room_number} ({self.get_status_display()})" # type: ignore


class GuestRoomAssignment(models.Model):
    STATUS_CHOICES = [
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]

    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='guest_assignments')
    room_number = models.CharField(max_length=10) # This should ideally be a ForeignKey to Room, but keeping as CharField for now to minimize changes
    guest_names = models.TextField(blank=True, null=True)
    check_in_time = models.DateTimeField()
    check_out_time = models.DateTimeField()
    bill_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) # type: ignore
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) # type: ignore
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')

    class Meta:
        ordering = ['-check_in_time']

    def clean(self):
        if self.check_in_time and self.check_out_time and self.check_out_time <= self.check_in_time:
            raise ValidationError('Check-out time must be strictly after check-in time.')
        
        if self.bill_amount is not None and self.amount_paid is not None:
            if self.amount_paid > self.bill_amount:
                raise ValidationError('Amount paid cannot be greater than the total bill amount.')

        overlapping_assignments = GuestRoomAssignment.objects.filter(
            hotel=self.hotel,
            room_number=self.room_number,
            check_in_time__lt=self.check_out_time,
            check_out_time__gt=self.check_in_time
        ).exclude(status__in=['cancelled', 'checked_out', 'no_show'])

        if self.pk:
            overlapping_assignments = overlapping_assignments.exclude(pk=self.pk)

        if overlapping_assignments.exists():
            raise ValidationError(f'Room {self.room_number} is already booked for the specified period.')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Room {self.room_number} - {self.guest_names} ({self.check_in_time.strftime('%Y-%m-%d')} to {self.check_out_time.strftime('%Y-%m-%d')}) - {self.get_status_display()}" # type: ignore


class GuestRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='guest_requests')
    room_number = models.CharField(max_length=10)
    raw_text = models.TextField()
    ai_intent = models.CharField(max_length=100, blank=True, null=True)
    ai_entities = models.JSONField(default=dict, blank=True, null=True)
    conci_response_text = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    timestamp = models.DateTimeField(default=timezone.now)
    staff_notes = models.TextField(blank=True, null=True)
    chat_history = models.JSONField(default=list, blank=True, null=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Room {self.room_number} - {self.raw_text[:50]}... ({self.get_status_display()})" # type: ignore
