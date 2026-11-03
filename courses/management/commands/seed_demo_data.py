from datetime import timedelta
from urllib.parse import urlparse

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from courses.models import (
    Assignment,
    Course,
    Enrollment,
    Lesson,
    LiveClass,
    StudyResource,
)
from students.models import Student
from teachers.models import Teacher


STUDENTS = [
    ('Ayesha', 'Khan'),
    ('Muhammad', 'Ali'),
    ('Fatima', 'Ahmed'),
    ('Hamza', 'Malik'),
    ('Zainab', 'Hussain'),
    ('Usman', 'Sheikh'),
    ('Maryam', 'Iqbal'),
    ('Hassan', 'Raza'),
    ('Hira', 'Shah'),
    ('Bilal', 'Siddiqui'),
    ('Noor', 'Javed'),
    ('Ahmad', 'Farooq'),
    ('Sana', 'Akhtar'),
    ('Daniyal', 'Butt'),
    ('Laiba', 'Chaudhry'),
    ('Saad', 'Qureshi'),
    ('Maham', 'Tariq'),
    ('Ibrahim', 'Nawaz'),
    ('Eman', 'Yousaf'),
    ('Abdullah', 'Mirza'),
]

TEACHERS = [
    ('demo.teacher.math', 'Nida', 'Aslam', 'Mathematics', 'T-DEMO-001'),
    ('demo.teacher.science', 'Omar', 'Khalid', 'Science', 'T-DEMO-002'),
    ('demo.teacher.english', 'Sadia', 'Rauf', 'English', 'T-DEMO-003'),
    ('demo.teacher.urdu', 'Imran', 'Saleem', 'Urdu', 'T-DEMO-004'),
]

SUBJECTS = (
    ('Mathematics', 'Mathematics'),
    ('Science', 'General Science'),
    ('English', 'English'),
    ('Urdu', 'Urdu'),
)


