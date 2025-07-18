# main/forms.py
from django import forms
from .models import GuestRoomAssignment, Room # Import Room if room_number is a ForeignKey
from django.utils import timezone

class GuestRoomAssignmentForm(forms.ModelForm):
    # Define separate fields for date and time inputs for the form
    # These are required fields, so set required=True
    check_in_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=True)
    check_in_time_input = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}), required=True)
    check_out_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=True)
    check_out_time_input = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}), required=True)

    class Meta:
        model = GuestRoomAssignment
        fields = ['room_number', 'guest_names', 'bill_amount', 'amount_paid', 'status']
    def __init__(self, *args, **kwargs):
        # Pop 'hotel' from kwargs if it's passed as an initial value from the view
        initial_hotel = kwargs.pop('hotel', None)
        super().__init__(*args, **kwargs)

        # Set initial values for the separate date/time fields if an instance exists (for editing)
        if self.instance.pk:
            if self.instance.check_in_time:
                self.fields['check_in_date'].initial = self.instance.check_in_time.date()
                self.fields['check_in_time_input'].initial = self.instance.check_in_time.time()
            if self.instance.check_out_time:
                self.fields['check_out_date'].initial = self.instance.check_out_time.date()
                self.fields['check_out_time_input'].initial = self.instance.check_out_time.time()
        
        # If a new instance is being created and initial_hotel is provided,
        # set it directly on the instance. This ensures it's available for model validation.
        if not self.instance.pk and initial_hotel:
            self.instance.hotel = initial_hotel

    def clean(self):
        cleaned_data = super().clean()

        # Get the cleaned individual date and time components
        check_in_date = cleaned_data.get('check_in_date')
        check_in_time_input = cleaned_data.get('check_in_time_input')
        check_out_date = cleaned_data.get('check_out_date')
        check_out_time_input = cleaned_data.get('check_out_time_input')

        # Combine them into full datetime objects and set them directly on the model instance
        # This is crucial so that the model's clean method (which runs after this)
        # has access to the combined datetime values.
        if check_in_date and check_in_time_input:
            self.instance.check_in_time = timezone.make_aware(
                timezone.datetime.combine(check_in_date, check_in_time_input)
            )
        else:
            # If date/time are required, add form errors if they are missing
            self.add_error('check_in_date', "Check-in date and time are required.")
            self.add_error('check_in_time_input', "Check-in date and time are required.")

        if check_out_date and check_out_time_input:
            self.instance.check_out_time = timezone.make_aware(
                timezone.datetime.combine(check_out_date, check_out_time_input)
            )
        else:
            self.add_error('check_out_date', "Check-out date and time are required.")
            self.add_error('check_out_time_input', "Check-out date and time are required.")

        # Perform cross-field validation here, e.g., check_in_time < check_out_time
        if self.instance.check_in_time and self.instance.check_out_time:
            if self.instance.check_in_time >= self.instance.check_out_time:
                self.add_error(None, "Check-out time must be after check-in time.") # Non-field error

        return cleaned_data
