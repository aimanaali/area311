from django import forms
from django.core.exceptions import ValidationError
from urllib.parse import urlparse

from teachers.models import Teacher

from .models import Assignment, Course, Enrollment, Lesson, LiveClass, Submission


class CourseForm(forms.ModelForm):
    subject = forms.ChoiceField(choices=())

    class Meta:
        model = Course
        fields = ('title', 'description')
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, teacher=None, is_admin=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.teacher = teacher
        if is_admin:
            self.fields['teacher'] = forms.ModelChoiceField(
                queryset=Teacher.objects.select_related('user').order_by('user__username'),
            )
            available_subjects = {
                subject
                for record in Teacher.objects.only('subject', 'subject_2', 'subject_3')
                for subject in record.subjects
            }
        elif teacher is not None:
            available_subjects = set(teacher.subjects)
        else:
            available_subjects = set()
        self.fields['subject'].choices = [
            ('', 'Select a subject'),
            *((subject, subject) for subject in sorted(available_subjects, key=str.casefold)),
        ]

    def clean(self):
        cleaned_data = super().clean()
        teacher = cleaned_data.get('teacher') if 'teacher' in self.fields else self.teacher
        subject = cleaned_data.get('subject')
        if teacher and subject and subject not in teacher.subjects:
            self.add_error('subject', 'Select a subject assigned to this teacher.')
        return cleaned_data


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ('course', 'title', 'content', 'order')
        widgets = {'content': forms.Textarea(attrs={'rows': 5})}

    def __init__(self, *args, courses=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['course'].queryset = courses if courses is not None else self.fields['course'].queryset.none()


class LiveClassForm(forms.ModelForm):
    class Meta:
        model = LiveClass
        fields = ('course', 'title', 'starts_at', 'meet_url', 'description')
        widgets = {
            'starts_at': forms.DateTimeInput(
                format='%Y-%m-%dT%H:%M',
                attrs={'type': 'datetime-local'},
            ),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, courses=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['course'].queryset = courses if courses is not None else self.fields['course'].queryset.none()

    def clean_meet_url(self):
        meet_url = self.cleaned_data['meet_url']
        parsed_url = urlparse(meet_url)
        if parsed_url.scheme != 'https' or parsed_url.hostname != 'meet.google.com':
            raise ValidationError('Enter an HTTPS Google Meet link from meet.google.com.')
        return meet_url


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ('course', 'title', 'instructions', 'due_date', 'max_points')
        widgets = {
            'instructions': forms.Textarea(attrs={'rows': 4}),
            'due_date': forms.DateTimeInput(
                format='%Y-%m-%dT%H:%M',
                attrs={'type': 'datetime-local'},
            ),
        }

    def __init__(self, *args, courses=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['course'].queryset = courses if courses is not None else self.fields['course'].queryset.none()


class EnrollmentForm(forms.ModelForm):
    class CourseField(forms.ModelChoiceField):
        def label_from_instance(self, course):
            teacher_name = course.teacher.user.get_full_name() or course.teacher.user.username
            return f'{course.subject} — {course.title} ({teacher_name})'

    course = CourseField(queryset=Course.objects.none())

    class Meta:
        model = Enrollment
        fields = ('course', 'student')

    def __init__(self, *args, courses=None, students=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['course'].queryset = courses if courses is not None else self.fields['course'].queryset.none()
        self.fields['student'].queryset = students if students is not None else self.fields['student'].queryset.none()

    def clean(self):
        cleaned_data = super().clean()
        course = cleaned_data.get('course')
        student = cleaned_data.get('student')
        if course and student and Enrollment.objects.filter(
            course=course,
            student=student,
        ).exists():
            raise ValidationError('This student is already enrolled in that subject.')
        return cleaned_data


class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ('response',)
        widgets = {'response': forms.Textarea(attrs={'rows': 6})}


class GradeForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ('score', 'feedback')
        widgets = {'feedback': forms.Textarea(attrs={'rows': 3})}

    def clean_score(self):
        score = self.cleaned_data['score']
        if score is not None and score > self.instance.assignment.max_points:
            raise ValidationError(
                f'Score cannot exceed {self.instance.assignment.max_points} points.'
            )
        return score
