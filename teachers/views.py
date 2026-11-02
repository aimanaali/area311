from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.decorators import role_required
from accounts.models import User
from courses.forms import (
    AssignmentForm,
    CourseForm,
    EnrollmentForm,
    GradeForm,
    LessonForm,
    LiveClassForm,
)
from courses.models import Assignment, Course, Enrollment, LiveClass, Submission
from students.models import Student

from .models import Teacher


def _teacher_for_user(user):
    return get_object_or_404(Teacher, user=user)


def _render_form(request, form, title):
    return render(
        request,
        'courses/form.html',
        {'form': form, 'title': title, 'back_url': 'teachers:dashboard'},
    )


@role_required(User.Role.TEACHER)
def dashboard(request):
    teacher = _teacher_for_user(request.user)
    courses = Course.objects.filter(teacher=teacher).prefetch_related(
        'live_classes', 'assignments'
    )
    live_classes = LiveClass.objects.filter(
        course__teacher=teacher,
        starts_at__gte=timezone.now(),
    ).select_related('course')
    assignments = Assignment.objects.filter(
        course__teacher=teacher
    ).select_related('course')
    submissions = Submission.objects.filter(
        assignment__course__teacher=teacher
    ).select_related('assignment', 'student__user')
    pending_submission_count = submissions.filter(score__isnull=True).count()
    return render(
        request,
        'teachers/dashboard.html',
        {
            'teacher': teacher,
            'courses': courses,
            'live_classes': live_classes,
            'assignments': assignments,
            'submissions': submissions,
            'course_count': courses.count(),
            'pending_submission_count': pending_submission_count,
        },
    )


@role_required(User.Role.TEACHER)
def create_course(request):
    teacher = _teacher_for_user(request.user)
    form = CourseForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        course = form.save(commit=False)
        course.teacher = teacher
        course.save()
        messages.success(request, 'Course created.')
        return redirect('teachers:dashboard')
    return _render_form(request, form, 'Create a course')


@role_required(User.Role.TEACHER)
def manage_course(request, course_id):
    teacher = _teacher_for_user(request.user)
    course = get_object_or_404(
        Course.objects.filter(teacher=teacher).select_related('teacher__user'),
        pk=course_id,
    )
    enrollments = Enrollment.objects.filter(course=course).select_related(
        'student__user'
    ).order_by('student__user__last_name', 'student__user__first_name')
    live_classes = LiveClass.objects.filter(course=course)
    return render(
        request,
        'teachers/course_detail.html',
        {
            'course': course,
            'enrollments': enrollments,
            'live_classes': live_classes,
        },
    )


@role_required(User.Role.TEACHER)
def create_lesson(request):
    teacher = _teacher_for_user(request.user)
    courses = Course.objects.filter(teacher=teacher)
    form = LessonForm(request.POST or None, courses=courses)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Study material added.')
        return redirect('teachers:dashboard')
    return _render_form(request, form, 'Add study material')


@role_required(User.Role.TEACHER)
def create_live_class(request, live_class_id=None, course_id=None):
    teacher = _teacher_for_user(request.user)
    courses = Course.objects.filter(teacher=teacher)
    live_class = None
    if live_class_id is not None:
        live_class = get_object_or_404(
            LiveClass,
            pk=live_class_id,
            course__teacher=teacher,
        )
        course_id = live_class.course_id
    elif course_id is not None:
        get_object_or_404(courses, pk=course_id)
    initial = {'course': course_id} if course_id is not None else None
    form = LiveClassForm(
        request.POST or None,
        instance=live_class,
        initial=initial,
        courses=courses,
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Live class schedule saved.')
        return redirect('teachers:dashboard')
    title = 'Reschedule live class' if live_class else 'Schedule a live class'
    return _render_form(request, form, title)


@role_required(User.Role.TEACHER)
def cancel_live_class(request, live_class_id):
    teacher = _teacher_for_user(request.user)
    live_class = get_object_or_404(
        LiveClass,
        pk=live_class_id,
        course__teacher=teacher,
    )
    if request.method == 'POST':
        live_class.delete()
        messages.success(request, 'Live class cancelled.')
    return redirect('teachers:dashboard')


@role_required(User.Role.TEACHER)
def create_assignment(request):
    teacher = _teacher_for_user(request.user)
    courses = Course.objects.filter(teacher=teacher)
    form = AssignmentForm(request.POST or None, courses=courses)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Assignment published.')
        return redirect('teachers:dashboard')
    return _render_form(request, form, 'Create an assignment')


@role_required(User.Role.TEACHER)
def enroll_student(request, course_id=None):
    teacher = _teacher_for_user(request.user)
    courses = Course.objects.filter(teacher=teacher)
    if course_id is not None:
        get_object_or_404(courses, pk=course_id)
    students = Student.objects.filter(user__role=User.Role.STUDENT).select_related('user')
    initial = {'course': course_id} if course_id is not None else None
    form = EnrollmentForm(
        request.POST or None,
        initial=initial,
        courses=courses,
        students=students,
    )
    if request.method == 'POST' and form.is_valid():
        enrollment = form.save(commit=False)
        if enrollment.course.teacher_id != teacher.pk:
            form.add_error('course', 'You can only manage your own courses.')
        elif enrollment.course.enrollment_set.filter(student=enrollment.student).exists():
            form.add_error(None, 'This student is already enrolled in that course.')
        else:
            enrollment.save()
            messages.success(request, 'Student enrolled in the course.')
            return redirect('teachers:dashboard')
    return _render_form(request, form, 'Enroll a student')


@role_required(User.Role.TEACHER)
def grade_submission(request, submission_id):
    teacher = _teacher_for_user(request.user)
    submission = get_object_or_404(
        Submission,
        pk=submission_id,
        assignment__course__teacher=teacher,
    )
    form = GradeForm(request.POST or None, instance=submission)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Grade saved.')
        return redirect('teachers:dashboard')
    return _render_form(request, form, f'Grade: {submission.assignment.title}')
