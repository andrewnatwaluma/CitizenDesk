from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django import forms
from .models import Ministry, Report, Photo, Reaction, Comment, UserProfile

class MinistryForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(),
        required=False,
        help_text="Set or change ministry password"
    )
    
    class Meta:
        model = Ministry
        fields = ['name', 'description', 'password']
    
    def save(self, commit=True):
        ministry = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            ministry.set_password(password)
        if commit:
            ministry.save()
        return ministry

@admin.register(Ministry)
class MinistryAdmin(admin.ModelAdmin):
    form = MinistryForm
    list_display = ['name', 'created_at', 'has_password']
    search_fields = ['name']
    ordering = ['name']
    fields = ['name', 'description', 'password']
    
    def has_password(self, obj):
        return bool(obj.password)
    has_password.boolean = True
    has_password.short_description = 'Has Password'

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'

class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff']

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

class PhotoInline(admin.TabularInline):
    model = Photo
    extra = 1
    max_num = 3

class ReactionInline(admin.TabularInline):
    model = Reaction
    extra = 0
    readonly_fields = ['citizen', 'reaction_type', 'created_at']

class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ['citizen', 'ministry', 'text', 'created_at']

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'ministry', 'citizen', 'status_colored', 'privacy', 'created_at']
    list_filter = ['status', 'ministry', 'privacy', 'is_security_related']
    search_fields = ['title', 'description', 'location', 'citizen__username']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [PhotoInline, ReactionInline, CommentInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'location', 'ministry', 'citizen')
        }),
        ('Privacy & Status', {
            'fields': ('privacy', 'status', 'admin_note'),
            'classes': ('wide',)
        }),
        ('Security', {
            'fields': ('is_security_related',),
            'classes': ('collapse',)
        }),
        ('Location Data', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_colored(self, obj):
        colors = {
            'RECEIVED': 'gray',
            'REVIEW': 'orange',
            'IN_PROGRESS': 'blue',
            'RESOLVED': 'green',
            'REJECTED': 'red',
        }
        color = colors.get(obj.status, 'gray')
        status_display = obj.get_status_display()
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, status_display)
    status_colored.short_description = 'Status'
    
    actions = ['mark_resolved', 'mark_rejected']
    
    def mark_resolved(self, request, queryset):
        queryset.update(status='RESOLVED')
    mark_resolved.short_description = 'Mark selected as Resolved'
    
    def mark_rejected(self, request, queryset):
        queryset.update(status='REJECTED')
    mark_rejected.short_description = 'Mark selected as Rejected'

@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ['report', 'image_tag', 'uploaded_at']
    readonly_fields = ['image_tag']
    
    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" height="100" style="object-fit: cover;" />', obj.image.url)
        return '-'
    image_tag.short_description = 'Preview'

@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ['report', 'citizen', 'reaction_type', 'created_at']
    list_filter = ['reaction_type']
    readonly_fields = ['created_at']

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['report', 'get_author', 'text_preview', 'created_at', 'is_ministry_comment']
    list_filter = ['is_ministry_comment', 'created_at']
    search_fields = ['text']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_author(self, obj):
        if obj.is_ministry_comment and obj.ministry:
            return f"🏛️ {obj.ministry.name}"
        return obj.citizen.username if obj.citizen else 'Unknown'
    get_author.short_description = 'Author'
    
    def text_preview(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = 'Comment'
