# main/forms.py

from django import forms
from .models import GuestRoomAssignment, Room, Amenity # Import Amenity model
from django.core.exceptions import ValidationError
from django.utils import timezone
class GuestRoomAssignmentForm(forms.ModelForm):
    room_number_input = forms.CharField(
        max_length=50,
        required=True,
        label="Room Number",
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
            'status',
            'total_bill_amount',
            # Note: check_in_time and check_out_time are handled by clean method
            # and should not be in 'fields' if you want to use check_in_date/time_input
        ]
        # Define the order of fields explicitly
        # Include 'room_number_input' here, and any other fields from 'fields' list
        field_order = [
            'room_number_input', # This will make it appear first
            'guest_names',
            'check_in_date',
            'check_in_time_input',
            'check_out_date',
            'check_out_time_input',
            'status',
            'total_bill_amount',
            # Add any other fields from GuestRoomAssignment model that you want to display
        ]


    def __init__(self, *args, **kwargs):
        self.hotel = kwargs.pop('hotel', None)
        super().__init__(*args, **kwargs)
        
        # Remove the problematic line:
        # self.fields.insert(0, 'room_number_input', self.fields.pop('room_number_input'))

        # Set initial values for date/time fields if instance exists
        if self.instance.pk:
            self.fields['check_in_date'].initial = self.instance.check_in_time.date()
            self.fields['check_in_time_input'].initial = self.instance.check_in_time.time()
            self.fields['check_out_date'].initial = self.instance.check_out_time.date()
            self.fields['check_out_time_input'].initial = self.instance.check_out_time.time()
            if self.instance.room_number:
                self.fields['room_number_input'].initial = self.instance.room_number.room_number


    def clean(self):
        cleaned_data = super().clean()
        
        room_number_str = cleaned_data.get('room_number_input')
        if room_number_str and self.hotel:
            room_obj, created = Room.objects.get_or_create(
                hotel=self.hotel,
                room_number=room_number_str,
                defaults={'status': 'available'}
            )
            self.instance.room_number = room_obj
            if created:
                self.add_error(None, f"Room '{room_number_str}' created and assigned.")
        elif not self.hotel:
            self.add_error(None, "Cannot assign room without a hotel context.")
        else:
            self.add_error('room_number_input', "Room number is required.")

        check_in_date = cleaned_data.get('check_in_date')
        check_in_time_input = cleaned_data.get('check_in_time_input')
        check_out_date = cleaned_data.get('check_out_date')
        check_out_time_input = cleaned_data.get('check_out_time_input')

        if check_in_date and check_in_time_input:
            cleaned_data['check_in_time'] = timezone.make_aware(
                timezone.datetime.combine(check_in_date, check_in_time_input)
            )
        else:
            self.add_error('check_in_date', 'Check-in date is required.')
            self.add_error('check_in_time_input', 'Check-in time is required.')

        if check_out_date and check_out_time_input:
            cleaned_data['check_out_time'] = timezone.make_aware(
                timezone.datetime.combine(check_out_date, check_out_time_input)
            )
        else:
            self.add_error('check_out_date', 'Check-out date is required.')
            self.add_error('check_out_time_input', 'Check-out time is required.')
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if self.hotel and not instance.hotel:
            instance.hotel = self.hotel
        
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

