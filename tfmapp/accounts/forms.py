from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, PasswordResetForm, AuthenticationForm


class UserCreateForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name','username', 'email', 'password1', 'password2', ]
        labels = {
        'first_name': 'First Name',
        'last_name': 'Last Name',
        'username': 'User Name',
        'email': 'Email Address',
        'password1': 'Password',
        'password2': 'Re-enter Password'
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'type': 'text', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'type': 'text', 'placeholder': 'Last Name'}),
            'username': forms.TextInput(attrs={'type': 'text', 'placeholder': 'User Name'}),
            'email': forms.EmailInput(attrs={'type': 'text', 'placeholder': 'Email Address'}),
            'password1': forms.PasswordInput(attrs={'type': 'password', 'placeholder': 'Password'}),
            'password2': forms.PasswordInput(attrs={'type': 'password', 'placeholder': 'Re-enter Password'}),
        }

    def clean_email(self):
        """Comprueba que no exista un email igual en la db"""
        email = self.cleaned_data['email']
        if User.objects.filter(email=email):
            raise forms.ValidationError('Email already registered')
        return email
