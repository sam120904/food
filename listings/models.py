from django.db import models
from django.conf import settings
from django.utils import timezone

class Listing(models.Model):
    FOOD_TYPES = (
        ('cooked', 'Cooked Meal'),
        ('raw', 'Raw Ingredients'),
        ('packaged', 'Packaged Food'),
    )
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('claimed', 'Claimed'),
        ('completed', 'Completed'),
        ('expired', 'Expired'),
    )

    donor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='listings')
    food_type = models.CharField(max_length=20, choices=FOOD_TYPES)
    quantity_kg = models.FloatField()
    servings = models.IntegerField(default=1, help_text="Approximate number of people this can serve")
    description = models.TextField()
    expiry_time = models.DateTimeField()
    pickup_instructions = models.TextField(blank=True)
    image = models.ImageField(upload_to='listings/', blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.expiry_time

    def __str__(self):
        return f"{self.food_type} - {self.quantity_kg}kg by {self.donor.username}"

class Claim(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed (Picked Up)'),
    )

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='claims')
    claimant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='claims')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    claimed_at = models.DateTimeField(auto_now_add=True)
    
    # Verification
    claimant_photo = models.ImageField(upload_to='claims/', blank=True, null=True, help_text="Photo taken by claimant at pickup")
    donor_photo = models.ImageField(upload_to='claims/', blank=True, null=True, help_text="Photo taken by donor at handover")

    def __str__(self):
        return f"Claim for {self.listing} by {self.claimant.username}"


class PickupAssignment(models.Model):
    STATUS_CHOICES = (
        ('assigned', 'Assigned'),
        ('picked_up', 'Picked Up'),
        ('delivered', 'Delivered'),
    )

    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='pickup_assignments')
    volunteer = models.ForeignKey('users.Volunteer', on_delete=models.CASCADE, related_name='pickup_assignments')
    assigned_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='assigned')
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Pickup #{self.id} - {self.claim.listing} → {self.volunteer.name}"


class PickupOTP(models.Model):
    """
    One-time 6-digit OTP for verifying food pickup handoffs.
    Auto-created via signal when a PickupAssignment is created.
    """
    assignment = models.OneToOneField(
        PickupAssignment,
        on_delete=models.CASCADE,
        related_name='otp',
    )
    code = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Pickup OTP'
        verbose_name_plural = 'Pickup OTPs'

    def __str__(self):
        status = '✓ Verified' if self.is_verified else '⏳ Pending'
        return f"OTP for Pickup #{self.assignment_id} [{status}]"
