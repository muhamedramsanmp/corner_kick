from django import forms
from .models import Address


class AddressForm(forms.ModelForm):

    class Meta:

        model = Address

        fields = [
            "full_name",
            "phone",
            "address_line",
            "city",
            "state",
            "pincode",
            "country",
            "address_type",
            "is_default",
        ]

        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "address_line": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "state": forms.TextInput(attrs={"class": "form-control"}),
            "pincode": forms.TextInput(attrs={"class": "form-control"}),
            "country": forms.TextInput(attrs={"class": "form-control"}),
            "address_type": forms.TextInput(attrs={"class": "form-control"}),
        }
