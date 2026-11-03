from django.db import models
from django.conf import settings

class Teacher(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    employee_id = models.CharField(max_length=20, unique=True)
    subject = models.CharField(max_length=50)
    subject_2 = models.CharField(max_length=50, blank=True)
    subject_3 = models.CharField(max_length=50, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)

    @property
    def subjects(self):
        return [
            subject
            for subject in (self.subject, self.subject_2, self.subject_3)
            if subject
        ]

    @property
    def subjects_display(self):
        return ', '.join(self.subjects)

    def __str__(self):
        return f"{self.user.username} - {self.subjects_display}"