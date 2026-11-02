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


admin.site.register(Course)
admin.site.register(Lesson)
admin.site.register(Enrollment)
admin.site.register(LiveClass)
admin.site.register(Assignment)
admin.site.register(Submission)
admin.site.register(StudyResource)
admin.site.register(FeeRecord)
