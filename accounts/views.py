from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from courses.forms import EnrollmentForm
from courses.models import Course, FeeRecord, LiveClass, Submission
from students.models import Student

from .decorators import role_required
from .forms import MessageForm, PortalUserCreationForm
from .models import Message, Parent, User


class PortalLoginView(auth_views.LoginView):
    template_name = 'accounts/login.html'

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['username'].widget.attrs['autocomplete'] = 'username'
        form.fields['password'].widget.attrs['autocomplete'] = 'current-password'
        return form

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.POST.get('remember_me'):
            self.request.session.set_expiry(30 * 24 * 60 * 60)
        else:
            self.request.session.set_expiry(0)
        return response


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
    if request.user.is_superuser:
        children = Student.objects.all()
    else:
        parent = get_object_or_404(Parent, user=request.user)
        children = parent.children.all()
    children = children.select_related('user').prefetch_related(
        'enrollment_set__course__teacher__user',
        'fee_records',
        'submissions__assignment__course',
    )
    return render(request, 'accounts/parent_dashboard.html', {'children': children})


@login_required
def admin_dashboard(request):
    if not request.user.is_superuser:
        raise PermissionDenied

    students = Student.objects.select_related('user').order_by('user__last_name', 'user__first_name')
    courses = Course.objects.select_related('teacher__user').order_by('subject', 'title')
    is_enrollment_post = request.method == 'POST' and request.POST.get('action') == 'enroll'
    form = PortalUserCreationForm(
        request.POST if request.method == 'POST' and not is_enrollment_post else None
    )
    enrollment_form = EnrollmentForm(
        request.POST if is_enrollment_post else None,
        courses=courses,
        students=students,
    )
    if request.method == 'POST' and is_enrollment_post and enrollment_form.is_valid():
        enrollment_form.save()
        messages.success(request, 'Student enrolled in the selected subject.')
        return redirect('accounts:admin_dashboard')
    if request.method == 'POST' and not is_enrollment_post and form.is_valid():
        form.save()
        messages.success(request, 'Account created successfully.')
        return redirect('accounts:admin_dashboard')

    context = {
        'form': form,
        'enrollment_form': enrollment_form,
        'user_count': User.objects.count(),
        'student_count': User.objects.filter(role=User.Role.STUDENT).count(),
        'teacher_count': User.objects.filter(role=User.Role.TEACHER).count(),
        'parent_count': User.objects.filter(role=User.Role.PARENT).count(),
        'course_count': Course.objects.count(),
        'live_class_count': LiveClass.objects.filter(
            starts_at__gte=timezone.now()
        ).count(),
        'upcoming_live_classes': LiveClass.objects.filter(
            starts_at__gte=timezone.now()
        ).select_related('course__teacher__user')[:5],
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
