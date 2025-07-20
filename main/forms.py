# main/forms.py

from django import forms
from .models import GuestRoomAssignment, Room, Amenity # Import Amenity model
from django.core.exceptions import ValidationError
from django.utils import timezone

class GuestRoomAssignmentForm(forms.ModelForm):
    # ... (your existing room_number_input, check_in_date, check_in_time_input, check_out_date, check_out_time_input fields) ...
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
            'amount_paid', 
        ]
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
            'status': forms.Select(attrs={'class': 'form-control'}),
            'total_bill_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'amount_paid': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}), 
        }


    def __init__(self, *args, **kwargs):
        self.hotel = kwargs.pop('hotel', None)
        super().__init__(*args, **kwargs)
        
        if self.instance.pk:
            if self.instance.check_in_time:
                self.fields['check_in_date'].initial = self.instance.check_in_time.date()
                self.fields['check_in_time_input'].initial = self.instance.check_in_time.time()
            if self.instance.check_out_time:
                self.fields['check_out_date'].initial = self.instance.check_out_time.date()
                self.fields['check_out_time_input'].initial = self.instance.check_out_time.time()
            
            if self.instance.room_number: 
                self.fields['room_number_input'].initial = self.instance.room_number
            else:
                self.fields['room_number_input'].initial = ''

            self.fields['amount_paid'].initial = self.instance.amount_paid


    def clean(self):
        cleaned_data = super().clean()
        
        room_number_str = cleaned_data.get('room_number_input')
        
        # Initialize a flag to indicate if a new room was created
        self._new_room_created = False # <--- NEW: Initialize flag

        if not self.hotel:
            raise ValidationError("Hotel context is missing for guest assignment form.")

        if room_number_str:
            try:
                room_obj = Room.objects.get(hotel=self.hotel, room_number=room_number_str)
            except Room.DoesNotExist:
                room_obj = Room.objects.create(
                    hotel=self.hotel,
                    room_number=room_number_str,
                    status='available'
                )
                self._new_room_created = True # <--- NEW: Set the flag instead of adding an error
            
            self.instance.room_number = room_obj.room_number
        else:
            self.add_error('room_number_input', "Room number is required.")

        check_in_date = cleaned_data.get('check_in_date')
        check_in_time_input = cleaned_data.get('check_in_time_input')
        check_out_date = cleaned_data.get('check_out_date')
        check_out_time_input = cleaned_data.get('check_out_time_input')

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
        
        self.instance.amount_paid = cleaned_data.get('amount_paid', 0.00)


        if hasattr(self.instance, 'check_in_time') and hasattr(self.instance, 'check_out_time') and \
           self.instance.check_in_time and self.instance.check_out_time:
            if self.instance.check_out_time <= self.instance.check_in_time:
                self.add_error('check_out_time', 'Check-out time must be after check-in time.')
            
            if self.instance.room_number:
                overlapping_assignments = GuestRoomAssignment.objects.filter(
                    hotel=self.hotel,
                    room_number=self.instance.room_number,
                    check_in_time__lt=self.instance.check_out_time,
                    check_out_time__gt=self.instance.check_in_time,
                ).exclude(pk=self.instance.pk)

                if overlapping_assignments.exists():
                    self.add_error('room_number_input', 'This room is already assigned for the selected dates/times.')

        return cleaned_data

    # Add a property to easily check if a new room was created
    @property
    def new_room_created(self): # <--- NEW: Property to access the flag
        return getattr(self, '_new_room_created', False)

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if self.hotel and not instance.hotel_id: 
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

