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
        widgets = {
            "mission_start": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "date_of_birth": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "biography": forms.Textarea(attrs={"rows": 4}),
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
        widgets = {
            "biography": forms.Textarea(attrs={"rows": 4}),
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
        widgets = {
            "biography": forms.Textarea(attrs={"rows": 4}),
            "photo": forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
        }
