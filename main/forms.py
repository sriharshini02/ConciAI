# main/forms.py

from django import forms
from .models import GuestRoomAssignment, Room, Amenity # Import Amenity model
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
            'base_bill_amount', 'amount_paid', 'status', 'hotel'
        ]
        widgets = {
            'room_number': forms.TextInput(attrs={'class': 'form-control'}),
            'guest_names': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'base_bill_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
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
            self.fields['room_number'] = forms.ChoiceField(
                choices=[(room.room_number, room.room_number) for room in Room.objects.filter(hotel=self.hotel).order_by('room_number')],
                widget=forms.Select(attrs={'class': 'form-control'}),
                required=True
            )
        else:
            self.fields['room_number'] = forms.CharField(
                widget=forms.TextInput(attrs={'class': 'form-control'}),
                required=True
            )

        if self.hotel:
            self.fields['hotel'].widget = forms.HiddenInput()
            self.fields['hotel'].initial = self.hotel.id

    def clean(self):
        cleaned_data = super().clean()
        check_in_date = cleaned_data.get('check_in_date')
        check_in_time_input = cleaned_data.get('check_in_time_input')
        check_out_date = cleaned_data.get('check_out_date')
        check_out_time_input = cleaned_data.get('check_out_time_input')
        
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

        if 'check_in_time' in cleaned_data and 'check_out_time' in cleaned_data:
            if cleaned_data['check_out_time'] <= cleaned_data['check_in_time']:
                raise ValidationError("Check-out time must be after check-in time.")
        
        room_number = cleaned_data.get('room_number')
        if self.hotel and room_number:
            if not Room.objects.filter(hotel=self.hotel, room_number=room_number).exists():
                raise ValidationError(f"Room {room_number} does not exist for this hotel.")

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

