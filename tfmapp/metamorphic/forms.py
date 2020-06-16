from django import forms
from .models import DBInstance, Query
from django.utils.translation import ugettext_lazy as _


class DBInstanceForm(forms.ModelForm):
    class Meta:
        model = DBInstance      
        exclude = ['user']
        labels = {
          'db_name': _('Database Name'),
          'db_user': _('Database User'),
          'db_password': _('Database Password'),
          'host': _('Host'),
          'port': _('Port'),
        }
        widgets = {
           'db_name': forms.TextInput(attrs={'class': 'form-control', 'type': 'text', 'placeholder': 'Database User'}),
           'db_user': forms.TextInput(attrs={'class': 'form-control', 'type': 'text', 'placeholder': 'Database User'}),
           'db_password': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}),
           'host': forms.TextInput(attrs={'class': 'form-control', 'type': 'text', 'placeholder': 'Host'}),
           'port': forms.TextInput(attrs={'class': 'form-control', 'type': 'text', 'placeholder': 'Port'}),
        }


class QueryForm(forms.ModelForm):
    class Meta:
        model = Query      
        exclude = ['user']
        labels = {
          'query_id': _('Query ID'),
          'query_text': _('Query'),
          'instance': _('Instance'),
        }
        widgets = {
           'query_id': forms.TextInput(attrs={'class': 'form-control', 'type': 'text', 'placeholder': 'Query ID'}),
           'query_text': forms.Textarea(attrs={'class': 'form-control', 'type': 'text', 'style': 'resize: none;'}),
           'instance': forms.Select(attrs={'class': 'form-control', 'type': 'select'}),
        }


class QueryTextForm(forms.ModelForm):
    class Meta:
        model = Query      
        fields = ['query_text']
        labels = {
          'query_text': _('Query'),
        }
        widgets = {
           'query_text': forms.Textarea(attrs={'class': 'form-control', 'type': 'text', 'style': 'resize: none;'}),
        }
