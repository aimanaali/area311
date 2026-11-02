from django.contrib import admin

from .models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        'student_id',
        'user',
        'grade',
        'phone_number',
        'guardian_name',
        'guardian_phone',
    )
    search_fields = (
        'student_id',
        'user__username',
        'user__first_name',
        'user__last_name',
        'user__email',
        'guardian_name',
    )
    list_filter = ('grade',)