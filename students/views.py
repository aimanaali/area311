from django.contrib import messages
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.decorators import role_required
from accounts.models import User
from courses.forms import SubmissionForm
from courses.models import Assignment, Course, LiveClass, StudyResource, Submission

from .models import Student


def _student_for_user(user):
    return Student.objects.filter(user=user).first()


@role_required(User.Role.STUDENT)
def dashboard(request):
    student = _student_for_user(request.user)
    is_admin_view = request.user.is_superuser
    if student is None and not is_admin_view:
        messages.warning(request, 'Your student profile has not been set up yet.')
        return render(request, 'students/dashboard.html', {'student': None})

    upcoming_course_classes = LiveClass.objects.filter(
        starts_at__gte=timezone.now()
    )
    courses = Course.objects.all() if is_admin_view else Course.objects.filter(
        enrollment__student=student
    )
    courses = courses.select_related(
        'teacher__user'
    ).prefetch_related(
        Prefetch(
            'live_classes',
            queryset=upcoming_course_classes,
            to_attr='upcoming_live_classes',
        )
    ).distinct()
    assignments = Assignment.objects.all() if is_admin_view else Assignment.objects.filter(
        course__enrollment__student=student
    )
    assignments = assignments.select_related('course').prefetch_related(
        Prefetch(
            'submissions',
            queryset=Submission.objects.filter(student=student) if student else Submission.objects.none(),
            to_attr='student_submissions',
        )
    )
    live_classes = LiveClass.objects.filter(starts_at__gte=timezone.now())
    if not is_admin_view:
        live_classes = live_classes.filter(course__enrollment__student=student)
    live_classes = live_classes.select_related('course__teacher__user')
    graded_submissions = (
        student.submissions.filter(score__isnull=False).select_related('assignment')
        if student else Submission.objects.none()
    )
    progress = None
    if graded_submissions.exists():
        scores = list(graded_submissions)
        total_possible = sum(item.assignment.max_points for item in scores)
        if total_possible:
            progress = round(
                sum(item.score for item in scores) / total_possible * 100
            )

    return render(
        request,
        'students/dashboard.html',
        {
            'student': student,
            'is_admin_view': is_admin_view,
            'courses': courses,
            'assignments': assignments,
            'live_classes': live_classes,
            'progress': progress,
        },
    )


@role_required(User.Role.STUDENT)
def course_list(request):
    student = _student_for_user(request.user)
    courses = Course.objects.none()
    resources = StudyResource.objects.none()
    if request.user.is_superuser:
        courses = Course.objects.select_related('teacher__user').prefetch_related('lessons')
        resources = StudyResource.objects.all()
    elif student is not None:
        courses = Course.objects.filter(
            enrollment__student=student
        ).select_related('teacher__user').prefetch_related('lessons').distinct()
        resources = StudyResource.objects.filter(
            Q(grade='') | Q(grade=student.grade)
        )
    return render(
        request,
        'students/course_list.html',
        {'courses': courses, 'resources': resources},
    )


@role_required(User.Role.STUDENT)
def submit_assignment(request, assignment_id):
    student = get_object_or_404(Student, user=request.user)
    assignment = get_object_or_404(
        Assignment.objects.filter(course__enrollment__student=student).select_related('course'),
        pk=assignment_id,
    )
    submission = Submission.objects.filter(
        assignment=assignment,
        student=student,
    ).first()
    form = SubmissionForm(request.POST or None, instance=submission)
    if request.method == 'POST' and form.is_valid():
        submission = form.save(commit=False)
        submission.assignment = assignment
        submission.student = student
        submission.save()
        messages.success(request, 'Your assignment response has been submitted.')
        return redirect('students:dashboard')
    return render(
        request,
        'courses/form.html',
        {
            'form': form,
            'title': f'Submit: {assignment.title}',
            'back_url': 'students:dashboard',
        },
    )
