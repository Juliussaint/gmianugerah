from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
import datetime


# ──────────────────────────────────────────
# SECTOR
# ──────────────────────────────────────────
class Sector(models.Model):
    name        = models.CharField(max_length=100, unique=True, verbose_name="Nama Sektor")
    description = models.TextField(blank=True, null=True, verbose_name="Keterangan")
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Sektor"
        verbose_name_plural = "Sektor"
        ordering            = ["name"]

    def __str__(self):
        return self.name

    def get_active_member_count(self):
        return self.members.filter(is_active=True).count()


# ──────────────────────────────────────────
# FAMILY
# ──────────────────────────────────────────
class Family(models.Model):

    class FamilyStatus(models.TextChoices):
        ACTIVE    = "ACTIVE",    "Aktif"
        INACTIVE  = "INACTIVE",  "Tidak Aktif"
        DISSOLVED = "DISSOLVED", "Bubar"

    sector          = models.ForeignKey(
        Sector, on_delete=models.PROTECT,
        related_name="families",
        verbose_name="Sektor"
    )
    family_name     = models.CharField(max_length=200, verbose_name="Nama Keluarga")
    head_of_family  = models.ForeignKey(
        "Member", on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="head_of_families",
        verbose_name="Kepala Keluarga"
    )

    # Status
    family_status      = models.CharField(
        max_length=20,
        choices=FamilyStatus.choices,
        default=FamilyStatus.ACTIVE,
        verbose_name="Status Keluarga"
    )
    dissolution_reason = models.CharField(
        max_length=100, blank=True, null=True,
        verbose_name="Alasan Bubar",
        help_text="Contoh: Meninggal, Perceraian, Pindah"
    )
    dissolution_date   = models.DateField(
        blank=True, null=True,
        verbose_name="Tanggal Bubar"
    )

    # Address
    address_street      = models.CharField(max_length=255, verbose_name="Alamat Jalan")
    address_city        = models.CharField(max_length=100, verbose_name="Kota")
    address_province    = models.CharField(max_length=100, verbose_name="Provinsi")
    address_postal_code = models.CharField(max_length=10, blank=True, verbose_name="Kode Pos")
    phone_number        = models.CharField(max_length=20, verbose_name="Nomor Telepon")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Keluarga"
        verbose_name_plural = "Keluarga"
        ordering            = ["family_name"]

    def __str__(self):
        return f"{self.family_name} ({self.sector.name})"

    def clean(self):
        # Kalau status DISSOLVED, wajib isi dissolution_reason & dissolution_date
        if self.family_status == self.FamilyStatus.DISSOLVED:
            if not self.dissolution_reason:
                raise ValidationError({
                    "dissolution_reason": "Alasan bubar wajib diisi jika status Bubar."
                })
            if not self.dissolution_date:
                raise ValidationError({
                    "dissolution_date": "Tanggal bubar wajib diisi jika status Bubar."
                })

    def get_member_count(self):
        return self.members.filter(is_active=True).count()

    @property
    def full_address(self):
        parts = [self.address_street, self.address_city,
                 self.address_province]
        if self.address_postal_code:
            parts.append(self.address_postal_code)
        return ", ".join(parts)


