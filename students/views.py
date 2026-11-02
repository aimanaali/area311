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
    if student is None:
        messages.warning(request, 'Your student profile has not been set up yet.')
        return render(request, 'students/dashboard.html', {'student': None})

    courses = Course.objects.filter(enrollment__student=student).select_related(
        'teacher__user'
    ).distinct()
    assignments = Assignment.objects.filter(
        course__enrollment__student=student
    ).select_related('course').prefetch_related(
        Prefetch(
            'submissions',
            queryset=Submission.objects.filter(student=student),
            to_attr='student_submissions',
        )
    )
    live_classes = LiveClass.objects.filter(
        course__enrollment__student=student,
        starts_at__gte=timezone.now(),
    ).select_related('course')
    graded_submissions = student.submissions.filter(
        score__isnull=False
    ).select_related('assignment')
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
    if student is not None:
        courses = Course.objects.filter(
            enrollment__student=student
        ).select_related('teacher__user').prefetch_related('lessons').distinct()
        resources = StudyResource.objects.filter(
            Q(grade='') | Q(grade=student.grade)
        )
    return render(
        request,
        'students/courselist.html',
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
