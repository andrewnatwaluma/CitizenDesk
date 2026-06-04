from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.db import models
from django.db.models import Count, Q
from datetime import datetime, timedelta
from .models import Ministry, Report, Photo, Reaction, Comment, UserProfile, LoginAttempt
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
    
    # Get client IP address
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip_address = x_forwarded_for.split(',')[0]
    else:
        ip_address = request.META.get('REMOTE_ADDR')
    
    if request.method == 'POST':
        email_or_phone = request.POST.get('username')
        password = request.POST.get('password')
        
        # Check if IP is locked out
        try:
            attempt = LoginAttempt.objects.get(ip_address=ip_address, username=email_or_phone)
            if attempt.locked_until and attempt.locked_until > datetime.now():
                remaining = (attempt.locked_until - datetime.now()).seconds // 60
                messages.error(request, f'Too many failed attempts. Try again in {remaining} minutes.')
                return render(request, 'desk/login.html', {'form': LoginForm()})
        except LoginAttempt.DoesNotExist:
            pass
        
        print(f"DEBUG: Attempting login with: {email_or_phone}")
        
        user = None
        try:
            user = User.objects.get(email=email_or_phone)
            print(f"DEBUG: Found by email: {user.username}")
        except User.DoesNotExist:
            print(f"DEBUG: No user found by email: {email_or_phone}")
            try:
                profile = UserProfile.objects.get(phone_number=email_or_phone)
                user = profile.user
                print(f"DEBUG: Found by phone: {user.username}")
            except UserProfile.DoesNotExist:
                print(f"DEBUG: No user found by phone: {email_or_phone}")
                try:
                    user = User.objects.get(username=email_or_phone)
                    print(f"DEBUG: Found by username: {user.username}")
                except User.DoesNotExist:
                    print(f"DEBUG: No user found at all for: {email_or_phone}")
        
        if user is not None:
            print(f"DEBUG: Attempting authenticate for: {user.username}")
            auth_user = authenticate(username=user.username, password=password)
            if auth_user is not None:
                login(request, auth_user)
                print(f"DEBUG: Login successful for: {user.username}")
                messages.success(request, f'Welcome back {user.username}!')
                # Clear any failed attempts on successful login
                LoginAttempt.objects.filter(ip_address=ip_address, username=email_or_phone).delete()
                next_url = request.GET.get('next', 'home')
                return redirect(next_url)
            else:
                print(f"DEBUG: Authentication FAILED for: {user.username}")
                # Record failed attempt
                attempt, created = LoginAttempt.objects.get_or_create(
                    ip_address=ip_address,
                    username=email_or_phone
                )
                attempt.attempts += 1
                if attempt.attempts >= 5:
                    attempt.locked_until = datetime.now() + timedelta(minutes=15)
                attempt.save()
                messages.error(request, 'Invalid password.')
        else:
            print(f"DEBUG: No user object found")
            # Record failed attempt for non-existent user
            attempt, created = LoginAttempt.objects.get_or_create(
                ip_address=ip_address,
                username=email_or_phone
            )
            attempt.attempts += 1
            if attempt.attempts >= 5:
                attempt.locked_until = datetime.now() + timedelta(minutes=15)
            attempt.save()
            messages.error(request, 'No account found with that email/phone number.')
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
    
    # Increment view count
    report.views += 1
    report.save()

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

    demographic_data = {}
    if is_ministry_admin:
        gender_counts = {
            'Male': UserProfile.objects.filter(sex='MALE').count(),
            'Female': UserProfile.objects.filter(sex='FEMALE').count(),
            'Other': UserProfile.objects.filter(sex='OTHER').count(),
            'Prefer not to say': UserProfile.objects.filter(sex='PREFER_NOT_TO_SAY').count(),
        }
        region_counts = {}
        for region_code, region_name in UserProfile.REGION_CHOICES:
            count = UserProfile.objects.filter(region_of_residence=region_code).count()
            if count > 0:
                region_counts[region_name] = count
        
        status_counts = {}
        for status_code, status_label in Report.STATUS_CHOICES:
            count = reports.filter(status=status_code).count()
            if count > 0:
                clean_label = status_label.replace('📋 ', '').replace('✅ ', '').replace('❌ ', '').replace('🔍 ', '').replace('🔄 ', '').strip()
                status_counts[clean_label] = count
        
        date_counts = []
        for i in range(30):
            date = datetime.now().date() - timedelta(days=i)
            count = reports.filter(created_at__date=date).count()
            if count > 0 or i < 7:
                date_counts.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'count': count
                })
        
        demographic_data = {
            'gender_counts': gender_counts,
            'region_counts': region_counts,
            'status_counts': status_counts,
            'date_counts': date_counts[::-1],
            'total_reports': reports.count(),
        }

    context = {
        'reports': reports,
        'ministries': ministries,
        'selected_ministry': ministry_id_filter,
        'selected_status': status_filter,
        'status_choices': Report.STATUS_CHOICES,
        'is_ministry_admin': is_ministry_admin,
        'demographic_data': demographic_data,
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

def statistics_dashboard(request):
    """Display statistics - accessible to ministry sessions and staff"""
    from .models import Category
    
    if 'ministry_id' in request.session:
        ministry_id = request.session['ministry_id']
        try:
            ministry = Ministry.objects.get(id=ministry_id)
            reports = Report.objects.filter(ministry=ministry)
            is_ministry_admin = True
        except Ministry.DoesNotExist:
            messages.error(request, 'Ministry session expired.')
            return redirect('ministry_login')
    elif request.user.is_authenticated and request.user.is_staff:
        reports = Report.objects.all()
        is_ministry_admin = False
        ministry = None
    else:
        messages.error(request, 'Access denied. Please login as ministry or admin.')
        return redirect('ministry_login')
    
    total_reports = reports.count()
    
    status_counts = {}
    for status_code, status_label in Report.STATUS_CHOICES:
        count = reports.filter(status=status_code).count()
        if count > 0:
            clean_label = status_label.replace('📋 ', '').replace('✅ ', '').replace('❌ ', '').replace('🔍 ', '').replace('🔄 ', '').strip()
            status_counts[clean_label] = count
    
    category_counts = {}
    for category in Category.objects.filter(is_active=True):
        count = reports.filter(category=category).count()
        if count > 0:
            category_counts[category.name] = count
    
    ministry_counts = {}
    for ministry_obj in Ministry.objects.all():
        count = reports.filter(ministry=ministry_obj).count()
        if count > 0:
            ministry_counts[ministry_obj.name] = count
    
    region_counts = {}
    for region_code, region_name in UserProfile.REGION_CHOICES:
        count = UserProfile.objects.filter(region_of_residence=region_code).count()
        if count > 0:
            region_counts[region_name] = count
    
    date_counts = []
    for i in range(30):
        date = datetime.now().date() - timedelta(days=i)
        count = reports.filter(created_at__date=date).count()
        if count > 0 or i < 7:
            date_counts.append({
                'date': date.strftime('%Y-%m-%d'),
                'count': count
            })
    
    context = {
        'total_reports': total_reports,
        'status_counts': status_counts,
        'category_counts': category_counts,
        'ministry_counts': ministry_counts,
        'region_counts': region_counts,
        'date_counts': date_counts[::-1],
        'is_ministry_admin': is_ministry_admin,
    }
    return render(request, 'desk/statistics.html', context)

def map_view(request):
    """Display map with heat signatures of reports - accessible to ministry sessions and staff"""
    if 'ministry_id' in request.session:
        ministry_id = request.session['ministry_id']
        try:
            ministry = Ministry.objects.get(id=ministry_id)
            reports = Report.objects.filter(ministry=ministry, latitude__isnull=False, longitude__isnull=False)
            is_ministry_admin = True
        except Ministry.DoesNotExist:
            messages.error(request, 'Ministry session expired.')
            return redirect('ministry_login')
    elif request.user.is_authenticated and request.user.is_staff:
        reports = Report.objects.filter(latitude__isnull=False, longitude__isnull=False)
        is_ministry_admin = False
        ministry = None
    else:
        messages.error(request, 'Access denied. Please login as ministry or admin.')
        return redirect('ministry_login')
    
    heatmap_data = []
    for report in reports:
        heatmap_data.append({
            'lat': float(report.latitude),
            'lng': float(report.longitude),
            'intensity': 1,
            'title': report.title,
            'id': report.id,
            'status': report.get_status_display(),
            'created_at': report.created_at.strftime('%Y-%m-%d'),
        })
    
    context = {
        'heatmap_data': heatmap_data,
        'is_ministry_admin': is_ministry_admin,
        'ministry': ministry,
        'total_reports': reports.count(),
    }
    return render(request, 'desk/map_view.html', context)

def demographics_view(request):
    """Display demographics - accessible to ministry sessions and staff"""
    if 'ministry_id' in request.session:
        ministry_id = request.session['ministry_id']
        try:
            ministry = Ministry.objects.get(id=ministry_id)
            reports = Report.objects.filter(ministry=ministry)
            is_ministry_admin = True
        except Ministry.DoesNotExist:
            messages.error(request, 'Ministry session expired.')
            return redirect('ministry_login')
    elif request.user.is_authenticated and request.user.is_staff:
        reports = Report.objects.all()
        is_ministry_admin = False
        ministry = None
    else:
        messages.error(request, 'Access denied. Please login as ministry or admin.')
        return redirect('ministry_login')
    
    total_reports = reports.count()
    
    gender_counts = {
        'Male': UserProfile.objects.filter(sex='MALE').count(),
        'Female': UserProfile.objects.filter(sex='FEMALE').count(),
        'Other': UserProfile.objects.filter(sex='OTHER').count(),
        'Prefer not to say': UserProfile.objects.filter(sex='PREFER_NOT_TO_SAY').count(),
    }
    
    region_counts = {}
    for region_code, region_name in UserProfile.REGION_CHOICES:
        count = UserProfile.objects.filter(region_of_residence=region_code).count()
        if count > 0:
            region_counts[region_name] = count
    
    age_ranges = {
        'Under 18': 0,
        '18-25': 0,
        '26-35': 0,
        '36-50': 0,
        '50+': 0,
    }
    for profile in UserProfile.objects.all():
        age = profile.get_age()
        if age:
            if age < 18:
                age_ranges['Under 18'] += 1
            elif age <= 25:
                age_ranges['18-25'] += 1
            elif age <= 35:
                age_ranges['26-35'] += 1
            elif age <= 50:
                age_ranges['36-50'] += 1
            else:
                age_ranges['50+'] += 1
    
    context = {
        'total_reports': total_reports,
        'gender_counts': gender_counts,
        'region_counts': region_counts,
        'age_ranges': age_ranges,
        'is_ministry_admin': is_ministry_admin,
    }
    return render(request, 'desk/demographics.html', context)