# ──────────────────────────────────────────
# MEMBER
# ──────────────────────────────────────────
class Member(models.Model):

    class Gender(models.TextChoices):
        MALE   = "M", "Laki-laki"
        FEMALE = "F", "Perempuan"

    class BloodType(models.TextChoices):
        A_POS  = "A+",  "A+"
        A_NEG  = "A-",  "A-"
        B_POS  = "B+",  "B+"
        B_NEG  = "B-",  "B-"
        AB_POS = "AB+", "AB+"
        AB_NEG = "AB-", "AB-"
        O_POS  = "O+",  "O+"
        O_NEG  = "O-",  "O-"

    class MembershipStatus(models.TextChoices):
        FULL         = "FULL",         "Anggota Penuh"
        PREPARATION  = "PREPARATION",  "Anggota Persiapan"
        TRANSFER_IN  = "TRANSFER_IN",  "Pindah Masuk"
        TRANSFER_OUT = "TRANSFER_OUT", "Pindah Keluar"

    # ── Identitas ──
    member_id = models.CharField(
        max_length=15, unique=True, blank=True,
        verbose_name="NIJ",
        help_text="Nomor Induk Jemaat — auto-generate"
    )
    family = models.ForeignKey(
        Family, on_delete=models.PROTECT,
        related_name="members",
        verbose_name="Keluarga"
    )
    current_sector = models.ForeignKey(
        Sector, on_delete=models.PROTECT,
        related_name="members",
        verbose_name="Sektor Saat Ini"
    )
    full_name = models.CharField(max_length=200, verbose_name="Nama Lengkap")
    gender    = models.CharField(max_length=1, choices=Gender.choices, verbose_name="Jenis Kelamin")

    # ── Data Pribadi ──
    blood_type    = models.CharField(
        max_length=3, choices=BloodType.choices,
        blank=True, null=True,
        verbose_name="Golongan Darah"
    )
    date_of_birth = models.DateField(verbose_name="Tanggal Lahir")
    phone_number  = models.CharField(max_length=20, blank=True, verbose_name="Nomor HP")
    email         = models.EmailField(blank=True, verbose_name="Email")

    # ── Data Gereja ──
    baptism_date      = models.DateField(blank=True, null=True, verbose_name="Tanggal Baptis")
    sidi_date         = models.DateField(blank=True, null=True, verbose_name="Tanggal Sidi")
    marriage_date     = models.DateField(blank=True, null=True, verbose_name="Tanggal Nikah")
    membership_status = models.CharField(
        max_length=20,
        choices=MembershipStatus.choices,
        default=MembershipStatus.FULL,
        verbose_name="Status Keanggotaan"
    )

    # ── Status Aktif ──
    is_active       = models.BooleanField(default=True, verbose_name="Aktif")
    inactive_reason = models.CharField(
        max_length=100, blank=True, null=True,
        verbose_name="Alasan Tidak Aktif"
    )

    # ── Foto ──
    photo = models.ImageField(
        upload_to="members/photos/%Y/%m/",
        blank=True, null=True,
        verbose_name="Foto"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Jemaat"
        verbose_name_plural = "Jemaat"
        ordering            = ["full_name"]
        indexes = [
            models.Index(fields=["member_id"]),
            models.Index(fields=["full_name"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["membership_status"]),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.member_id})"

    def save(self, *args, **kwargs):
        # Auto-generate NIJ sebelum simpan pertama kali
        if not self.member_id:
            self.member_id = self._generate_nij()
        super().save(*args, **kwargs)

    def _generate_nij(self):
        """
        Generate NIJ dengan format: NIJ-YYYY-XXXXX
        Contoh: NIJ-2026-00001
        Thread-safe menggunakan select_for_update().
        """
        from django.db import transaction

        year = timezone.now().year
        prefix = f"NIJ-{year}-"

        with transaction.atomic():
            # Lock baris terakhir untuk mencegah race condition
            last = (
                Member.objects
                .filter(member_id__startswith=prefix)
                .select_for_update()
                .order_by("-member_id")
                .first()
            )

            if last:
                try:
                    last_seq = int(last.member_id.split("-")[-1])
                except (ValueError, IndexError):
                    last_seq = 0
            else:
                last_seq = 0

            new_seq = last_seq + 1
            return f"{prefix}{new_seq:05d}"

    @property
    def age(self):
        if not self.date_of_birth:
            return None
        today = datetime.date.today()
        return (
            today.year - self.date_of_birth.year
            - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        )

    @property
    def initials(self):
        """Ambil dua huruf pertama nama untuk avatar."""
        parts = self.full_name.strip().split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[1][0]).upper()
        return self.full_name[:2].upper()

    def days_until_birthday(self):
        """Hitung hari sampai ulang tahun berikutnya."""
        if not self.date_of_birth:
            return None
        today = datetime.date.today()
        birthday = self.date_of_birth.replace(year=today.year)
        if birthday < today:
            birthday = birthday.replace(year=today.year + 1)
        return (birthday - today).days


# ──────────────────────────────────────────
# SECTOR HISTORY
# ──────────────────────────────────────────
class SectorHistory(models.Model):
    member      = models.ForeignKey(
        Member, on_delete=models.CASCADE,
        related_name="sector_history",
        verbose_name="Jemaat"
    )
    from_sector = models.ForeignKey(
        Sector, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="transfers_from",
        verbose_name="Dari Sektor"
    )
    to_sector   = models.ForeignKey(
        Sector, on_delete=models.PROTECT,
        related_name="transfers_to",
        verbose_name="Ke Sektor"
    )
    transfer_date = models.DateField(verbose_name="Tanggal Pindah")
    reason        = models.CharField(max_length=200, blank=True, verbose_name="Alasan")
    notes         = models.TextField(blank=True, verbose_name="Catatan")
    created_by    = models.ForeignKey(
        User, on_delete=models.PROTECT,
        verbose_name="Dicatat Oleh"
    )
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Riwayat Sektor"
        verbose_name_plural = "Riwayat Sektor"
        ordering            = ["-transfer_date"]

    def __str__(self):
        from_name = self.from_sector.name if self.from_sector else "Awal"
        return (
            f"{self.member.full_name}: "
            f"{from_name} → {self.to_sector.name} "
            f"({self.transfer_date})"
        )