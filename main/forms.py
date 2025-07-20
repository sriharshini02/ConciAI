# main/forms.py

from django import forms
from .models import GuestRoomAssignment, Room, Amenity # Import Amenity model
from django.core.exceptions import ValidationError
from django.utils import timezone


class GuestRoomAssignmentForm(forms.ModelForm):
    # Change room_number to a CharField for text input
    room_number_input = forms.CharField(
        max_length=50, 
        required=True,
        label="Room Number", # Custom label for clarity in the form
        widget=forms.TextInput(attrs={'placeholder': 'e.g., 101, 205A'})
    )

    check_in_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=True)
    check_in_time_input = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}), required=True)
    check_out_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=True)
    check_out_time_input = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}), required=True)

    class Meta:
        model = GuestRoomAssignment
        fields = [
            'guest_names',
            'check_in_time',  # <--- CRITICAL: Include these fields
            'check_out_time', # <--- CRITICAL: Include these fields
            'status', 
            'total_bill_amount',
            'amount_paid', 
        ]
        # It's good practice to list all fields explicitly, especially if you're manipulating them
        # in clean() or __init__
        field_order = [
            'room_number_input',
            'guest_names',
            'check_in_date',
            'check_in_time_input',
            'check_out_date',
            'check_out_time_input',
            'total_bill_amount',
            'amount_paid',       
            'status',
        ]
        widgets = {
            'guest_names': forms.TextInput(attrs={'class': 'form-control'}),
            # check_in_time and check_out_time are handled by custom fields, no widget needed here
            'status': forms.Select(attrs={'class': 'form-control'}),
            'total_bill_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'amount_paid': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}), 
        }


    def __init__(self, *args, **kwargs):
        self.hotel = kwargs.pop('hotel', None) # Pop hotel from kwargs
        super().__init__(*args, **kwargs)
        
        # Set initial values for date/time fields if instance exists
        if self.instance.pk:
            # Ensure instance.check_in_time and check_out_time are not None before accessing .date() or .time()
            if self.instance.check_in_time:
                self.fields['check_in_date'].initial = self.instance.check_in_time.date()
                self.fields['check_in_time_input'].initial = self.instance.check_in_time.time()
            if self.instance.check_out_time:
                self.fields['check_out_date'].initial = self.instance.check_out_time.date()
                self.fields['check_out_time_input'].initial = self.instance.check_out_time.time()
            if self.instance.room_number:
                self.fields['room_number_input'].initial = self.instance.room_number.room_number
            self.fields['amount_paid'].initial = self.instance.amount_paid


    def clean(self):
        cleaned_data = super().clean()
        
        room_number_str = cleaned_data.get('room_number_input')
        
        # Ensure hotel context is available
        if not self.hotel:
            raise ValidationError("Hotel context is missing for guest assignment form.")

        if room_number_str:
            try:
                room_obj = Room.objects.get(hotel=self.hotel, room_number=room_number_str)
            except Room.DoesNotExist:
                # If room doesn't exist for this hotel, create it
                room_obj = Room.objects.create(
                    hotel=self.hotel,
                    room_number=room_number_str,
                    status='available' # Default status for new rooms
                )
                # Add a non-field error to inform the user that a new room was created
                self.add_error(None, f"Room '{room_number_str}' created and assigned.")
            self.instance.room_number = room_obj # Assign the Room object to the instance
        else:
            self.add_error('room_number_input', "Room number is required.")

        check_in_date = cleaned_data.get('check_in_date')
        check_in_time_input = cleaned_data.get('check_in_time_input')
        check_out_date = cleaned_data.get('check_out_date')
        check_out_time_input = cleaned_data.get('check_out_time_input')

        # Combine date and time inputs into DateTimeField for the instance
        if check_in_date and check_in_time_input:
            self.instance.check_in_time = timezone.make_aware(
                timezone.datetime.combine(check_in_date, check_in_time_input)
            )
        else:
            self.add_error('check_in_date', 'Check-in date is required.')
            self.add_error('check_in_time_input', 'Check-in time is required.')

        if check_out_date and check_out_time_input:
            self.instance.check_out_time = timezone.make_aware(
                timezone.datetime.combine(check_out_date, check_out_time_input)
            )
        else:
            self.add_error('check_out_date', 'Check-out date is required.')
            self.add_error('check_out_time_input', 'Check-out time is required.')
        
        # Ensure amount_paid is handled (if it's not provided, default to 0.00)
        amount_paid = cleaned_data.get('amount_paid')
        if amount_paid is None:
            cleaned_data['amount_paid'] = 0.00
        # Assign to instance if not already handled by ModelForm
        self.instance.amount_paid = cleaned_data['amount_paid']


        # Perform cross-field validation after individual fields are clean
        if hasattr(self.instance, 'check_in_time') and hasattr(self.instance, 'check_out_time') and \
           self.instance.check_in_time and self.instance.check_out_time: # Ensure they are not None
            if self.instance.check_out_time <= self.instance.check_in_time:
                self.add_error('check_out_time', 'Check-out time must be after check-in time.')
            
            # Check for overlapping assignments for the same room
            if self.instance.room_number: # Only check if room is assigned
                overlapping_assignments = GuestRoomAssignment.objects.filter(
                    room_number=self.instance.room_number,
                    check_in_time__lt=self.instance.check_out_time,
                    check_out_time__gt=self.instance.check_in_time,
                ).exclude(pk=self.instance.pk) # Exclude self for updates

                if overlapping_assignments.exists():
                    self.add_error('room_number_input', 'This room is already assigned for the selected dates/times.')


        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Ensure 'hotel' is set on the instance before saving.
        if self.hotel and not instance.hotel_id: 
            instance.hotel = self.hotel
        
        # The room_number, check_in_time, check_out_time, and amount_paid
        # are now assigned to self.instance in clean()
        # They will be saved when instance.save() is called.

        if commit:
            instance.save()
        return instance




# New Amenity Form
class AmenityForm(forms.ModelForm):
    class Meta:
        model = Amenity
        fields = ['name', 'description', 'price', 'is_available']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
    
    def clean_name(self):
        name = self.cleaned_data['name']
        # Ensure amenity names are unique (case-insensitive)
        if self.instance.pk: # If updating an existing amenity
            if Amenity.objects.filter(name__iexact=name).exclude(pk=self.instance.pk).exists():
                raise ValidationError("An amenity with this name already exists.")
        else: # If creating a new amenity
            if Amenity.objects.filter(name__iexact=name).exists():
                raise ValidationError("An amenity with this name already exists.")
        return name

