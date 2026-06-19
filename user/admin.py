from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile


class UserProfileInline(admin.StackedInline):
    model              = UserProfile
    can_delete         = False
    verbose_name_plural = 'Profile & Role'
    fields             = ['role', 'phone', 'address', 'image']
    extra              = 0  # Don't show empty extra forms

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs

    def has_add_permission(self, request, obj=None):
        # Allow adding profile if it doesn't exist yet
        if obj is not None:
            return not UserProfile.objects.filter(user=obj).exists()
        return True


class CustomUserAdmin(UserAdmin):
    inlines      = [UserProfileInline]
    list_display = ['username', 'email', 'first_name', 'last_name', 'get_role', 'is_active']

    def get_role(self, obj):
        try:
            return obj.profile.get_role_display()
        except UserProfile.DoesNotExist:
            # Create missing profile automatically
            role = 'admin' if obj.is_superuser else 'seller'
            UserProfile.objects.create(user=obj, role=role)
            return role.capitalize()
    get_role.short_description = 'Role'

    def get_inline_instances(self, request, obj=None):
        """Ensure profile exists before showing inline — prevents crash."""
        if obj is not None:
            try:
                obj.profile
            except UserProfile.DoesNotExist:
                role = 'admin' if obj.is_superuser else 'seller'
                UserProfile.objects.create(user=obj, role=role)
        return super().get_inline_instances(request, obj)


# Re-register User with the custom admin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ['user', 'role', 'phone']
    list_filter   = ['role']
    search_fields = ['user__username', 'user__email']
