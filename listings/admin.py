from django.contrib import admin
from .models import Listing, Claim, PickupAssignment, PickupOTP


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ('id', 'donor', 'food_type', 'quantity_kg', 'status', 'created_at')
    list_filter = ('status', 'food_type')


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ('id', 'listing', 'claimant', 'status', 'claimed_at')
    list_filter = ('status',)


@admin.register(PickupAssignment)
class PickupAssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'claim', 'volunteer', 'status', 'assigned_at')
    list_filter = ('status',)


@admin.register(PickupOTP)
class PickupOTPAdmin(admin.ModelAdmin):
    list_display = ('id', 'assignment', 'code', 'is_verified', 'verified_at', 'created_at')
    list_filter = ('is_verified',)
    readonly_fields = ('code', 'assignment', 'created_at')
