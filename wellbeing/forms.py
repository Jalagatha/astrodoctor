from django import forms

from .catalog import DURATION_CHOICES, SCALES, SCENE_KEYS, TIME_BLOCKS, blocked_reason
from .models import VRSession, WellbeingCheckIn


def scale_field(name, required=True):
    label, words = SCALES[name]
    return forms.TypedChoiceField(
        label=label, coerce=int, required=required, widget=forms.RadioSelect,
        choices=[(value, f"{value} · {word}") for value, word in enumerate(words, start=1)],
    )


class CheckInForm(forms.ModelForm):
    mood = scale_field("mood")
    energy = scale_field("energy")
    stress = scale_field("stress")
    homesickness = scale_field("homesickness")
    time_block = forms.ChoiceField(label="Time of day", choices=TIME_BLOCKS, widget=forms.RadioSelect)

    class Meta:
        model = WellbeingCheckIn
        fields = ["mood", "energy", "stress", "homesickness", "sleep_hours", "mission_day", "time_block"]
        labels = {"sleep_hours": "Sleep last night (hours)", "mission_day": "Mission day"}
        widgets = {
            "sleep_hours": forms.NumberInput(attrs={"step": "0.5", "min": "0", "max": "14", "inputmode": "decimal"}),
            "mission_day": forms.NumberInput(attrs={"min": "1", "max": "1000", "inputmode": "numeric"}),
        }

    @property
    def scale_fields(self):
        return [self[name] for name in ("mood", "energy", "stress", "homesickness")]


class StartSessionForm(forms.Form):
    scene = forms.ChoiceField(choices=[(key, key) for key in SCENE_KEYS])
    minutes = forms.TypedChoiceField(coerce=int, choices=[(value, f"{value} min") for value in DURATION_CHOICES])

    def __init__(self, *args, context=None, **kwargs):
        self.context = context
        super().__init__(*args, **kwargs)

    def clean_scene(self):
        scene = self.cleaned_data["scene"]
        reason = blocked_reason(scene, self.context)
        if reason:
            raise forms.ValidationError(reason)
        return scene


class ReCheckForm(forms.ModelForm):
    mood_after = scale_field("mood")
    energy_after = scale_field("energy")
    stress_after = scale_field("stress")
    enjoyment = scale_field("enjoyment")

    class Meta:
        model = VRSession
        fields = ["mood_after", "energy_after", "stress_after", "enjoyment"]

    @property
    def scale_fields(self):
        return [self[name] for name in self.Meta.fields]


class GenerateDatasetForm(forms.Form):
    astronauts = forms.IntegerField(label="Astronauts", min_value=5, max_value=500, initial=60)
    days = forms.IntegerField(label="Mission length (days)", min_value=30, max_value=1000, initial=180)
    per_week = forms.FloatField(label="Check-ins per week", min_value=0.5, max_value=14, initial=3.5)
    seed = forms.IntegerField(label="Random seed", min_value=0, max_value=1_000_000, initial=7,
                              help_text="The same settings and seed always give the same dataset.")


class TrainModelForm(forms.Form):
    source = forms.ChoiceField(
        label="Training data", widget=forms.RadioSelect, initial="dataset",
        choices=[("dataset", "Current synthetic dataset"), ("upload", "Upload a CSV")],
    )
    upload = forms.FileField(label="CSV file", required=False, widget=forms.ClearableFileInput(attrs={"accept": ".csv"}))
    include_sessions = forms.BooleanField(label="Also train on completed re-checks recorded in the app", required=False)

    def __init__(self, *args, dataset_available=True, **kwargs):
        self.dataset_available = dataset_available
        super().__init__(*args, **kwargs)

    def clean(self):
        from .jobs import read_training_csv

        cleaned = super().clean()
        if cleaned.get("source") == "upload":
            upload = cleaned.get("upload")
            if not upload:
                self.add_error("upload", "Choose a CSV file to upload.")
            else:
                try:
                    cleaned["frame"] = read_training_csv(upload)
                except ValueError as exc:
                    self.add_error("upload", str(exc))
        elif cleaned.get("source") == "dataset" and not self.dataset_available:
            self.add_error("source", "There is no synthetic dataset yet. Generate one first.")
        return cleaned
