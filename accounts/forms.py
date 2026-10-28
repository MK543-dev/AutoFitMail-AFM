from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password


class SignUpForm(forms.Form):
    first_name = forms.CharField(max_length=60, label='Full name')
    email = forms.EmailField()
    password1 = forms.CharField(widget=forms.PasswordInput, label='Password')
    password2 = forms.CharField(widget=forms.PasswordInput, label='Confirm password')

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(username__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean(self):
        data = super().clean()
        if data.get('password1') != data.get('password2'):
            raise forms.ValidationError('Passwords do not match.')
        if data.get('password1'):
            validate_password(data['password1'])
        return data

    def save(self):
        d = self.cleaned_data
        return User.objects.create_user(
            username=d['email'], email=d['email'],
            password=d['password1'], first_name=d['first_name'],
        )
