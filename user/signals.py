from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Auto-create a UserProfile whenever a new User is saved."""
    if created:
        role = 'admin' if instance.is_superuser else 'seller'
        UserProfile.objects.get_or_create(
            user=instance,
            defaults={'role': role}
        )


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save the profile whenever the User is saved. Create if missing."""
    try:
        instance.profile.save()
    except UserProfile.DoesNotExist:
        # Profile somehow missing — create it now
        role = 'admin' if instance.is_superuser else 'seller'
        UserProfile.objects.create(user=instance, role=role)
