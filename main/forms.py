# main/forms.py

from django import forms
from .models import GuestRoomAssignment, Room, Amenity, GuestRequest, StaffMember # Import GuestRequest and StaffMember
from django.core.exceptions import ValidationError
from django.utils import timezone
import json # Import json for JSONField handling in GuestRequestForm

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

# NEW FORM: GuestRequestForm for Staff
class GuestRequestForm(forms.ModelForm):
    """
    Form for staff to view and update GuestRequest details,
    including assigning staff and adding/editing staff notes.
    """
    # Dynamically populate assigned_staff choices
    assigned_staff = forms.ModelChoiceField(
        queryset=StaffMember.objects.none(), # Initial empty queryset, will be set in __init__
        required=False,
        empty_label="Unassigned",
        label="Assign Staff"
    )

    class Meta:
        model = GuestRequest
        fields = [
            'room_number', 'raw_text', 'conci_response_text', 'status',
            'request_type', 'ai_intent', 'ai_entities', 'assigned_staff',
            'staff_notes', 'amenity_requested', 'amenity_quantity', 'bill_added' # Changed from amenity_bill_added to bill_added
        ]
        widgets = {
            # Fields that should be read-only for staff when editing a request
            'room_number': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'raw_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'readonly': 'readonly'}),
            'conci_response_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'readonly': 'readonly'}),
            'ai_intent': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'ai_entities': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'readonly': 'readonly'}),
            'amenity_requested': forms.Select(attrs={'class': 'form-control', 'disabled': 'disabled'}), # Staff shouldn't change this in edit
            'amenity_quantity': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'bill_added': forms.CheckboxInput(attrs={'class': 'form-check-input', 'disabled': 'disabled'}),
            
            # Fields that staff *can* edit
            'status': forms.Select(attrs={'class': 'form-control'}),
            'request_type': forms.Select(attrs={'class': 'form-control'}), # Staff might re-categorize
            'staff_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}), # This will be editable by staff
        }

    def __init__(self, *args, **kwargs):
        self.hotel = kwargs.pop('hotel', None)
        super().__init__(*args, **kwargs)

        if self.hotel:
            # Filter assigned_staff queryset to only show staff members of the current hotel
            self.fields['assigned_staff'].queryset = StaffMember.objects.filter(hotel=self.hotel)

        # Ensure that 'ai_entities' is displayed correctly if it's a JSONField
        # When loading an existing instance, convert JSON to string for display in textarea
        if self.instance.pk and self.instance.ai_entities:
            self.initial['ai_entities'] = json.dumps(self.instance.ai_entities, indent=2)

    def clean_ai_entities(self):
        # Handle JSONField for ai_entities
        data = self.cleaned_data['ai_entities']
        if isinstance(data, str) and data.strip(): # Check if it's a non-empty string
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                raise forms.ValidationError("Invalid JSON format for AI Entities.")
        elif not data: # If it's an empty string or None, return None
            return None
        return data

