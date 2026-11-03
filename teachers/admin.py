from django.contrib import admin

from .models import Teacher


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'user', 'subject', 'subject_2', 'subject_3', 'phone_number')
    search_fields = (
        'employee_id',
        'user__username',
        'user__first_name',
        'user__last_name',
        'user__email',
    )
    list_filter = ('subject', 'subject_2', 'subject_3')