from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password

class Ministry(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    password = models.CharField(max_length=128, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    def set_password(self, raw_password):
        self.password = make_password(raw_password)
    
    def check_password(self, raw_password):
        if not self.password:
            return False
        return check_password(raw_password, self.password)
    
    class Meta:
        ordering = ['name']

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Emoji or icon code (e.g., 🚗, 💡, 💧)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.icon} {self.name}" if self.icon else self.name
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

class Report(models.Model):
    STATUS_CHOICES = [
        ('RECEIVED', '📋 Received'),
        ('REVIEW', '🔍 Under Review'),
        ('IN_PROGRESS', '🔄 In Progress'),
        ('RESOLVED', '✅ Resolved'),
        ('REJECTED', '❌ Rejected'),
    ]
    
    PRIVACY_CHOICES = [
        ('PUBLIC', '🌍 Public - Everyone can see'),
        ('PRIVATE', '🔒 Private - Only ministry admin can see'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=300)
    
    ministry = models.ForeignKey(Ministry, on_delete=models.CASCADE, related_name='reports')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='reports')
    citizen = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='RECEIVED')
    status_updated_at = models.DateTimeField(auto_now=True)
    
    privacy = models.CharField(max_length=10, choices=PRIVACY_CHOICES, default='PUBLIC')
    is_security_related = models.BooleanField(default=False)
    
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    admin_note = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.title} - {self.citizen.username}"
    
    def get_status_color(self):
        colors = {
            'RECEIVED': 'gray',
            'REVIEW': 'yellow',
            'IN_PROGRESS': 'blue',
            'RESOLVED': 'green',
            'REJECTED': 'red',
        }
        return colors.get(self.status, 'gray')
    
    def is_comment_locked(self):
        return self.status == 'REJECTED'
    
    class Meta:
        ordering = ['-created_at']

class Photo(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='report_photos/%Y/%m/%d/')
    caption = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Photo for {self.report.title}"

class Reaction(models.Model):
    REACTION_TYPES = [
        ('ACKNOWLEDGED', '✅ Acknowledged'),
        ('ESCALATED', '⚠️ Escalated'),
        ('RESOLVED', '✔️ Resolved'),
    ]
    
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='reactions')
    citizen = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reactions')
    reaction_type = models.CharField(max_length=15, choices=REACTION_TYPES, default='ACKNOWLEDGED')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['report', 'citizen']
    
    def __str__(self):
        return f"{self.citizen.username} - {self.reaction_type}"

class Comment(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='comments')
    citizen = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments', null=True, blank=True)
    ministry = models.ForeignKey(Ministry, on_delete=models.CASCADE, related_name='comments', null=True, blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    text = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_ministry_comment = models.BooleanField(default=False)
    
    def __str__(self):
        if self.is_ministry_comment and self.ministry:
            return f"Ministry {self.ministry.name}: {self.text[:50]}"
        return f"Comment by {self.citizen.username if self.citizen else 'Unknown'}"
    
    class Meta:
        ordering = ['-is_ministry_comment', 'created_at']

class UserProfile(models.Model):
    SEX_CHOICES = [
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
        ('OTHER', 'Other'),
        ('PREFER_NOT_TO_SAY', 'Prefer not to say'),
    ]
    
    REGION_CHOICES = [
        ('CENTRAL', 'Central'),
        ('EASTERN', 'Eastern'),
        ('NORTHERN', 'Northern'),
        ('WESTERN', 'Western'),
        ('KAMPALA', 'Kampala'),
        ('OTHER', 'Other'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=15, unique=True, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/%Y/%m/%d/', blank=True, null=True)
    
    # Demographic fields
    date_of_birth = models.DateField(null=True, blank=True)
    sex = models.CharField(max_length=20, choices=SEX_CHOICES, blank=True, null=True)
    region_of_origin = models.CharField(max_length=20, choices=REGION_CHOICES, blank=True, null=True)
    region_of_residence = models.CharField(max_length=20, choices=REGION_CHOICES, blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.phone_number or 'no phone'}"
    
    def get_profile_picture_url(self):
        if self.profile_picture:
            return self.profile_picture.url
        return None
    
    def get_age(self):
        if self.date_of_birth:
            today = timezone.now().date()
            return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        return None
