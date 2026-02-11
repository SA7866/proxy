from django import forms

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
