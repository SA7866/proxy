from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

INPUT_CLASS = "input-field"

class CheckoutForm(forms.Form):
    #add widgets so the inputs look good + have placeholders
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
    Simple signup form. Uses Django's built-in password rules + hashing.
    """
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={"class": INPUT_CLASS, "placeholder": "Email"}))

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
        widgets = {
            "username": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "Username"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make password inputs match your styling
        self.fields["password1"].widget.attrs.update({"class": INPUT_CLASS, "placeholder": "Password"})
        self.fields["password2"].widget.attrs.update({"class": INPUT_CLASS, "placeholder": "Confirm password"})