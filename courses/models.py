from django.db import models

from teachers.models import Teacher


class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)

    def __str__(self):
        return self.title


class Lesson(models.Model):
    course = models.ForeignKey(Course, related_name='lessons', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    content = models.TextField()
    order = models.PositiveIntegerField(help_text='Lesson order within the course')

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title


class StudyResource(models.Model):
    title = models.CharField(max_length=200)
    publisher = models.CharField(max_length=150)
    subject = models.CharField(max_length=50, blank=True)
    grade = models.CharField(max_length=10, blank=True)
    url = models.URLField()

    class Meta:
        ordering = ['grade', 'subject', 'title']

    def __str__(self):
        return self.title


class Enrollment(models.Model):
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    enrollment_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'course')

    def __str__(self):
        return f'{self.student.user.username} - {self.course.title}'


class LiveClass(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='live_classes')
    title = models.CharField(max_length=200)
    starts_at = models.DateTimeField()
    meet_url = models.URLField()
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['starts_at']

    def __str__(self):
        return f'{self.course.title}: {self.title}'


class Assignment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=200)
    instructions = models.TextField()
    due_date = models.DateTimeField()
    max_points = models.PositiveIntegerField(default=100)

    class Meta:
        ordering = ['due_date']

    def __str__(self):
        return f'{self.course.title}: {self.title}'


class Submission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='submissions')
    response = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    score = models.PositiveIntegerField(null=True, blank=True)
    feedback = models.TextField(blank=True)

    class Meta:
        ordering = ['-submitted_at']
        constraints = [
            models.UniqueConstraint(
                fields=['assignment', 'student'],
                name='unique_assignment_student_submission',
            ),
        ]

    def __str__(self):
        return f'{self.student.user.username}: {self.assignment.title}'


class FeeRecord(models.Model):
    class Status(models.TextChoices):
        DUE = 'due', 'Due'
        PAID = 'paid', 'Paid'

    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='fee_records')
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=9, decimal_places=2)
    due_date = models.DateField()
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.DUE)

    class Meta:
        ordering = ['due_date']

    def __str__(self):
        return f'{self.student.user.username}: {self.description}'
