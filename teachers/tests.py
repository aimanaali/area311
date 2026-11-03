from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from courses.models import Assignment, Course, Enrollment, LiveClass, Submission
from students.models import Student

from .models import Teacher


class CourseSetupWorkflowTests(TestCase):
    def setUp(self):
        self.teacher_user = User.objects.create_user(
            username='course-teacher',
            password='Safe-test-pass-123!',
            role=User.Role.TEACHER,
        )
        self.teacher = Teacher.objects.create(
            user=self.teacher_user,
            employee_id='T-COURSE-01',
            subject='Mathematics',
        )
        self.course = Course.objects.create(
            title='Mathematics Grade 9',
            subject='Mathematics',
            description='Grade 9 mathematics',
            teacher=self.teacher,
        )
        self.student_user = User.objects.create_user(
            username='enrolled-student',
            password='Safe-test-pass-123!',
            role=User.Role.STUDENT,
        )
        self.student = Student.objects.create(
            user=self.student_user,
            student_id='S-COURSE-01',
            grade='9',
        )
        self.other_user = User.objects.create_user(
            username='other-student',
            password='Safe-test-pass-123!',
            role=User.Role.STUDENT,
        )
        self.other_student = Student.objects.create(
            user=self.other_user,
            student_id='S-COURSE-02',
            grade='9',
        )

    def test_teacher_can_enroll_student_then_schedule_course_meet_link(self):
        self.client.force_login(self.teacher_user)
        manage_url = reverse('teachers:manage_course', args=[self.course.pk])
        response = self.client.get(manage_url)
        self.assertContains(response, 'Enroll student in this course')
        self.assertContains(response, 'Schedule Meet class for this course')

        enrollment_url = reverse(
            'teachers:enroll_student_in_course',
            args=[self.course.pk],
        )
        response = self.client.get(enrollment_url)
        self.assertContains(response, f'value="{self.course.pk}" selected')
        response = self.client.post(
            enrollment_url,
            {'course': self.course.pk, 'student': self.student.pk},
        )
        self.assertRedirects(response, reverse('teachers:dashboard'))
        self.assertTrue(
            Enrollment.objects.filter(student=self.student, course=self.course).exists()
        )

        schedule_url = reverse(
            'teachers:schedule_course_live_class',
            args=[self.course.pk],
        )
        response = self.client.get(schedule_url)
        self.assertContains(response, f'value="{self.course.pk}" selected')
        meet_url = 'https://meet.google.com/abc-defg-hij'
        response = self.client.post(
            schedule_url,
            {
                'course': self.course.pk,
                'title': 'Grade 9 mathematics class',
                'starts_at': (
                    timezone.now() + timedelta(days=1)
                ).strftime('%Y-%m-%dT%H:%M'),
                'meet_url': meet_url,
                'description': 'Join the scheduled class.',
            },
        )
        self.assertRedirects(response, reverse('teachers:dashboard'))
        self.assertTrue(
            LiveClass.objects.filter(course=self.course, meet_url=meet_url).exists()
        )

        self.client.force_login(self.student_user)
        response = self.client.get(reverse('students:dashboard'))
        self.assertContains(response, self.course.title)
        self.assertContains(response, 'Subject: Mathematics')
        self.assertContains(response, meet_url)

        self.client.force_login(self.other_user)
        response = self.client.get(reverse('students:dashboard'))
        self.assertNotContains(response, meet_url)
        self.assertNotContains(response, self.course.title)

    def test_teacher_cannot_manage_another_teachers_course(self):
        other_teacher_user = User.objects.create_user(
            username='other-course-teacher',
            password='Safe-test-pass-123!',
            role=User.Role.TEACHER,
        )
        other_teacher = Teacher.objects.create(
            user=other_teacher_user,
            employee_id='T-COURSE-02',
            subject='Science',
        )
        other_course = Course.objects.create(
            title='Science Grade 9',
            subject='Science',
            description='Grade 9 science',
            teacher=other_teacher,
        )
        self.client.force_login(self.teacher_user)
        response = self.client.get(
            reverse('teachers:manage_course', args=[other_course.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_admin_can_access_portals_and_manage_all_teachers_courses(self):
        admin_user = User.objects.create_superuser(
            username='global-admin',
            email='global-admin@example.test',
            password='Safe-test-pass-123!',
        )
        assignment = Assignment.objects.create(
            course=self.course,
            title='Admin grading test',
            instructions='Answer the question.',
            due_date=timezone.now() + timedelta(days=1),
        )
        submission = Submission.objects.create(
            assignment=assignment,
            student=self.student,
            response='Answer.',
        )
        live_class = LiveClass.objects.create(
            course=self.course,
            title='Admin edit test',
            starts_at=timezone.now() + timedelta(days=2),
            meet_url='https://meet.google.com/abc-defg-hij',
        )
        self.client.force_login(admin_user)

        urls = (
            reverse('teachers:dashboard'),
            reverse('teachers:manage_course', args=[self.course.pk]),
            reverse('teachers:create_course'),
            reverse('teachers:create_lesson'),
            reverse('teachers:create_live_class'),
            reverse('teachers:edit_live_class', args=[live_class.pk]),
            reverse('teachers:enroll_student'),
            reverse('teachers:create_assignment'),
            reverse('teachers:grade_submission', args=[submission.pk]),
            reverse('students:dashboard'),
            reverse('students:course_list'),
            reverse('accounts:parent_dashboard'),
        )
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

        response = self.client.post(
            reverse('teachers:create_course'),
            {
                'title': 'Admin-created course',
                'subject': 'Mathematics',
                'description': 'Created by an administrator.',
                'teacher': self.teacher.pk,
            },
        )
        self.assertRedirects(response, reverse('teachers:dashboard'))
        self.assertTrue(
            Course.objects.filter(
                title='Admin-created course',
                teacher=self.teacher,
            ).exists()
        )

    def test_teacher_can_create_course_in_any_assigned_subject(self):
        self.teacher.subject_2 = 'English'
        self.teacher.subject_3 = 'Urdu'
        self.teacher.save(update_fields=['subject_2', 'subject_3'])
        self.client.force_login(self.teacher_user)

        response = self.client.get(reverse('teachers:create_course'))
        self.assertContains(response, 'English')
        self.assertContains(response, 'Urdu')

        response = self.client.post(
            reverse('teachers:create_course'),
            {
                'title': 'English Grade 9',
                'subject': 'English',
                'description': 'English language course',
            },
        )

        self.assertRedirects(response, reverse('teachers:dashboard'))
        self.assertTrue(
            Course.objects.filter(
                title='English Grade 9',
                subject='English',
                teacher=self.teacher,
            ).exists()
        )
