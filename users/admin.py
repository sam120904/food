from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Volunteer

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_verified', 'trust_score')
    list_filter = ('role', 'is_verified')
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('role', 'is_verified', 'trust_score', 'latitude', 'longitude', 'restaurant_license', 'ngo_registration', 'institution_name')}),
    )

class VolunteerAdmin(admin.ModelAdmin):
    list_display = ('volunteer_id', 'name', 'ngo', 'phone', 'email', 'status', 'date_joined')
    list_filter = ('status', 'ngo')
    search_fields = ('name', 'volunteer_id', 'email')

admin.site.register(User, CustomUserAdmin)
admin.site.register(Volunteer, VolunteerAdmin)
