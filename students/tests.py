from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from courses.models import Course, Enrollment, LiveClass, StudyResource
from students.models import Student
from teachers.models import Teacher


class SeedDemoDataCommandTests(TestCase):
    meet_url = 'https://meet.google.com/abc-defg-hij'

    def run_seed(self):
        call_command(
            'seed_demo_data',
            meet_url=self.meet_url,
            password='Demo-only-pass-123!',
            allow_non_debug=True,
            stdout=StringIO(),
        )

    def test_seed_command_creates_lms_demo_data_and_book_links(self):
        self.run_seed()

        self.assertEqual(Student.objects.count(), 20)
        self.assertEqual(Teacher.objects.count(), 4)
        self.assertEqual(Course.objects.filter(title__startswith='Demo ').count(), 4)
        self.assertEqual(Enrollment.objects.count(), 80)
        self.assertEqual(StudyResource.objects.count(), 2)

        student = Student.objects.select_related('user').get(student_id='DEMO-S-001')
        self.assertEqual(student.user.get_full_name(), 'Ayesha Khan')
        self.assertEqual(student.user.email, 'student01@example.test')
        self.assertTrue(student.phone_number)
        self.assertTrue(student.guardian_name)
        self.assertTrue(student.guardian_phone)
        self.assertTrue(student.user.check_password('Demo-only-pass-123!'))

        live_class = LiveClass.objects.get(
            title='Demo live class - join using the teacher-provided Meet link'
        )
        self.assertEqual(live_class.meet_url, self.meet_url)
        self.assertEqual(live_class.course.teacher.subject, 'Mathematics')

        self.client.force_login(student.user)
        response = self.client.get(reverse('students:course_list'))
        self.assertContains(response, 'Punjab Textbook Board')
        self.assertContains(response, 'https://ptbb.punjab.gov.pk/')
        self.assertContains(response, 'https://elearn.gov.pk/')
        self.assertContains(response, 'target="_blank"')

    def test_seed_command_is_idempotent_and_does_not_reset_existing_password(self):
        self.run_seed()
        student_user = User.objects.get(username='demo.student.01')
        student_user.set_password('My-changed-demo-password-123!')
        student_user.save(update_fields=['password'])

        self.run_seed()

        self.assertEqual(Student.objects.count(), 20)
        self.assertEqual(Teacher.objects.count(), 4)
        self.assertEqual(Course.objects.filter(title__startswith='Demo ').count(), 4)
        self.assertEqual(Enrollment.objects.count(), 80)
        self.assertEqual(StudyResource.objects.count(), 2)
        self.assertEqual(LiveClass.objects.count(), 1)
        student_user.refresh_from_db()
        self.assertTrue(student_user.check_password('My-changed-demo-password-123!'))

    def test_seed_command_rejects_non_google_meet_urls(self):
        with self.assertRaises(CommandError):
            call_command(
                'seed_demo_data',
                meet_url='https://example.com/meeting',
                allow_non_debug=True,
                stdout=StringIO(),
            )
        self.assertEqual(User.objects.count(), 0)
