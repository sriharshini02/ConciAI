# main/forms.py

from django import forms
from .models import GuestRoomAssignment, Room, Amenity # Import Amenity model
from django.core.exceptions import ValidationError
from django.utils import timezone

class GuestRoomAssignmentForm(forms.ModelForm):
    # Change room_number to a CharField for text input
    # We will handle the conversion to a Room object in clean_room_number
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
            'guest_names', 'num_adults', 'num_children',
            'check_in_time', 'check_out_time', 'status', 'notes', 'total_bill_amount'
        ]
        # Exclude 'room_number' from Meta.fields because we're handling it manually
        # and will assign the Room object in the clean method.

    def __init__(self, *args, **kwargs):
        self.hotel = kwargs.pop('hotel', None)
        super().__init__(*args, **kwargs)
        
        # Add room_number_input to the form's fields order
        # This ensures it appears at the top, or where you want it.
        # If you want it at the very top, you can adjust the order.
        self.fields.insert(0, 'room_number_input', self.fields.pop('room_number_input')) # type: ignore

        # Set initial values for date/time fields if instance exists
        if self.instance.pk:
            self.fields['check_in_date'].initial = self.instance.check_in_time.date()
            self.fields['check_in_time_input'].initial = self.instance.check_in_time.time()
            self.fields['check_out_date'].initial = self.instance.check_out_time.date()
            self.fields['check_out_time_input'].initial = self.instance.check_out_time.time()
            # If editing an existing assignment, populate room_number_input
            self.fields['room_number_input'].initial = self.instance.room_number.room_number


    def clean(self):
        cleaned_data = super().clean()
        
        # Handle room_number_input: find or create Room object
        room_number_str = cleaned_data.get('room_number_input')
        if room_number_str and self.hotel:
            # Try to get the room, or create it if it doesn't exist
            # defaults={'status': 'available'} sets the status for newly created rooms
            room_obj, created = Room.objects.get_or_create(
                hotel=self.hotel,
                room_number=room_number_str,
                defaults={'status': 'available'} # Default status for new rooms
            )
            if created:
                self.instance.room_number = room_obj # Assign to instance for save
                self.add_error(None, f"Room '{room_number_str}' created and assigned.")
            else:
                self.instance.room_number = room_obj # Assign to instance for save
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
        if check_out_date and check_out_time_input:
            cleaned_data['check_out_time'] = timezone.make_aware(
                timezone.datetime.combine(check_out_date, check_out_time_input)
            )
        
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

