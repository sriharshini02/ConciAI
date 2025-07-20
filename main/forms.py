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
            # Removed 'num_adults', 'num_children', 'notes' as they are not in GuestRoomAssignment model
            'status', 'total_bill_amount'
            # 'check_in_time' and 'check_out_time' are handled by clean method
        ]
        # If you have num_adults, num_children, or notes in GuestRoomAssignment model, add them back here.
        # Based on your models.py, GuestRoomAssignment has:
        # room_number (ForeignKey to Room)
        # guest_names (CharField)
        # check_in_time (DateTimeField)
        # check_out_time (DateTimeField)
        # status (CharField)
        # total_bill_amount (DecimalField)
        # created_at (DateTimeField)
        # updated_at (DateTimeField)
        # hotel (ForeignKey to Hotel)

    def __init__(self, *args, **kwargs):
        self.hotel = kwargs.pop('hotel', None)
        super().__init__(*args, **kwargs)
        
        # Add room_number_input to the form's fields order
        self.fields.insert(0, 'room_number_input', self.fields.pop('room_number_input'))

        # Set initial values for date/time fields if instance exists
        if self.instance.pk:
            self.fields['check_in_date'].initial = self.instance.check_in_time.date()
            self.fields['check_in_time_input'].initial = self.instance.check_in_time.time()
            self.fields['check_out_date'].initial = self.instance.check_out_time.date()
            self.fields['check_out_time_input'].initial = self.instance.check_out_time.time()
            # If editing an existing assignment, populate room_number_input
            if self.instance.room_number: # Check if room_number is not None
                self.fields['room_number_input'].initial = self.instance.room_number.room_number


    def clean(self):
        cleaned_data = super().clean()
        
        # Handle room_number_input: find or create Room object
        room_number_str = cleaned_data.get('room_number_input')
        if room_number_str and self.hotel:
            # Try to get the room, or create it if it doesn't exist
            room_obj, created = Room.objects.get_or_create(
                hotel=self.hotel,
                room_number=room_number_str,
                defaults={'status': 'available'} # Default status for new rooms
            )
            # Assign the Room object to the instance's room_number field
            self.instance.room_number = room_obj 
            if created:
                # This message will appear in Django's form errors but won't stop submission
                self.add_error(None, f"Room '{room_number_str}' created and assigned.")
        elif not self.hotel:
            self.add_error(None, "Cannot assign room without a hotel context.")
        else:
            self.add_error('room_number_input', "Room number is required.")

        # Combine date and time inputs into datetime objects
        check_in_date = cleaned_data.get('check_in_date')
        check_in_time_input = cleaned_data.get('check_in_time_input')
        check_out_date = cleaned_data.get('check_out_date')
        check_out_time_input = cleaned_data.get('check_out_time_input')

        if check_in_date and check_in_time_input:
            cleaned_data['check_in_time'] = timezone.make_aware(
                timezone.datetime.combine(check_in_date, check_in_time_input)
            )
        else: # Ensure these fields are always set or raise an error
            self.add_error('check_in_date', 'Check-in date is required.')
            self.add_error('check_in_time_input', 'Check-in time is required.')

        if check_out_date and check_out_time_input:
            cleaned_data['check_out_time'] = timezone.make_aware(
                timezone.datetime.combine(check_out_date, check_out_time_input)
            )
        else: # Ensure these fields are always set or raise an error
            self.add_error('check_out_date', 'Check-out date is required.')
            self.add_error('check_out_time_input', 'Check-out time is required.')
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # The room_number_input has already been processed in clean()
        # and self.instance.room_number should now hold the correct Room object.
        
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

