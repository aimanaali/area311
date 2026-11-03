from django.contrib import admin

from .models import (
    Assignment,
    Course,
    Enrollment,
    FeeRecord,
    Lesson,
    LiveClass,
    Submission,
    StudyResource,
)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'teacher')
    list_filter = ('subject', 'teacher')
    search_fields = ('title', 'subject', 'teacher__user__username')


admin.site.register(Lesson)
admin.site.register(Enrollment)


@admin.register(LiveClass)
class LiveClassAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'get_subject', 'starts_at')
    list_filter = ('starts_at', 'course')
    search_fields = ('title', 'course__title', 'course__subject')
    list_select_related = ('course', 'course__teacher')
    date_hierarchy = 'starts_at'

    @admin.display(description='Subject', ordering='course__subject')
    def get_subject(self, live_class):
        return live_class.course.subject


admin.site.register(Assignment)
admin.site.register(Submission)
admin.site.register(StudyResource)
admin.site.register(FeeRecord)
