from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.forms import (
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)

from .demo import is_portfolio_demo_user
from .rbac import (
    ROLE_CHOICES,
    assign_role,
)


User = get_user_model()


def _bootstrap_fields(form):
    for field in form.fields.values():
        css = field.widget.attrs.get("class", "")
        field.widget.attrs["class"] = (css + " form-control").strip()


def _validate_unique_email(email, instance=None):
    email = (email or "").strip()
    if not email:
        raise forms.ValidationError("L’adresse e-mail est obligatoire.")

    queryset = User.objects.filter(email__iexact=email)
    if instance is not None and instance.pk:
        queryset = queryset.exclude(pk=instance.pk)

    if queryset.exists():
        raise forms.ValidationError(
            _("Cette adresse e-mail est déjà utilisée par un autre compte.")
        )
    return email


class ProfileForm(forms.ModelForm):
    current_password = forms.CharField(
        label=_("Mot de passe actuel"),
        required=False,
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "current-password",
                "placeholder": _("Requis uniquement pour changer l’e-mail"),
            }
        ),
        help_text=(
            "Pour protéger le compte, le mot de passe actuel est demandé "
            "uniquement si l’adresse e-mail change."
        ),
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")
        labels = {
            "first_name": _("Prénom"),
            "last_name": _("Nom"),
            "email": _("Adresse e-mail"),
        }
        widgets = {
            "first_name": forms.TextInput(
                attrs={"autocomplete": "given-name", "placeholder": _("Prénom")}
            ),
            "last_name": forms.TextInput(
                attrs={"autocomplete": "family-name", "placeholder": _("Nom")}
            ),
            "email": forms.EmailInput(
                attrs={"autocomplete": "email", "placeholder": "nom@exemple.com"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        _bootstrap_fields(self)

    def clean_email(self):
        return _validate_unique_email(
            self.cleaned_data.get("email"),
            self.instance,
        )

    def clean(self):
        cleaned = super().clean()
        new_email = cleaned.get("email")
        old_email = (self.instance.email or "").strip()
        password = cleaned.get("current_password")

        email_changed = (
            new_email is not None
            and new_email.casefold() != old_email.casefold()
        )

        if email_changed:
            if not password:
                self.add_error(
                    "current_password",
                    _("Saisissez votre mot de passe actuel pour modifier l’e-mail."),
                )
            elif not self.instance.check_password(password):
                self.add_error(
                    "current_password",
                    _("Le mot de passe actuel est incorrect."),
                )

        return cleaned


class BootstrapPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _bootstrap_fields(self)
        self.fields["old_password"].widget.attrs["autocomplete"] = "current-password"
        self.fields["new_password1"].widget.attrs["autocomplete"] = "new-password"
        self.fields["new_password2"].widget.attrs["autocomplete"] = "new-password"


class BootstrapPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _bootstrap_fields(self)
        self.fields["email"].widget.attrs.update(
            {
                "autocomplete": "email",
                "placeholder": "nom@exemple.com",
            }
        )

    def get_users(self, email):
        for user in super().get_users(email):
            if not is_portfolio_demo_user(user):
                yield user


class BootstrapSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _bootstrap_fields(self)
        self.fields["new_password1"].widget.attrs["autocomplete"] = "new-password"
        self.fields["new_password2"].widget.attrs["autocomplete"] = "new-password"


class ManagedUserCreateForm(UserCreationForm):
    email = forms.EmailField(label=_("Adresse e-mail"), required=True)
    first_name = forms.CharField(label=_("Prénom"), required=False)
    last_name = forms.CharField(label=_("Nom"), required=False)
    role = forms.ChoiceField(label=_("Rôle"), choices=ROLE_CHOICES)
    is_active = forms.BooleanField(
        label=_("Compte actif"),
        required=False,
        initial=True,
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "role",
            "is_active",
            "password1",
            "password2",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _bootstrap_fields(self)
        self.fields["is_active"].widget.attrs["class"] = "form-check-input"

    def clean_email(self):
        return _validate_unique_email(self.cleaned_data.get("email"))

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data.get("first_name", "")
        user.last_name = self.cleaned_data.get("last_name", "")
        user.is_active = self.cleaned_data.get("is_active", True)

        if commit:
            user.save()
            assign_role(user, self.cleaned_data["role"])
        return user


class ManagedUserRoleForm(forms.Form):
    role = forms.ChoiceField(label=_("Rôle"), choices=ROLE_CHOICES)
    is_active = forms.BooleanField(
        label=_("Compte actif"),
        required=False,
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user is not None:
            self.fields["is_active"].initial = user.is_active
        self.fields["role"].widget.attrs["class"] = "form-select"
        self.fields["is_active"].widget.attrs["class"] = "form-check-input"
