from django.contrib import admin

from .models import DBInstance, Query

# Register your models here.

admin.site.register(DBInstance)
admin.site.register(Query)