# apps/accounts/forms.py

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

from .models import ProducerProfile, CustomerProfile, CommunityGroupProfile, RestaurantProfile

User = get_user_model()


class LoginForm(AuthenticationForm):
    """Custom login form with email instead of username."""
    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password'
        })
    )


class ProducerRegistrationForm(forms.ModelForm):
    """
    Registration form for Producer accounts (TC-001).
    Collects user credentials and business information.
    """
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'jane.smith@bristolvalleyfarm.com'
        })
    )
    phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '01179 123456'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter a secure password'
        }),
        help_text='Minimum 8 characters'
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your password'
        }),
        label='Confirm Password'
    )
    business_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Bristol Valley Farm'
        })
    )
    contact_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Jane Smith'
        })
    )
    business_address = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Farm address'
        })
    )
    postcode = forms.CharField(
        max_length=10,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'BS1 4DJ'
        })
    )

    class Meta:
        model = User
        fields = ['email', 'phone']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('An account with this email already exists.')
        return email

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if len(password) < 8:
            raise ValidationError('Password must be at least 8 characters.')
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            raise ValidationError('Passwords do not match.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.role = User.Role.PRODUCER
        if commit:
            user.save()
            ProducerProfile.objects.create(
                user=user,
                business_name=self.cleaned_data['business_name'],
                contact_name=self.cleaned_data['contact_name'],
                business_address=self.cleaned_data['business_address'],
                postcode=self.cleaned_data['postcode']
            )
        return user


class CustomerRegistrationForm(forms.ModelForm):
    """
    Registration form for Customer accounts (TC-002).
    Collects user credentials and delivery address as separate fields.
    """
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'robert.johnson@email.com'
        })
    )
    phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '07700 900123'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter a secure password'
        }),
        help_text='Minimum 8 characters'
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your password'
        }),
        label='Confirm Password'
    )
    full_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Robert Johnson'
        })
    )
    street = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '45 Park Street'
        })
    )
    city = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Bristol'
        })
    )
    state = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'England'
        })
    )
    postcode = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'BS1 5JG'
        })
    )
    country = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'United Kingdom'
        })
    )
    terms_accepted = forms.BooleanField(
        required=True,
        label='I accept the terms and conditions'
    )

    class Meta:
        model = User
        fields = ['email', 'phone']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('An account with this email already exists.')
        return email

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if len(password) < 8:
            raise ValidationError('Password must be at least 8 characters.')
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            raise ValidationError('Passwords do not match.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.role = User.Role.CUSTOMER
        if commit:
            user.save()
            CustomerProfile.objects.create(
                user=user,
                full_name=self.cleaned_data['full_name'],
                street=self.cleaned_data['street'],
                city=self.cleaned_data['city'],
                state=self.cleaned_data['state'],
                postcode=self.cleaned_data['postcode'],
                country=self.cleaned_data['country'],
            )
        return user


class CommunityGroupRegistrationForm(forms.ModelForm):
    """
    Registration form for Community Group accounts (TC-017).
    """
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'group@email.com'
        })
    )
    phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '0117 900000'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter a secure password'
        }),
        help_text='Minimum 8 characters'
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your password'
        }),
        label='Confirm Password'
    )
    organisation_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Bristol Food Bank'
        })
    )
    organisation_address = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Organisation address'
        })
    )
    postcode = forms.CharField(
        max_length=10,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'BS1 2AB'
        })
    )

    class Meta:
        model = User
        fields = ['email', 'phone']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            raise ValidationError('Passwords do not match.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.role = User.Role.COMMUNITY_GROUP
        if commit:
            user.save()
            CommunityGroupProfile.objects.create(
                user=user,
                organisation_name=self.cleaned_data['organisation_name'],
                organisation_address=self.cleaned_data['organisation_address'],
                postcode=self.cleaned_data['postcode']
            )
        return user


class RestaurantRegistrationForm(forms.ModelForm):
    """
    Registration form for Independent Restaurant accounts (TC-018).
    """
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'info@restaurant.com'
        })
    )
    phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '0117 123456'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter a secure password'
        }),
        help_text='Minimum 8 characters'
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your password'
        }),
        label='Confirm Password'
    )
    restaurant_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'The Local Bistro'
        })
    )
    restaurant_address = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Restaurant address'
        })
    )
    postcode = forms.CharField(
        max_length=10,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'BS1 9XY'
        })
    )

    class Meta:
        model = User
        fields = ['email', 'phone']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            raise ValidationError('Passwords do not match.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.role = User.Role.RESTAURANT
        if commit:
            user.save()
            RestaurantProfile.objects.create(
                user=user,
                restaurant_name=self.cleaned_data['restaurant_name'],
                restaurant_address=self.cleaned_data['restaurant_address'],
                postcode=self.cleaned_data['postcode']
            )
        return user