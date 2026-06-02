from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import Report, Photo, UserProfile

class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        'class': 'w-full px-3 py-2 md:px-4 md:py-2 text-sm md:text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500',
        'placeholder': 'your@email.com'
    }))
    phone_number = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={
        'class': 'w-full px-3 py-2 md:px-4 md:py-2 text-sm md:text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500',
        'placeholder': '07XX XXX XXX (optional)'
    }))
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={
        'class': 'w-full px-3 py-2 md:px-4 md:py-2 text-sm md:text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500',
        'placeholder': 'First name'
    }))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={
        'class': 'w-full px-3 py-2 md:px-4 md:py-2 text-sm md:text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500',
        'placeholder': 'Last name'
    }))

    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 md:px-4 md:py-2 text-sm md:text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500',
            'placeholder': 'Enter password (any length, any characters)'
        }),
    )
    password2 = forms.CharField(
        label="Confirm Password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 md:px-4 md:py-2 text-sm md:text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500',
            'placeholder': 'Confirm your password'
        }),
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'password1', 'password2']
        # Username removed - will be auto-generated

    def generate_username_suggestions(self, first_name, last_name):
        """Generate available username suggestions"""
        import random
        base_username = f"{first_name.lower()}.{last_name.lower()}".replace(" ", "")
        suggestions = []
        
        # Check if base username is available
        if not User.objects.filter(username=base_username).exists():
            suggestions.append(base_username)
        
        # Try with numbers
        for i in range(1, 10):
            candidate = f"{base_username}{i}"
            if not User.objects.filter(username=candidate).exists():
                suggestions.append(candidate)
            if len(suggestions) >= 3:
                break
        
        # If still not enough suggestions, add random numbers
        while len(suggestions) < 3:
            candidate = f"{base_username}{random.randint(10, 999)}"
            if not User.objects.filter(username=candidate).exists():
                suggestions.append(candidate)
        
        return suggestions[:3]

    def clean(self):
        cleaned_data = super().clean()
        first_name = cleaned_data.get('first_name')
        last_name = cleaned_data.get('last_name')
        
        if first_name and last_name:
            suggestions = self.generate_username_suggestions(first_name, last_name)
            # Store suggestions in form for template access
            self.username_suggestions = suggestions
            # Auto-select the first available suggestion
            cleaned_data['username'] = suggestions[0]
        
        return cleaned_data

    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        if not password1:
            raise forms.ValidationError("Password cannot be empty")
        return password1

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def _post_clean(self):
        super(UserCreationForm, self)._post_clean()

    def save(self, commit=True):
        user = super(UserCreationForm, self).save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.username = self.cleaned_data.get('username')
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.phone_number = self.cleaned_data['phone_number']
            profile.save()
        return user

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Email or Phone Number",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 md:px-4 md:py-2 text-sm md:text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500',
            'placeholder': 'Email or Phone Number'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 md:px-4 md:py-2 text-sm md:text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500',
            'placeholder': 'Password'
        })
    )

class ReportForm(forms.ModelForm):
    photo1 = forms.ImageField(required=False, label='Photo 1', widget=forms.FileInput(attrs={
        'class': 'w-full text-sm text-gray-500 file:mr-2 file:py-1 file:px-3 md:file:mr-4 md:file:py-2 md:file:px-4 file:rounded-lg file:border-0 file:text-sm file:bg-yellow-50 file:text-yellow-700 hover:file:bg-yellow-100'
    }))
    photo2 = forms.ImageField(required=False, label='Photo 2', widget=forms.FileInput(attrs={
        'class': 'w-full text-sm text-gray-500 file:mr-2 file:py-1 file:px-3 md:file:mr-4 md:file:py-2 md:file:px-4 file:rounded-lg file:border-0 file:text-sm file:bg-yellow-50 file:text-yellow-700 hover:file:bg-yellow-100'
    }))
    photo3 = forms.ImageField(required=False, label='Photo 3', widget=forms.FileInput(attrs={
        'class': 'w-full text-sm text-gray-500 file:mr-2 file:py-1 file:px-3 md:file:mr-4 md:file:py-2 md:file:px-4 file:rounded-lg file:border-0 file:text-sm file:bg-yellow-50 file:text-yellow-700 hover:file:bg-yellow-100'
    }))

    class Meta:
        model = Report
        fields = ['title', 'description', 'location', 'ministry', 'privacy', 'latitude', 'longitude']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 md:px-4 md:py-2 text-sm md:text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500',
                'placeholder': 'Brief title of your report/request'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 md:px-4 md:py-2 text-sm md:text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500',
                'rows': 4,
                'placeholder': 'Describe the issue or request in detail...'
            }),
            'location': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 md:px-4 md:py-2 text-sm md:text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500',
                'placeholder': 'e.g., Kampala, Namuwongo near the mosque'
            }),
            'ministry': forms.Select(attrs={
                'class': 'w-full px-3 py-2 md:px-4 md:py-2 text-sm md:text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500'
            }),
            'privacy': forms.Select(attrs={
                'class': 'w-full px-3 py-2 md:px-4 md:py-2 text-sm md:text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500'
            }),
            'latitude': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 md:px-4 md:py-2 text-sm md:text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500',
                'placeholder': '0.0000000',
                'step': '0.0000001',
                'id': 'latitude'
            }),
            'longitude': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 md:px-4 md:py-2 text-sm md:text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500',
                'placeholder': '0.0000000',
                'step': '0.0000001',
                'id': 'longitude'
            }),
        }
        labels = {
            'title': 'Title',
            'description': 'Description',
            'location': 'Location Description',
            'ministry': 'Select Ministry',
            'privacy': 'Who can see this report?',
            'latitude': 'GPS Latitude',
            'longitude': 'GPS Longitude',
        }

class ProfileUpdateForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={
        'class': 'w-full px-3 py-2 md:px-4 md:py-2 text-sm md:text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500'
    }))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={
        'class': 'w-full px-3 py-2 md:px-4 md:py-2 text-sm md:text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500'
    }))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        'class': 'w-full px-3 py-2 md:px-4 md:py-2 text-sm md:text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500'
    }))
    phone_number = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={
        'class': 'w-full px-3 py-2 md:px-4 md:py-2 text-sm md:text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500',
        'placeholder': '07XX XXX XXX'
    }))
    profile_picture = forms.ImageField(required=False, widget=forms.FileInput(attrs={
        'class': 'w-full text-sm text-gray-500 file:mr-2 file:py-1 file:px-3 md:file:mr-4 md:file:py-2 md:file:px-4 file:rounded-lg file:border-0 file:text-sm file:bg-yellow-50 file:text-yellow-700 hover:file:bg-yellow-100'
    }))

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user and hasattr(self.user, 'profile'):
            self.fields['phone_number'].initial = self.user.profile.phone_number

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.phone_number = self.cleaned_data.get('phone_number')
            if self.cleaned_data.get('profile_picture'):
                profile.profile_picture = self.cleaned_data.get('profile_picture')
            profile.save()
        return user
