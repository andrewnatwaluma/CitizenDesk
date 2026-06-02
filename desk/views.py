from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.db import models
from django.db.models import Count, Q
from .models import Ministry, Report, Photo, Reaction, Comment, UserProfile
from .forms import ReportForm, SignUpForm, LoginForm, ProfileUpdateForm

def home(request):
    if request.user.is_authenticated and request.user.is_superuser:
        reports = Report.objects.all()
    elif request.user.is_authenticated:
        reports = Report.objects.filter(
            models.Q(privacy='PUBLIC') |
            models.Q(privacy='PRIVATE', citizen=request.user)
        ).filter(is_security_related=False)
    else:
        reports = Report.objects.filter(privacy='PUBLIC', is_security_related=False)

    ministry_id = request.GET.get('ministry')
    if ministry_id:
        reports = reports.filter(ministry_id=ministry_id)

    status = request.GET.get('status')
    if status:
        reports = reports.filter(status=status)

    reports = reports[:50]
    ministries = Ministry.objects.all()

    for report in reports:
        report.reaction_count = report.reactions.count()
        report.comment_count = report.comments.count()

    context = {
        'reports': reports,
        'ministries': ministries,
        'selected_ministry': ministry_id,
        'selected_status': status,
    }
    return render(request, 'desk/home.html', context)

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome {user.first_name}! You are now signed up.')
            return redirect('home')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = SignUpForm()

    return render(request, 'desk/signup.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            email_or_phone = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            
            # Try to find user by email first
            user = None
            try:
                user = User.objects.get(email=email_or_phone)
            except User.DoesNotExist:
                # If not found by email, try by phone number
                try:
                    profile = UserProfile.objects.get(phone_number=email_or_phone)
                    user = profile.user
                except UserProfile.DoesNotExist:
                    pass
            
            if user is not None:
                user = authenticate(username=user.username, password=password)
                if user is not None:
                    login(request, user)
                    messages.success(request, f'Welcome back {user.username}!')
                    next_url = request.GET.get('next', 'home')
                    return redirect(next_url)
            
            messages.error(request, 'Invalid email/phone or password.')
        else:
            messages.error(request, 'Invalid email/phone or password.')
    else:
        form = LoginForm()
    
    return render(request, 'desk/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('home')

def ministry_login_view(request):
    if request.method == 'POST':
        ministry_name = request.POST.get('ministry_name')
        password = request.POST.get('password')

        try:
            ministry = Ministry.objects.get(name__iexact=ministry_name)
            if ministry.check_password(password):
                request.session['ministry_id'] = ministry.id
                request.session['ministry_name'] = ministry.name
                messages.success(request, f'Welcome {ministry.name}! You are now logged in as ministry.')
                return redirect('ministry_dashboard')
            else:
                messages.error(request, 'Invalid password.')
        except Ministry.DoesNotExist:
            messages.error(request, 'Ministry not found.')

    return render(request, 'desk/ministry_login.html')

def ministry_logout_view(request):
    if 'ministry_id' in request.session:
        del request.session['ministry_id']
        del request.session['ministry_name']
    messages.success(request, 'Ministry logged out successfully.')
    return redirect('home')

@login_required
def profile_view(request):
    user_reports = Report.objects.filter(citizen=request.user).order_by('-created_at')
    user_comments = Comment.objects.filter(citizen=request.user).order_by('-created_at')
    user_reactions = Reaction.objects.filter(citizen=request.user).order_by('-created_at')

    profile, created = UserProfile.objects.get_or_create(user=request.user)

    context = {
        'user_reports': user_reports,
        'user_comments': user_comments,
        'user_reactions': user_reactions,
        'profile': profile,
    }
    return render(request, 'desk/profile.html', context)

@login_required
def profile_update_view(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=request.user, user=request.user)

    return render(request, 'desk/profile_update.html', {'form': form})

def public_profile_view(request, user_id):
    citizen = get_object_or_404(User, id=user_id)
    user_reports = Report.objects.filter(citizen=citizen, is_security_related=False).order_by('-created_at')

    context = {
        'profile_user': citizen,
        'user_reports': user_reports,
    }
    return render(request, 'desk/public_profile.html', context)

@login_required
def submit_report(request):
    if request.method == 'POST':
        form = ReportForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(commit=False)
            report.citizen = request.user
            report.save()

            for i in range(1, 4):
                photo_field = f'photo{i}'
                if request.FILES.get(photo_field):
                    Photo.objects.create(
                        report=report,
                        image=request.FILES[photo_field]
                    )

            messages.success(request, f'Your report has been submitted! Tracking ID: #{report.id}')
            return redirect('report_detail', report_id=report.id)
    else:
        form = ReportForm()

    ministries = Ministry.objects.all()
    return render(request, 'desk/submit.html', {'form': form, 'ministries': ministries})

def report_detail(request, report_id):
    report = get_object_or_404(Report, id=report_id)

    if report.privacy == 'PRIVATE' and report.citizen != request.user and not request.user.is_staff and 'ministry_id' not in request.session:
        messages.error(request, 'This report is private.')
        return redirect('home')

    if report.is_security_related and not request.user.is_staff and 'ministry_id' not in request.session:
        messages.error(request, 'This report is confidential.')
        return redirect('home')

    if request.method == 'POST' and 'reaction' in request.POST and request.user.is_authenticated:
        reaction_type = request.POST.get('reaction')
        Reaction.objects.update_or_create(
            report=report,
            citizen=request.user,
            defaults={'reaction_type': reaction_type}
        )
        return redirect('report_detail', report_id=report.id)

    if request.method == 'POST' and 'comment_text' in request.POST:
        comment_text = request.POST.get('comment_text')
        parent_id = request.POST.get('parent_id')

        if comment_text:
            if report.is_comment_locked() and 'ministry_id' not in request.session:
                messages.error(request, 'This report is rejected. Only the ministry can comment on it.')
                return redirect('report_detail', report_id=report.id)

            parent = None
            if parent_id:
                parent = Comment.objects.filter(id=parent_id).first()

            is_ministry_comment = 'ministry_id' in request.session
            ministry = None
            citizen = None

            if is_ministry_comment:
                ministry_id = request.session.get('ministry_id')
                ministry = get_object_or_404(Ministry, id=ministry_id)
            elif request.user.is_authenticated:
                citizen = request.user
            else:
                messages.error(request, 'You must be logged in to comment.')
                return redirect('login')

            Comment.objects.create(
                report=report,
                citizen=citizen,
                ministry=ministry,
                text=comment_text,
                parent=parent,
                is_ministry_comment=is_ministry_comment
            )
            messages.success(request, 'Comment added!')
            return redirect('report_detail', report_id=report.id)

    reactions = {
        'ACKNOWLEDGED': report.reactions.filter(reaction_type='ACKNOWLEDGED').count(),
        'ESCALATED': report.reactions.filter(reaction_type='ESCALATED').count(),
        'RESOLVED': report.reactions.filter(reaction_type='RESOLVED').count(),
    }

    user_reaction = None
    if request.user.is_authenticated:
        user_reaction = report.reactions.filter(citizen=request.user).first()

    comments = report.comments.filter(parent__isnull=True)
    photos = report.photos.all()

    context = {
        'report': report,
        'photos': photos,
        'reactions': reactions,
        'user_reaction': user_reaction,
        'comments': comments,
    }
    return render(request, 'desk/detail.html', context)

@login_required
def add_reaction(request, report_id):
    if request.method == 'POST':
        report = get_object_or_404(Report, id=report_id)
        reaction_type = request.POST.get('reaction_type')
        reaction, created = Reaction.objects.update_or_create(
            report=report,
            citizen=request.user,
            defaults={'reaction_type': reaction_type}
        )
        return JsonResponse({'success': True, 'count': report.reactions.count()})
    return JsonResponse({'success': False})

def ministry_dashboard(request):
    if 'ministry_id' in request.session:
        ministry_id = request.session['ministry_id']
        try:
            ministry = Ministry.objects.get(id=ministry_id)
            reports = Report.objects.filter(ministry=ministry)
            ministries = Ministry.objects.filter(id=ministry_id)
            is_ministry_admin = True
        except Ministry.DoesNotExist:
            messages.error(request, 'Ministry session expired.')
            return redirect('ministry_login')
    elif request.user.is_authenticated and request.user.is_staff:
        reports = Report.objects.all()
        ministries = Ministry.objects.all()
        is_ministry_admin = False
    else:
        messages.error(request, 'Access denied. Ministry admin access only.')
        return redirect('ministry_login')

    ministry_id_filter = request.GET.get('ministry')
    if ministry_id_filter:
        reports = reports.filter(ministry_id=ministry_id_filter)

    status_filter = request.GET.get('status')
    if status_filter:
        reports = reports.filter(status=status_filter)

    context = {
        'reports': reports,
        'ministries': ministries,
        'selected_ministry': ministry_id_filter,
        'selected_status': status_filter,
        'status_choices': Report.STATUS_CHOICES,
        'is_ministry_admin': is_ministry_admin,
    }
    return render(request, 'desk/ministry_dashboard.html', context)

def update_status(request, report_id):
    report = get_object_or_404(Report, id=report_id)

    if 'ministry_id' in request.session:
        ministry_id = request.session['ministry_id']
        if report.ministry.id != ministry_id:
            messages.error(request, 'You do not have permission to update this report.')
            return redirect('ministry_dashboard')
    elif not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        admin_note = request.POST.get('admin_note', '')

        if new_status in dict(Report.STATUS_CHOICES):
            report.status = new_status
            if admin_note:
                report.admin_note = admin_note
            report.save()
            messages.success(request, f'Report #{report.id} status updated to {report.get_status_display()}')

    if 'ministry_id' in request.session:
        return redirect('ministry_dashboard')
    return redirect('admin_dashboard')
