from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'role', 'restaurant_license', 'ngo_registration', 'institution_name', 'address', 'latitude', 'longitude')
        widgets = {
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
        }

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        if role == 'donor' and not cleaned_data.get('restaurant_license'):
            self.add_error('restaurant_license', 'Restaurant License is required for Donors.')
        if role == 'claimant' and not cleaned_data.get('ngo_registration'):
            self.add_error('ngo_registration', 'NGO Registration is required for Claimants.')
        return cleaned_data

    def clean_restaurant_license(self):
        license_no = self.cleaned_data.get('restaurant_license')
        if license_no:
            if not license_no.isdigit():
                raise forms.ValidationError("FSSAI License must contain only digits.")
            if len(license_no) != 14:
                raise forms.ValidationError("FSSAI License must be exactly 14 digits.")
        return license_no

    def clean_ngo_registration(self):
        reg_no = self.cleaned_data.get('ngo_registration')
        if reg_no:
            if not reg_no.isdigit():
                raise forms.ValidationError("NGO Registration Number must contain only digits.")
            if len(reg_no) != 14:
                raise forms.ValidationError("NGO Registration Number must be exactly 14 digits.")
        return reg_no
