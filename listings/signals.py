import secrets
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import PickupAssignment, PickupOTP


@receiver(post_save, sender=PickupAssignment)
def create_pickup_otp(sender, instance, created, **kwargs):
    """Auto-generate a secure 6-digit OTP when a PickupAssignment is created."""
    if created:
        code = f"{secrets.randbelow(1000000):06d}"
        PickupOTP.objects.create(assignment=instance, code=code)
