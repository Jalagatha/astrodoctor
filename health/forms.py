import io
from datetime import date

from django import forms
from django.core.files.base import ContentFile
from PIL import Image, ImageOps

from .models import CrewMember


class CrewMemberForm(forms.ModelForm):
    class Meta:
        model = CrewMember
        fields = ["full_name", "call_sign", "role", "agency", "nationality", "mission", "status", "mission_start", "date_of_birth", "email", "biography", "photo"]
        labels = {"call_sign": "Call sign", "mission_start": "Mission start", "date_of_birth": "Date of birth", "email": "Contact email"}
        widgets = {
            "full_name": forms.TextInput(attrs={"placeholder": "e.g. Amina Okello", "data-live-source": "", "data-initials-source": ""}),
            "call_sign": forms.TextInput(attrs={"placeholder": "e.g. Orion", "data-live-source": ""}),
            "role": forms.TextInput(attrs={"placeholder": "e.g. Flight engineer", "data-live-source": ""}),
            "agency": forms.TextInput(attrs={"placeholder": "e.g. NASA, ESA, KARI"}),
            "nationality": forms.TextInput(attrs={"placeholder": "e.g. Kenyan"}),
            "mission": forms.TextInput(attrs={"placeholder": "e.g. Expedition 74"}),
            "status": forms.RadioSelect,
            "mission_start": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "date_of_birth": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "email": forms.EmailInput(attrs={"placeholder": "name@agency.org"}),
            "biography": forms.Textarea(attrs={"rows": 5, "placeholder": "Background, expertise and what they bring to the mission."}),
            "photo": forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
        }

    def clean_date_of_birth(self):
        value = self.cleaned_data["date_of_birth"]
        if value and value > date.today():
            raise forms.ValidationError("Date of birth cannot be in the future.")
        return value

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if not photo or not hasattr(photo, "content_type"):
            return photo
        if photo.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Choose a photo of 5 MB or smaller.")
        with Image.open(photo) as image:
            if image.format not in {"JPEG", "PNG", "WEBP"}:
                raise forms.ValidationError("Choose a JPEG, PNG, or WebP photo.")
            if image.width * image.height > 20_000_000:
                raise forms.ValidationError("Photo must be 20 megapixels or smaller.")
            image = ImageOps.exif_transpose(image).convert("RGB")
            image.thumbnail((800, 800))
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=88)
        return ContentFile(output.getvalue(), name="portrait.jpg")


class DeveloperForm(CrewMemberForm):
    class Meta:
        from .models import Developer

        model = Developer
        fields = ["full_name", "role", "biography", "email", "github", "website", "photo"]
        labels = {"github": "GitHub profile", "email": "Email"}
        widgets = {
            "full_name": forms.TextInput(attrs={"placeholder": "e.g. Ada Lovelace", "data-live-source": "", "data-initials-source": ""}),
            "role": forms.TextInput(attrs={"placeholder": "e.g. Machine-learning engineer", "data-live-source": ""}),
            "email": forms.EmailInput(attrs={"placeholder": "name@example.org"}),
            "github": forms.URLInput(attrs={"placeholder": "https://github.com/username"}),
            "website": forms.URLInput(attrs={"placeholder": "https://…"}),
            "biography": forms.Textarea(attrs={"rows": 5, "placeholder": "What they built for Astro-Doctor and what they care about."}),
            "photo": forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
        }

    def clean(self):
        data = super().clean()
        for field in ("github", "website"):
            value = data.get(field)
            if value and not value.lower().startswith(("http://", "https://")):
                self.add_error(field, "Use an HTTP or HTTPS link.")
        return data


class UserProfileForm(CrewMemberForm):
    class Meta:
        from .models import UserProfile

        model = UserProfile
        fields = ["display_name", "job_title", "biography", "photo"]
        labels = {"display_name": "Display name", "job_title": "Role or title", "biography": "Short bio"}
        widgets = {
            "display_name": forms.TextInput(attrs={"placeholder": "What should we call you?", "autocomplete": "nickname", "data-live-source": "", "data-initials-source": ""}),
            "job_title": forms.TextInput(attrs={"placeholder": "e.g. Flight engineer", "data-live-source": ""}),
            "biography": forms.Textarea(attrs={"rows": 5, "placeholder": "A few words about you, your mission or what helps you recharge."}),
            "photo": forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
        }
