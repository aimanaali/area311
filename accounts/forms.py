from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction

from students.models import Student

from .models import Message, Parent, User


class PortalUserCreationForm(UserCreationForm):
    role = forms.ChoiceField(choices=User.Role.choices)
    student_id = forms.CharField(max_length=20, required=False)
    grade = forms.CharField(max_length=10, required=False)
    employee_id = forms.CharField(max_length=20, required=False)
    subject = forms.CharField(max_length=50, required=False, label='Subject 1')
    subject_2 = forms.CharField(max_length=50, required=False, label='Subject 2')
    subject_3 = forms.CharField(max_length=50, required=False, label='Subject 3')
    children = forms.ModelMultipleChoiceField(
        queryset=Student.objects.select_related('user').order_by('user__username'),
        required=False,
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'role')

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        required_by_role = {
            User.Role.STUDENT: ('student_id', 'grade'),
            User.Role.TEACHER: ('employee_id', 'subject'),
        }
        for field in required_by_role.get(role, ()):
            if not cleaned_data.get(field):
                self.add_error(field, 'This field is required for this account role.')
        if role == User.Role.TEACHER:
            subjects = [
                cleaned_data.get(field, '').strip().casefold()
                for field in ('subject', 'subject_2', 'subject_3')
                if cleaned_data.get(field, '').strip()
            ]
            if len(subjects) != len(set(subjects)):
                self.add_error(None, 'Enter each teacher subject only once.')
        if role == User.Role.STUDENT:
            student_id = cleaned_data.get('student_id')
            if student_id and Student.objects.filter(student_id=student_id).exists():
                self.add_error('student_id', 'This student ID is already in use.')
        elif role == User.Role.TEACHER:
            from teachers.models import Teacher

            employee_id = cleaned_data.get('employee_id')
            if employee_id and Teacher.objects.filter(employee_id=employee_id).exists():
                self.add_error('employee_id', 'This employee ID is already in use.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = self.cleaned_data['role']
        if commit:
            with transaction.atomic():
                user.save()
                if user.role == User.Role.STUDENT:
                    Student.objects.create(
                        user=user,
                        student_id=self.cleaned_data['student_id'],
                        grade=self.cleaned_data['grade'],
                    )
                elif user.role == User.Role.TEACHER:
                    from teachers.models import Teacher

                    Teacher.objects.create(
                        user=user,
                        employee_id=self.cleaned_data['employee_id'],
                        subject=self.cleaned_data['subject'].strip(),
                        subject_2=self.cleaned_data['subject_2'].strip(),
                        subject_3=self.cleaned_data['subject_3'].strip(),
                    )
                else:
                    parent = Parent.objects.create(user=user)
                    parent.children.set(self.cleaned_data['children'])
        return user


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ('recipient', 'body')
        widgets = {
            'body': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, recipients=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['recipient'].queryset = recipients if recipients is not None else User.objects.none()
