# forms.py
# Django Forms handle two things:
#   1. Rendering HTML inputs with the right attributes (placeholders, CSS classes)
#   2. Validating submitted data before it touches the database

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

# Shared CSS class applied to every input so they all look consistent
INPUT_CLASS = "input-field"


class CheckoutForm(forms.Form):
    """
    Collects delivery address at checkout.
    Django validates required fields and correct email format automatically.
    """
    full_name = forms.CharField(
        max_length=120,
        widget=forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "Full name"})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": INPUT_CLASS, "placeholder": "Email"})
    )
    address_line1 = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "Address line 1"})
    )
    city = forms.CharField(
        max_length=120,
        widget=forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "City"})
    )
    postcode = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "Postcode"})
    )
    country = forms.CharField(
        max_length=60,
        widget=forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "Country"})
    )


class RegisterForm(UserCreationForm):
    """
    Sign-up form that extends Django's built-in UserCreationForm.
    UserCreationForm already handles:
      - password confirmation (password1 == password2)
      - password strength rules
      - hashing the password before saving (never stored as plain text)
    We just add an email field and apply our CSS class to all inputs.
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"class": INPUT_CLASS, "placeholder": "Email"})
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
        widgets = {
            "username": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "Username"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply the shared CSS class to the password fields (defined by the parent form)
        self.fields["password1"].widget.attrs.update({"class": INPUT_CLASS, "placeholder": "Password"})
        self.fields["password2"].widget.attrs.update({"class": INPUT_CLASS, "placeholder": "Confirm password"})
