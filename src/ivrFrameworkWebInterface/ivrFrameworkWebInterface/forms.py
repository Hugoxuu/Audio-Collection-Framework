from django import forms

from django.contrib.auth.models import User
from django.contrib.auth import authenticate

from ivrFrameworkWebInterface.models import *


class LoginForm(forms.Form):
    username = forms.CharField(label='Username', max_length=20,
                               widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(label='Password', max_length=200,
                               widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    # Customizes form validation for properties that apply to more
    # than one field.  Overrides the forms.Form.clean function.
    def clean(self):
        # Calls our parent (forms.Form) .clean function, gets a dictionary
        # of cleaned data as a result
        cleaned_data = super().clean()

        # Confirms that the two password fields match
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        user = authenticate(username=username, password=password)
        if not user:
            raise forms.ValidationError("Invalid username/password")

        # We must return the cleaned data we got from our parent.
        return cleaned_data