class Command(BaseCommand):
    help = 'Create repeatable dummy LMS accounts, courses, enrollments, books, and a Google Meet class.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--meet-url',
            help='Optional existing Google Meet URL (https://meet.google.com/...).',
        )
        parser.add_argument(
            '--password',
            help='Optional shared password for newly created demo accounts. Existing passwords are never changed.',
        )
        parser.add_argument(
            '--allow-non-debug',
            action='store_true',
            help='Allow demo data creation when DEBUG is disabled.',
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options['allow_non_debug']:
            raise CommandError(
                'Refusing to add demo data while DEBUG is disabled. '
                'Use --allow-non-debug only if this is an intentional test database.'
            )

        meet_url = (options['meet_url'] or '').strip()
        if meet_url:
            parsed_url = urlparse(meet_url)
            if parsed_url.scheme != 'https' or parsed_url.hostname != 'meet.google.com':
                raise CommandError(
                    '--meet-url must be an HTTPS Google Meet link on meet.google.com.'
                )

        with transaction.atomic():
            teachers = self._create_teachers(options['password'])
            courses = self._create_courses(teachers)
            students = self._create_students(options['password'])
            self._create_enrollments(students, courses)
            self._create_resources()
            self._create_lessons(courses)
            self._create_assignments(courses)
            if meet_url:
                self._create_live_class(courses['Mathematics'], meet_url)

        password_note = (
            'New demo accounts use the supplied shared password.'
            if options['password']
            else 'New demo accounts have unusable passwords; set one with changepassword.'
        )
        class_note = 'one live class.' if meet_url else (
            'no live class was created because no Meet URL was provided. '
            'Rerun with --meet-url https://meet.google.com/your-room-code to add it.'
        )
        self.stdout.write(self.style.SUCCESS(
            'Demo data is ready: 20 students, 4 teachers, 4 courses, '
            f'enrollments, textbook links, and {class_note} {password_note}'
        ))
        self.stdout.write('Demo student usernames: demo.student.01 through demo.student.20')
        self.stdout.write('Demo teacher usernames: demo.teacher.math, demo.teacher.science, demo.teacher.english, demo.teacher.urdu')

    def _get_or_create_user(self, username, email, first_name, last_name, role, password):
        user = User.objects.filter(username=username).first()
        if user is not None:
            if user.role != role or user.is_superuser:
                raise CommandError(
                    f'Account "{username}" already exists with a different role.'
                )
            return user, False

        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role,
            password=password,
        )
        return user, True

    def _create_students(self, password):
        students = []
        for index, (first_name, last_name) in enumerate(STUDENTS, start=1):
            user, created = self._get_or_create_user(
                username=f'demo.student.{index:02d}',
                email=f'student{index:02d}@example.test',
                first_name=first_name,
                last_name=last_name,
                role=User.Role.STUDENT,
                password=password,
            )
            student, profile_created = Student.objects.get_or_create(
                user=user,
                defaults={
                    'student_id': f'DEMO-S-{index:03d}',
                    'grade': str(6 + ((index - 1) % 5)),
                    'phone_number': f'0300-000-{index:04d}',
                    'address': f'Demo address {index:02d}, Lahore, Punjab',
                    'guardian_name': f'Mr. {last_name}',
                    'guardian_phone': f'0300-900-{index:04d}',
                },
            )
            if not profile_created and student.student_id != f'DEMO-S-{index:03d}':
                raise CommandError(
                    f'Unexpected student profile already exists for "{user.username}".'
                )
            students.append(student)
        return students

    def _create_teachers(self, password):
        teachers = {}
        for username, first_name, last_name, subject, employee_id in TEACHERS:
            user, _ = self._get_or_create_user(
                username=username,
                email=f'{username.replace(".", "_")}@example.test',
                first_name=first_name,
                last_name=last_name,
                role=User.Role.TEACHER,
                password=password,
            )
            teacher, created = Teacher.objects.get_or_create(
                user=user,
                defaults={
                    'employee_id': employee_id,
                    'subject': subject,
                    'phone_number': f'0300-800-{len(teachers) + 1:04d}',
                },
            )
            if not created and teacher.employee_id != employee_id:
                raise CommandError(
                    f'Unexpected teacher profile already exists for "{user.username}".'
                )
            teachers[subject] = teacher
        return teachers

    def _create_courses(self, teachers):
        courses = {}
        for subject, course_title in SUBJECTS:
            course, created = Course.objects.get_or_create(
                title=f'Demo {course_title} (Punjab Grade 6-10)',
                defaults={
                    'subject': subject,
                    'description': (
                        f'Demo {course_title} course for Punjab grades 6-10. '
                        'Use the official Punjab textbook links in the student library.'
                    ),
                    'teacher': teachers[subject],
                },
            )
            if not created and course.teacher_id != teachers[subject].pk:
                raise CommandError(
                    f'The demo course "{course.title}" is assigned to another teacher.'
                )
            courses[subject] = course
        return courses

    def _create_enrollments(self, students, courses):
        for student in students:
            for course in courses.values():
                Enrollment.objects.get_or_create(student=student, course=course)

    def _create_resources(self):
        resources = (
            {
                'title': 'Punjab Textbook Board - official website',
                'publisher': 'Punjab Curriculum and Textbook Board',
                'subject': '',
                'grade': '',
                'url': 'https://ptbb.punjab.gov.pk/',
            },
            {
                'title': 'eLearn Punjab - digital textbooks and learning resources',
                'publisher': 'Government of Punjab',
                'subject': '',
                'grade': '',
                'url': 'https://elearn.gov.pk/',
            },
        )
        for resource in resources:
            StudyResource.objects.get_or_create(
                title=resource['title'],
                publisher=resource['publisher'],
                defaults=resource,
            )

    def _create_lessons(self, courses):
        for order, (subject, course) in enumerate(courses.items(), start=1):
            Lesson.objects.get_or_create(
                course=course,
                title='Official textbook and study resources',
                defaults={
                    'content': (
                        f'Use the official Punjab textbook links in the student library '
                        f'for {subject}. Ask your teacher for the current chapter and edition.'
                    ),
                    'order': order,
                },
            )

    def _create_assignments(self, courses):
        for subject, course in courses.items():
            Assignment.objects.get_or_create(
                course=course,
                title=f'Demo {subject} study check',
                defaults={
                    'instructions': (
                        f'Write a short response showing what you learned in {subject}. '
                        'This is sample assignment data.'
                    ),
                    'due_date': timezone.now() + timedelta(days=14),
                    'max_points': 20,
                },
            )

    def _create_live_class(self, course, meet_url):
        LiveClass.objects.update_or_create(
            course=course,
            title='Demo live class - join using the teacher-provided Meet link',
            defaults={
                'starts_at': timezone.now() + timedelta(days=1),
                'meet_url': meet_url,
                'description': 'Sample scheduled class. Confirm the time with your teacher.',
            },
        )
