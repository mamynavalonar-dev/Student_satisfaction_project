from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView
from django.utils.translation import gettext as _

from .demo import is_portfolio_demo_user
from .forms import (
    BootstrapPasswordChangeForm,
    BootstrapPasswordResetForm,
    BootstrapSetPasswordForm,
    ManagedUserCreateForm,
    ManagedUserRoleForm,
    ProfileForm,
)
from .rbac import (
    CAP_USERS,
    ROLE_SUPER_ADMIN,
    assign_role,
    can_manage_target,
    get_user_role,
    role_badge_class,
    user_can,
)


User = get_user_model()


class CapabilityRequiredMixin(LoginRequiredMixin):
    capability = None
    login_url = reverse_lazy("login_register")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if not user_can(request.user, self.capability):
            return HttpResponseForbidden(
                _("Votre rôle ne permet pas d’accéder à cette page.")
            )
        return super().dispatch(request, *args, **kwargs)


class DemoAccountImmutableMixin:
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and is_portfolio_demo_user(request.user):
            return HttpResponseForbidden(
                _("Le compte public de démonstration ne peut pas être modifié.")
            )
        return super().dispatch(request, *args, **kwargs)


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"
    login_url = reverse_lazy("login_register")


class ProfileUpdateView(DemoAccountImmutableMixin, LoginRequiredMixin, FormView):
    template_name = "accounts/profile_edit.html"
    form_class = ProfileForm
    success_url = reverse_lazy("accounts:profile")
    login_url = reverse_lazy("login_register")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(
            self.request,
            _("Votre profil a été mis à jour avec succès."),
        )
        return super().form_valid(form)


class AccountPasswordChangeView(
    DemoAccountImmutableMixin,
    LoginRequiredMixin,
    auth_views.PasswordChangeView,
):
    template_name = "accounts/password_change.html"
    form_class = BootstrapPasswordChangeForm
    success_url = reverse_lazy("accounts:profile")
    login_url = reverse_lazy("login_register")

    def form_valid(self, form):
        messages.success(
            self.request,
            _("Votre mot de passe a été modifié. Votre session actuelle reste active."),
        )
        return super().form_valid(form)


class AccountPasswordResetView(auth_views.PasswordResetView):
    template_name = "accounts/password_reset_form.html"
    form_class = BootstrapPasswordResetForm
    email_template_name = "accounts/password_reset_email.txt"
    subject_template_name = "accounts/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")


class AccountPasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class AccountPasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    form_class = BootstrapSetPasswordForm
    success_url = reverse_lazy("accounts:password_reset_complete")

    def form_valid(self, form):
        if is_portfolio_demo_user(self.user):
            return HttpResponseForbidden(
                _("Le mot de passe du compte public de démonstration est administré par le déploiement.")
            )
        return super().form_valid(form)


class AccountPasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"


class UserManagementView(CapabilityRequiredMixin, TemplateView):
    capability = CAP_USERS
    template_name = "accounts/user_management.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        query = (self.request.GET.get("q") or "").strip()
        queryset = (
            User.objects.all()
            .prefetch_related("groups")
            .order_by("-is_superuser", "-is_staff", "username")
        )

        if query:
            queryset = queryset.filter(
                Q(username__icontains=query)
                | Q(email__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
            )

        paginator = Paginator(queryset, 20)
        page = paginator.get_page(self.request.GET.get("page"))

        rows = []
        for user in page.object_list:
            role = get_user_role(user)
            rows.append(
                {
                    "user": user,
                    "role": role,
                    "role_label": _(role),
                    "role_badge_class": role_badge_class(role),
                    "can_edit": can_manage_target(self.request.user, user),
                }
            )

        context.update(
            {
                "rows": rows,
                "page_obj": page,
                "query": query,
                "total_users": queryset.count(),
            }
        )
        return context


class ManagedUserCreateView(CapabilityRequiredMixin, FormView):
    capability = CAP_USERS
    template_name = "accounts/user_create.html"
    form_class = ManagedUserCreateForm
    success_url = reverse_lazy("accounts:user_list")

    def form_valid(self, form):
        user = form.save()
        messages.success(
            self.request,
            f"Le compte {user.username} a été créé avec le rôle {get_user_role(user)}.",
        )
        return super().form_valid(form)


class UserRoleUpdateView(CapabilityRequiredMixin, FormView):
    capability = CAP_USERS
    template_name = "accounts/user_role_edit.html"
    form_class = ManagedUserRoleForm
    success_url = reverse_lazy("accounts:user_list")

    def dispatch(self, request, *args, **kwargs):
        self.target_user = get_object_or_404(User, pk=kwargs["pk"])

        if request.user.is_authenticated and not can_manage_target(
            request.user,
            self.target_user,
        ):
            if self.target_user.is_superuser:
                messages.error(
                    request,
                    (
                        "Un Super Administrateur ne peut pas être modifié depuis "
                        "cette interface. Utilisez l’administration Django ou la CLI."
                    ),
                )
            elif self.target_user.pk == request.user.pk:
                messages.error(
                    request,
                    _("Vous ne pouvez pas modifier votre propre rôle depuis cette interface."),
                )
            return redirect("accounts:user_list")

        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        initial.update(
            {
                "role": get_user_role(self.target_user),
                "is_active": self.target_user.is_active,
            }
        )
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.target_user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["target_user"] = self.target_user
        context["target_role"] = get_user_role(self.target_user)
        context["target_role_label"] = _(context["target_role"])
        return context

    def form_valid(self, form):
        role = form.cleaned_data["role"]
        is_active = form.cleaned_data["is_active"]

        assign_role(self.target_user, role)

        if self.target_user.is_active != is_active:
            self.target_user.is_active = is_active
            self.target_user.save(update_fields=["is_active"])

        messages.success(
            self.request,
            f"Rôle de {self.target_user.username} mis à jour : {role}.",
        )
        return super().form_valid(form)
