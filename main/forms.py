# main/forms.py

from django import forms
from .models import GuestRoomAssignment, Room # Import Room model
from django.core.exceptions import ValidationError
from django.utils import timezone

class GuestRoomAssignmentForm(forms.ModelForm):
    # Add separate date and time fields for better user input
    check_in_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}), required=True)
    check_in_time_input = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}), required=True)
    check_out_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}), required=True)
    check_out_time_input = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}), required=True)

    class Meta:
        model = GuestRoomAssignment
        fields = [
            'room_number', 'guest_names', 'check_in_time', 'check_out_time',
            'base_bill_amount', 'amount_paid', 'status', 'hotel' # Corrected: 'bill_amount' changed to 'base_bill_amount'
        ]
        # Exclude check_in_time and check_out_time from default widget rendering
        # as we are handling them with separate date/time inputs
        widgets = {
            'room_number': forms.TextInput(attrs={'class': 'form-control'}),
            'guest_names': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'base_bill_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}), # Updated widget name
            'amount_paid': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'hotel': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.hotel = kwargs.pop('hotel', None) # Pop the hotel instance
        super().__init__(*args, **kwargs)
        
        # Set initial values for date/time fields if instance exists
        if self.instance.pk:
            if self.instance.check_in_time:
                self.fields['check_in_date'].initial = self.instance.check_in_time.date()
                self.fields['check_in_time_input'].initial = self.instance.check_in_time.time()
            if self.instance.check_out_time:
                self.fields['check_out_date'].initial = self.instance.check_out_time.date()
                self.fields['check_out_time_input'].initial = self.instance.check_out_time.time()
        
        # Filter room_number choices based on the hotel if provided
        if self.hotel:
            self.fields['room_number'].queryset = Room.objects.filter(hotel=self.hotel).values_list('room_number', flat=True).distinct() # type: ignore
            # If you want a dropdown of existing room numbers, you can use:
            self.fields['room_number'] = forms.ChoiceField(
                choices=[(room.room_number, room.room_number) for room in Room.objects.filter(hotel=self.hotel).order_by('room_number')],
                widget=forms.Select(attrs={'class': 'form-control'}),
                required=True
            )
        else:
            # If no hotel is provided (e.g., in admin for superuser), show all rooms or handle as needed
            self.fields['room_number'] = forms.CharField(
                widget=forms.TextInput(attrs={'class': 'form-control'}),
                required=True
            )

        # Hide the 'hotel' field in the form if it's already set or not needed for direct input
        if self.hotel:
            self.fields['hotel'].widget = forms.HiddenInput()
            self.fields['hotel'].initial = self.hotel.id # Set initial value for hidden input

    def clean(self):
        cleaned_data = super().clean()
        check_in_date = cleaned_data.get('check_in_date')
        check_in_time_input = cleaned_data.get('check_in_time_input')
        check_out_date = cleaned_data.get('check_out_date')
        check_out_time_input = cleaned_data.get('check_out_time_input')
        
        # Combine date and time fields into full datetime objects
        if check_in_date and check_in_time_input:
            cleaned_data['check_in_time'] = timezone.make_aware(
                timezone.datetime.combine(check_in_date, check_in_time_input),
                timezone.get_current_timezone()
            )
        if check_out_date and check_out_time_input:
            cleaned_data['check_out_time'] = timezone.make_aware(
                timezone.datetime.combine(check_out_date, check_out_time_input),
                timezone.get_current_timezone()
            )

        # Validate check-in/check-out times
        if 'check_in_time' in cleaned_data and 'check_out_time' in cleaned_data:
            if cleaned_data['check_out_time'] <= cleaned_data['check_in_time']:
                raise ValidationError("Check-out time must be after check-in time.")
        
        # Validate room number exists for the hotel
        room_number = cleaned_data.get('room_number')
        if self.hotel and room_number:
            if not Room.objects.filter(hotel=self.hotel, room_number=room_number).exists():
                raise ValidationError(f"Room {room_number} does not exist for this hotel.")

        return cleaned_data

    # Override save to handle the combined datetime fields
    def save(self, commit=True):
        instance = super().save(commit=False)
        # The combined check_in_time and check_out_time are already in cleaned_data
        # and assigned to instance by the parent clean method.
        
        # Ensure hotel is set if it was passed in __init__
        if self.hotel and not instance.hotel:
            instance.hotel = self.hotel

        if commit:
            instance.save()
        return instance

