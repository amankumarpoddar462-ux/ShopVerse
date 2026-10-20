from django.apps import apps
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin


@admin.register(get_user_model())
class ShopVerseUserAdmin(UserAdmin):
    list_display = (
        "username",
        "email",
        "phone",
        "role",
        "is_staff",
        "is_active",
        "date_joined",
    )
    list_filter = ("role", "is_staff", "is_active", "is_verified")
    search_fields = ("username", "first_name", "last_name", "email", "phone")
    fieldsets = UserAdmin.fieldsets + (
        (
            "ShopVerse account",
            {
                "fields": (
                    "role",
                    "phone",
                    "is_verified",
                    "avatar_url",
                    "wallet_balance",
                    "reward_points",
                    "support_approved",
                    "support_level",
                    "referral_code",
                    "referred_by",
                )
            },
        ),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("ShopVerse account", {"fields": ("role", "phone")}),
    )


class ShopVerseModelAdmin(admin.ModelAdmin):
    exclude = (
        "password",
        "password_hash",
        "reset_token",
        "reset_token_created_at",
    )
    list_per_page = 50

    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)
        fields = [
            field
            for field in model._meta.get_fields()
            if getattr(field, "concrete", False)
            and not getattr(field, "many_to_many", False)
            and field.name not in self.exclude
        ]
        displayable_types = {
            "AutoField",
            "BigAutoField",
            "BigIntegerField",
            "BooleanField",
            "CharField",
            "DateField",
            "DateTimeField",
            "DecimalField",
            "EmailField",
            "FloatField",
            "ForeignKey",
            "IntegerField",
            "PositiveIntegerField",
            "SlugField",
        }
        preferred_names = (
            "name",
            "title",
            "store_name",
            "order_number",
            "ticket_id",
            "username",
            "email",
            "status",
            "is_active",
            "is_approved",
            "created_at",
            "id",
        )
        by_name = {field.name: field for field in fields}
        display_fields = [
            name
            for name in preferred_names
            if name in by_name
            and by_name[name].get_internal_type() in displayable_types
        ]
        for field in fields:
            if (
                len(display_fields) >= 6
                or field.name in display_fields
                or field.get_internal_type() not in displayable_types
            ):
                continue
            display_fields.append(field.name)
        self.list_display = tuple(display_fields) or ("__str__",)

        self.search_fields = tuple(
            field.name
            for field in fields
            if field.get_internal_type() in {"CharField", "EmailField", "SlugField"}
        )[:6]
        self.list_filter = tuple(
            field.name
            for field in fields
            if field.choices or field.get_internal_type() in {"BooleanField", "DateField", "DateTimeField"}
        )[:4]
        if "created_at" in by_name and by_name["created_at"].get_internal_type() == "DateTimeField":
            self.date_hierarchy = "created_at"


for model in apps.get_models():
    if (
        model._meta.app_config.name.startswith("django.")
        or model._meta.proxy
        or model is get_user_model()
        or admin.site.is_registered(model)
    ):
        continue
    admin.site.register(model, ShopVerseModelAdmin)
