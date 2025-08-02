from django import forms
from .models import *

class CustomUserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'password', 'role']
        
class BrandingSettingsForm(forms.ModelForm):
    class Meta:
        model = BrandingSettings
        fields = '__all__'
