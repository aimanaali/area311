from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from courses.models import Assignment, Course, Enrollment, FeeRecord, LiveClass, Submission
from students.models import Student
from teachers.models import Teacher

from .models import Message, Parent, User


class PortalWorkflowTests(TestCase):
    def setUp(self):
        self.student_user = User.objects.create_user(
            username='student-one',
            password='Safe-test-pass-123!',
            role=User.Role.STUDENT,
        )
        self.student = Student.objects.create(
            user=self.student_user,
            student_id='S-100',
            grade='8',
        )
        self.teacher_user = User.objects.create_user(
            username='teacher-one',
            password='Safe-test-pass-123!',
            role=User.Role.TEACHER,
        )
        self.teacher = Teacher.objects.create(
            user=self.teacher_user,
            employee_id='T-100',
            subject='Science',
        )
        self.parent_user = User.objects.create_user(
            username='parent-one',
            password='Safe-test-pass-123!',
            role=User.Role.PARENT,
        )
        self.parent = Parent.objects.create(user=self.parent_user)
        self.parent.children.add(self.student)
        self.course = Course.objects.create(
            title='Science 8',
            description='Core science course',
            teacher=self.teacher,
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
        )

    def test_landing_page_links_each_portal_in_a_new_tab(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'target="_blank"', count=4)
        self.assertContains(
            response,
            f'{reverse("accounts:login")}?next={reverse("students:dashboard")}',
        )
        self.assertContains(
            response,
            f'{reverse("accounts:login")}?next={reverse("teachers:dashboard")}',
        )
        self.assertContains(
            response,
            f'{reverse("accounts:login")}?next={reverse("accounts:parent_dashboard")}',
        )
        self.assertContains(
            response,
            f'{reverse("accounts:login")}?next={reverse("accounts:admin_dashboard")}',
        )

    def test_role_login_redirects_to_correct_portals(self):
        self.client.force_login(self.student_user)
        response = self.client.get(reverse('accounts:dashboard_redirect'))
        self.assertRedirects(response, reverse('students:dashboard'))

        self.client.force_login(self.teacher_user)
        response = self.client.get(reverse('accounts:dashboard_redirect'))
        self.assertRedirects(response, reverse('teachers:dashboard'))

        self.client.force_login(self.parent_user)
        response = self.client.get(reverse('accounts:dashboard_redirect'))
        self.assertRedirects(response, reverse('accounts:parent_dashboard'))

    def test_anonymous_users_are_sent_to_login(self):
        response = self.client.get(reverse('students:dashboard'))
        self.assertRedirects(
            response,
            f'{reverse("accounts:login")}?next={reverse("students:dashboard")}',
        )

    def test_login_form_authenticates_and_redirects_by_role(self):
        response = self.client.post(
            reverse('accounts:login'),
            {'username': self.student_user.username, 'password': 'Safe-test-pass-123!'},
        )
        self.assertRedirects(response, reverse('accounts:dashboard_redirect'), fetch_redirect_response=False)
        response = self.client.get(reverse('accounts:dashboard_redirect'))
        self.assertRedirects(response, reverse('students:dashboard'))

    def test_student_sees_database_course_assignment_and_meet_link(self):
        live_class = LiveClass.objects.create(
            course=self.course,
            title='Live science',
            starts_at=timezone.now() + timedelta(days=1),
            meet_url='https://meet.google.com/abc-defg-hij',
        )
        assignment = Assignment.objects.create(
            course=self.course,
            title='Lab report',
            instructions='Describe the experiment.',
            due_date=timezone.now() + timedelta(days=2),
        )
        self.client.force_login(self.student_user)
        response = self.client.get(reverse('students:dashboard'))
        self.assertContains(response, self.course.title)
        self.assertContains(response, assignment.title)
        self.assertContains(response, live_class.meet_url)

    def test_teacher_can_schedule_only_google_meet_urls(self):
        self.client.force_login(self.teacher_user)
        response = self.client.post(
            reverse('teachers:create_live_class'),
            {
                'course': self.course.pk,
                'title': 'Weekly lesson',
                'starts_at': (timezone.now() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'),
                'meet_url': 'https://meet.google.com/abc-defg-hij',
                'description': 'Bring your workbook.',
            },
        )
        self.assertRedirects(response, reverse('teachers:dashboard'))
        self.assertTrue(LiveClass.objects.filter(title='Weekly lesson').exists())

        response = self.client.post(
            reverse('teachers:create_live_class'),
            {
                'course': self.course.pk,
                'title': 'External link',
                'starts_at': (timezone.now() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'),
                'meet_url': 'https://example.com/meeting',
                'description': '',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(LiveClass.objects.filter(title='External link').exists())

    def test_student_submission_can_be_graded_by_the_course_teacher(self):
        assignment = Assignment.objects.create(
            course=self.course,
            title='Lab report',
            instructions='Describe the experiment.',
            due_date=timezone.now() + timedelta(days=1),
            max_points=20,
        )
        self.client.force_login(self.student_user)
        response = self.client.post(
            reverse('students:submit_assignment', args=[assignment.pk]),
            {'response': 'The experiment showed a chemical change.'},
        )
        self.assertRedirects(response, reverse('students:dashboard'))
        submission = Submission.objects.get(assignment=assignment, student=self.student)

        self.client.force_login(self.teacher_user)
        response = self.client.post(
            reverse('teachers:grade_submission', args=[submission.pk]),
            {'score': 18, 'feedback': 'Good explanation.'},
        )
        self.assertRedirects(response, reverse('teachers:dashboard'))
        submission.refresh_from_db()
        self.assertEqual(submission.score, 18)

    def test_parent_sees_child_progress_and_fee_status(self):
        assignment = Assignment.objects.create(
            course=self.course,
            title='Lab report',
            instructions='Describe the experiment.',
            due_date=timezone.now() + timedelta(days=1),
            max_points=20,
        )
        Submission.objects.create(
            assignment=assignment,
            student=self.student,
            response='Completed.',
            score=18,
        )
        FeeRecord.objects.create(
            student=self.student,
            description='November tuition',
            amount='125.00',
            due_date=timezone.localdate() + timedelta(days=10),
            status=FeeRecord.Status.DUE,
        )
        self.client.force_login(self.parent_user)
        response = self.client.get(reverse('accounts:parent_dashboard'))
        self.assertContains(response, 'Science 8')
        self.assertContains(response, '18/20')
        self.assertContains(response, 'November tuition')
        self.assertContains(response, 'Due')

    def test_communication_is_limited_to_linked_course_participants(self):
        self.client.force_login(self.student_user)
        response = self.client.get(reverse('accounts:messages'))
        self.assertContains(response, self.teacher_user.username)
        self.assertNotContains(response, self.parent_user.username)
        response = self.client.post(
            reverse('accounts:messages'),
            {'recipient': self.teacher_user.pk, 'body': 'Question about the lesson.'},
        )
        self.assertRedirects(response, reverse('accounts:messages'))
        self.assertTrue(
            Message.objects.filter(
                sender=self.student_user,
                recipient=self.teacher_user,
                body='Question about the lesson.',
            ).exists()
        )

    def test_admin_can_create_a_student_account_and_profile(self):
        admin_user = User.objects.create_superuser(
            username='portal-admin',
            email='admin@example.test',
            password='Safe-test-pass-123!',
        )
        self.client.force_login(admin_user)
        response = self.client.post(
            reverse('accounts:admin_dashboard'),
            {
                'username': 'new-student',
                'first_name': 'New',
                'last_name': 'Student',
                'email': 'new-student@example.test',
                'role': User.Role.STUDENT,
                'student_id': 'S-200',
                'grade': '7',
                'employee_id': '',
                'subject': '',
                'password1': 'Safe-test-pass-456!',
                'password2': 'Safe-test-pass-456!',
            },
        )
        self.assertRedirects(response, reverse('accounts:admin_dashboard'))
        created_user = User.objects.get(username='new-student')
        self.assertEqual(created_user.role, User.Role.STUDENT)
        self.assertEqual(created_user.student.student_id, 'S-200')
