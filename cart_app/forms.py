from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import authenticate
from .models import User

class CustomUserCreationForm(UserCreationForm):
    phone_number = forms.CharField(max_length=15, required=True)
    email = forms.EmailField(required=False)

    class Meta:
        model = User
        fields = ('phone_number', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['phone_number']  # Use phone number as username
        user.phone_number = self.cleaned_data['phone_number']
        if self.cleaned_data.get('email'):
            user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label='Phone Number', max_length=15)

    def clean(self):
        phone_number = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if phone_number and password:
            self.user_cache = authenticate(username=phone_number, password=password)
            if self.user_cache is None:
                raise forms.ValidationError(
                    'Please enter a correct phone number and password. Note that both fields may be case-sensitive.',
                    code='invalid_login'
                )
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data 