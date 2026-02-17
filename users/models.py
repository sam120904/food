from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('donor', 'Donor'),
        ('claimant', 'Claimant'),
        ('volunteer', 'Volunteer'),
        ('admin', 'Admin'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='claimant')
    is_verified = models.BooleanField(default=False)
    
    # Location
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    address = models.TextField(blank=True)
    
    # Verification details
    restaurant_license = models.CharField(max_length=50, blank=True, help_text="For Donors")
    ngo_registration = models.CharField(max_length=50, blank=True, help_text="For Claimants")
    
    # Institutional details
    institution_name = models.CharField(max_length=100, blank=True)

    # Trust Score
    trust_score = models.FloatField(default=5.0)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class Volunteer(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    )

    ngo = models.ForeignKey(User, on_delete=models.CASCADE, related_name='volunteers', limit_choices_to={'role': 'claimant'})
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='volunteer_profile')
    name = models.CharField(max_length=100)
    volunteer_id = models.CharField(max_length=20, unique=True, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    date_joined = models.DateField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.volunteer_id:
            # Auto-generate volunteer ID: VOL-<ngo_id>-<count+1>
            count = Volunteer.objects.filter(ngo=self.ngo).count()
            self.volunteer_id = f"VOL-{self.ngo.id:03d}-{count + 1:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.volunteer_id})"
