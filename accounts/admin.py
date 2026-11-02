from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Message, Parent, User


@admin.register(User)
class PortalUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (('Portal access', {'fields': ('role',)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Portal access', {'fields': ('role',)}),
    )
    list_display = ('username', 'email', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')


@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ('user',)
    filter_horizontal = ('children',)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'recipient', 'created_at', 'is_read')
    readonly_fields = ('created_at',)
