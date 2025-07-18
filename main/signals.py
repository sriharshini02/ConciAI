# main/signals.py

from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import UserProfile, Hotel # Ensure Hotel is imported

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Signal receiver to create a UserProfile automatically when a new User is created.
    If a UserProfile already exists, it ensures it's linked (though direct updates
    to existing profiles should be handled on the profile object itself).
    """
    if created:
        print(f"Signal: Creating UserProfile for new user: {instance.username}")
        # Try to get the first existing Hotel to link to the new UserProfile.
        # If no hotels exist yet, the 'hotel' field will be None (as it's null=True, blank=True).
        default_hotel = None
        try:
            default_hotel = Hotel.objects.first()
            if default_hotel:
                print(f"Signal: Linking new UserProfile to hotel: {default_hotel.name}")
            else:
                print("Signal: No Hotel objects found, UserProfile 'hotel' will be None.")
        except Exception as e:
            print(f"Signal Warning: Could not retrieve default Hotel for new UserProfile: {e}")
            
        UserProfile.objects.create(user=instance, hotel=default_hotel)
    # else:
    # This `else` block for `instance.profile.save()` is often problematic in signals
    # because `instance.profile` might not be fully loaded or ready, or it can cause
    # infinite recursion if UserProfile also has a post_save signal.
    # Updates to existing UserProfiles should typically be done explicitly.
    # print(f"Signal: UserProfile for {instance.username} already exists, skipping creation.")

