from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from courses.models import Course, FeeRecord, Submission
from students.models import Student

from .decorators import role_required
from .forms import MessageForm, PortalUserCreationForm
from .models import Message, Parent, User


@login_required
def dashboard_redirect(request):
    if request.user.is_superuser:
        return redirect('accounts:admin_dashboard')
    destinations = {
        User.Role.STUDENT: 'students:dashboard',
        User.Role.TEACHER: 'teachers:dashboard',
        User.Role.PARENT: 'accounts:parent_dashboard',
    }
    return redirect(destinations.get(request.user.role, 'accounts:login'))


@role_required(User.Role.PARENT)
def parent_dashboard(request):
    parent = get_object_or_404(Parent, user=request.user)
    children = parent.children.select_related('user').prefetch_related(
        'enrollment_set__course__teacher__user',
        'fee_records',
        'submissions__assignment__course',
    )
    return render(request, 'accounts/parent_dashboard.html', {'children': children})


@login_required
def admin_dashboard(request):
    if not request.user.is_superuser:
        raise PermissionDenied

    form = PortalUserCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Account created successfully.')
        return redirect('accounts:admin_dashboard')

    context = {
        'form': form,
        'user_count': User.objects.count(),
        'student_count': User.objects.filter(role=User.Role.STUDENT).count(),
        'teacher_count': User.objects.filter(role=User.Role.TEACHER).count(),
        'parent_count': User.objects.filter(role=User.Role.PARENT).count(),
        'course_count': Course.objects.count(),
        'submission_count': Submission.objects.filter(score__isnull=True).count(),
        'fees_due': FeeRecord.objects.filter(status=FeeRecord.Status.DUE).count(),
    }
    return render(request, 'accounts/admin_dashboard.html', context)


@login_required
def messages_view(request):
    if request.user.is_superuser:
        recipients = User.objects.none()
    elif request.user.role == User.Role.TEACHER:
        student_user_ids = Student.objects.filter(
            enrollment__course__teacher__user=request.user
        ).values_list('user_id', flat=True)
        parent_user_ids = Parent.objects.filter(
            children__user_id__in=student_user_ids
        ).values_list('user_id', flat=True)
        recipients = User.objects.filter(
            Q(pk__in=student_user_ids) | Q(pk__in=parent_user_ids),
            is_active=True,
        ).order_by('username')
    elif request.user.role in (User.Role.STUDENT, User.Role.PARENT):
        student_ids = (
            get_object_or_404(Parent, user=request.user).children.values_list('id', flat=True)
            if request.user.role == User.Role.PARENT
            else Student.objects.filter(user=request.user).values_list('id', flat=True)
        )
        recipients = User.objects.filter(
            teacher__course__enrollment__student_id__in=student_ids,
            is_active=True,
        ).distinct().order_by('username')
    else:
        raise PermissionDenied

    form = MessageForm(request.POST or None, recipients=recipients)
    if request.method == 'POST' and form.is_valid():
        message = form.save(commit=False)
        message.sender = request.user
        message.save()
        messages.success(request, 'Your message has been sent.')
        return redirect('accounts:messages')

    incoming = Message.objects.filter(recipient=request.user).select_related('sender')
    outgoing = Message.objects.filter(sender=request.user).select_related('recipient')
    incoming.filter(is_read=False).update(is_read=True)
    return render(
        request,
        'accounts/messages.html',
        {'form': form, 'incoming': incoming, 'outgoing': outgoing},
    )
