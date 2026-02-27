from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q
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

    @property
    def husband(self):
        """Get suami (kepala keluarga) yang masih hidup"""
        return self.members.filter(
            family_role='HUSBAND',
            is_deceased=False
        ).first()

    @property
    def wife(self):
        """Get istri yang masih hidup"""
        return self.members.filter(
            family_role='WIFE',
            is_deceased=False
        ).first()

    @property
    def children(self):
        """Get semua anak yang masih hidup, sorted by birth_order"""
        return self.members.filter(
            family_role='CHILD',
            is_deceased=False
        ).order_by('birth_order')

    @property
    def deceased_members(self):
        """Get anggota keluarga yang sudah meninggal"""
        return self.members.filter(is_deceased=True).order_by('-deceased_date')

    def validate_family_structure(self):
        """Validasi struktur keluarga"""
        errors = []

        # Check: Maksimal 1 suami hidup
        husband_count = self.members.filter(
            family_role='HUSBAND',
            is_deceased=False
        ).count()
        if husband_count > 1:
            errors.append("Tidak boleh ada lebih dari 1 suami hidup dalam 1 keluarga")

        # Check: Maksimal 1 istri hidup
        wife_count = self.members.filter(
            family_role='WIFE',
            is_deceased=False
        ).count()
        if wife_count > 1:
            errors.append("Tidak boleh ada lebih dari 1 istri hidup dalam 1 keluarga")

        return errors


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

    class FamilyRole(models.TextChoices):
        HUSBAND = 'HUSBAND', 'Suami'
        WIFE = 'WIFE', 'Istri'
        CHILD = 'CHILD', 'Anak'
        PARENT = 'PARENT', 'Orang Tua (Kakek/Nenek)'
        OTHER = 'OTHER', 'Lainnya'

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

    # ── Peran dalam Keluarga ──
    family_role = models.CharField(
        max_length=10,
        choices=FamilyRole.choices,
        default=FamilyRole.OTHER,
        verbose_name="Peran dalam Keluarga",
        help_text="Peran anggota dalam struktur keluarga"
    )

    birth_order = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Urutan Kelahiran",
        help_text="Hanya untuk anak: 1 = anak pertama, 2 = anak kedua, dst."
    )

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

    # ── Status Kehidupan ──
    is_deceased = models.BooleanField(
        default=False,
        verbose_name="Sudah Meninggal",
        help_text="Centang jika jemaat sudah meninggal dunia"
    )

    deceased_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Tanggal Meninggal"
    )

    deceased_reason = models.TextField(
        blank=True,
        verbose_name="Sebab Meninggal / Catatan",
        help_text="Opsional: Sebab meninggal atau catatan lainnya"
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
            models.Index(fields=["family_role"]),
            models.Index(fields=["is_deceased"]),
        ]
        constraints = [
            # Pastikan birth_order unique per family untuk anak
            models.UniqueConstraint(
                fields=['family', 'birth_order'],
                condition=Q(family_role='CHILD', birth_order__isnull=False),
                name='unique_birth_order_per_family'
            )
        ]

    def __str__(self):
        return f"{self.full_name} ({self.member_id})"

    def clean(self):
        """Validasi model-level"""
        errors = {}

        # Validasi 1: birth_order hanya untuk CHILD
        if self.birth_order and self.family_role != self.FamilyRole.CHILD:
            errors['birth_order'] = 'Urutan kelahiran hanya untuk anak'

        # Validasi 2: CHILD wajib punya birth_order
        if self.family_role == self.FamilyRole.CHILD and not self.birth_order:
            errors['birth_order'] = 'Anak wajib memiliki urutan kelahiran'

        # Validasi 3: Jika meninggal, wajib isi tanggal
        if self.is_deceased and not self.deceased_date:
            errors['deceased_date'] = 'Tanggal meninggal wajib diisi'

        # Validasi 4: Tanggal meninggal harus setelah lahir
        if self.deceased_date and self.date_of_birth:
            if self.deceased_date < self.date_of_birth:
                errors['deceased_date'] = 'Tanggal meninggal tidak boleh sebelum tanggal lahir'

        if errors:
            raise ValidationError(errors)

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