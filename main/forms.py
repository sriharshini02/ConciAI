# main/forms.py

from django import forms
from django.utils import timezone
from .models import GuestRoomAssignment # Corrected model name

class GuestRoomAssignmentForm(forms.ModelForm): # Corrected form name
    # Add separate date and time fields for better user input in forms
    check_in_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=True)
    check_in_time_input = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}), required=True)
    check_out_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=True)
    check_out_time_input = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}), required=True)

    class Meta:
        model = GuestRoomAssignment # Corrected model name
        fields = [
            'hotel', 'room_number', 'guest_names',
            'bill_amount', 'amount_paid', 'status' # Added 'status' field
        ]
        # Make hotel field hidden as it's set by the view based on user's hotel
        widgets = {
            'hotel': forms.HiddenInput(),
            'status': forms.Select(choices=GuestRoomAssignment.STATUS_CHOICES), # Use a select widget for status
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If an instance is provided (for editing), populate date/time fields
        if self.instance and self.instance.pk:
            if self.instance.check_in_time:
                self.initial['check_in_date'] = self.instance.check_in_time.date()
                self.initial['check_in_time_input'] = self.instance.check_in_time.time()
            if self.instance.check_out_time:
                self.initial['check_out_date'] = self.instance.check_out_time.date()
                self.initial['check_out_time_input'] = self.instance.check_out_time.time()
        
        # Add Bootstrap-like classes for styling
        for field_name, field in self.fields.items():
            if isinstance(field.widget, (forms.TextInput, forms.Textarea, forms.NumberInput, forms.DateInput, forms.TimeInput, forms.Select)):
                field.widget.attrs.update({'class': 'form-control'})

    def clean(self):
        cleaned_data = super().clean()
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

        if 'check_in_time' in cleaned_data and 'check_out_time' in cleaned_data:
            if cleaned_data['check_out_time'] <= cleaned_data['check_in_time']:
                self.add_error(None, "Check-out time must be strictly after check-in time.")

        return cleaned_data

    def save(self, commit=True):
        if 'check_in_time' in self.cleaned_data:
            self.instance.check_in_time = self.cleaned_data['check_in_time']
        if 'check_out_time' in self.cleaned_data:
            self.instance.check_out_time = self.cleaned_data['check_out_time']
        
        return super().save(commit=commit)
