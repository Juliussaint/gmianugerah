from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Sector, Family, Member, SectorHistory


# ──────────────────────────────────────────
# SECTOR ADMIN
# ──────────────────────────────────────────
@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    list_display  = ("name", "get_family_count", "get_member_count", "created_at")
    search_fields = ("name",)
    ordering      = ("name",)

    def get_family_count(self, obj):
        return obj.families.count()
    get_family_count.short_description = "Jumlah Keluarga"

    def get_member_count(self, obj):
        return obj.get_active_member_count()
    get_member_count.short_description = "Jemaat Aktif"


# ──────────────────────────────────────────
# SECTOR HISTORY INLINE (untuk Member)
# ──────────────────────────────────────────
class SectorHistoryInline(admin.TabularInline):
    model          = SectorHistory
    extra          = 0
    readonly_fields = ("from_sector", "to_sector", "transfer_date", "reason", "created_by", "created_at")
    can_delete     = False

    def has_add_permission(self, request, obj=None):
        return False


# ──────────────────────────────────────────
# MEMBER INLINE (untuk Family)
# ──────────────────────────────────────────
class MemberInline(admin.TabularInline):
    model       = Member
    extra       = 0
    fields      = ("full_name", "member_id", "gender", "family_role", "birth_order", "membership_status", "is_active", "is_deceased")
    readonly_fields = ("member_id",)
    show_change_link = True


# ──────────────────────────────────────────
# FAMILY ADMIN
# ──────────────────────────────────────────
@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display   = (
        "family_name", "sector", "head_of_family",
        "family_status", "get_member_count", "phone_number"
    )
    list_filter    = ("sector", "family_status")
    search_fields  = ("family_name", "phone_number", "address_street")
    ordering       = ("family_name",)
    inlines        = [MemberInline]

    fieldsets = (
        ("Informasi Keluarga", {
            "fields": ("family_name", "sector", "head_of_family", "family_status")
        }),
        ("Status Keluarga (isi jika Bubar)", {
            "fields": ("dissolution_reason", "dissolution_date"),
            "classes": ("collapse",),
        }),
        ("Alamat & Kontak", {
            "fields": (
                "address_street", "address_city",
                "address_province", "address_postal_code",
                "phone_number"
            )
        }),
    )

    def get_member_count(self, obj):
        return obj.get_member_count()
    get_member_count.short_description = "Jml Anggota"


# ──────────────────────────────────────────
# MEMBER ADMIN
# ──────────────────────────────────────────
@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = (
        "get_photo_thumb", "full_name", "member_id",
        "family_role", "current_sector", "gender", 
        "membership_status", "is_active", "get_deceased_badge",
        "date_of_birth"
    )
    list_filter  = (
        "current_sector", "membership_status",
        "is_active", "gender", "family_role", "is_deceased"
    )
    search_fields  = ("full_name", "member_id", "phone_number", "email")
    readonly_fields = ("member_id", "get_photo_thumb", "age_display")
    ordering       = ("full_name",)
    inlines        = [SectorHistoryInline]

    fieldsets = (
        ("Identitas", {
            "fields": (
                "member_id", "full_name", "gender",
                "date_of_birth", "age_display",
                "blood_type", "photo", "get_photo_thumb"
            )
        }),
        ("Peran dalam Keluarga", {
            "fields": ("family_role", "birth_order"),
            "classes": ("collapse",),
        }),
        ("Kontak", {
            "fields": ("phone_number", "email"),
        }),
        ("Keanggotaan", {
            "fields": (
                "family", "current_sector",
                "membership_status", "is_active", "inactive_reason"
            )
        }),
        ("Data Gereja", {
            "fields": ("baptism_date", "sidi_date", "marriage_date"),
            "classes": ("collapse",),
        }),
        ("Status Kehidupan", {
            "fields": ("is_deceased", "deceased_date", "deceased_reason"),
            "classes": ("collapse",),
        }),
    )

    def get_photo_thumb(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="width:40px;height:40px;border-radius:50%;object-fit:cover;">',
                obj.photo.url
            )
        return format_html(
            '<div style="width:40px;height:40px;border-radius:50%;background:#e0ebff;'
            'display:flex;align-items:center;justify-content:center;'
            'font-weight:bold;color:#6272f5;font-size:14px;">{}</div>',
            obj.initials
        )
    get_photo_thumb.short_description = "Foto"

    def age_display(self, obj):
        age = obj.age
        return f"{age} tahun" if age else "-"
    age_display.short_description = "Usia"
    
    def get_deceased_badge(self, obj):
        """Show deceased badge in list"""
        if obj.is_deceased:
            return format_html(
                '<span style="background:#1f2937;color:white;padding:2px 8px;'
                'border-radius:4px;font-size:11px;font-weight:600;">† Alm</span>'
            )
        return ""
    get_deceased_badge.short_description = "Status"


# ──────────────────────────────────────────
# SECTOR HISTORY ADMIN
# ──────────────────────────────────────────
@admin.register(SectorHistory)
class SectorHistoryAdmin(admin.ModelAdmin):
    list_display  = ("member", "from_sector", "to_sector", "transfer_date", "created_by")
    list_filter   = ("to_sector", "from_sector", "transfer_date")
    search_fields = ("member__full_name", "member__member_id")
    readonly_fields = ("created_by", "created_at")
    ordering      = ("-transfer_date",)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)