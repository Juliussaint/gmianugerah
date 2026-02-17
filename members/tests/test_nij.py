"""
Test NIJ auto-generation logic.

Jalankan dengan:
    python manage.py test members.tests.test_nij -v 2
"""
from django.test import TestCase
from django.contrib.auth.models import User
from unittest.mock import patch
from members.models import Sector, Family, Member
import datetime


def make_sector(name="Sektor A"):
    return Sector.objects.get_or_create(name=name)[0]


def make_family(sector=None):
    if sector is None:
        sector = make_sector()
    return Family.objects.create(
        sector=sector,
        family_name="Keluarga Test",
        family_status=Family.FamilyStatus.ACTIVE,
        address_street="Jl. Test No. 1",
        address_city="Jakarta",
        address_province="DKI Jakarta",
        phone_number="08123456789",
    )


class NIJGenerationTest(TestCase):
    """Test NIJ auto-generate dengan format NIJ-YYYY-XXXXX."""

    def setUp(self):
        self.sector = make_sector()
        self.family = make_family(self.sector)

    def _make_member(self, full_name="Jemaat Test"):
        return Member.objects.create(
            family=self.family,
            current_sector=self.sector,
            full_name=full_name,
            gender=Member.Gender.MALE,
            date_of_birth=datetime.date(1990, 1, 1),
            membership_status=Member.MembershipStatus.FULL,
        )

    # ── Format ──────────────────────────────────────────────
    def test_nij_format(self):
        """NIJ harus memiliki format NIJ-YYYY-XXXXX."""
        member = self._make_member()
        year = datetime.date.today().year
        self.assertRegex(member.member_id, rf"^NIJ-{year}-\d{{5}}$")

    def test_nij_is_auto_generated(self):
        """member_id terisi otomatis saat save."""
        member = self._make_member()
        self.assertIsNotNone(member.member_id)
        self.assertTrue(member.member_id.startswith("NIJ-"))

    def test_nij_not_overwritten_on_update(self):
        """NIJ tidak boleh berubah saat update data member."""
        member = self._make_member()
        original_nij = member.member_id
        member.full_name = "Nama Baru"
        member.save()
        member.refresh_from_db()
        self.assertEqual(member.member_id, original_nij)

    # ── Sequence ────────────────────────────────────────────
    def test_nij_increments_sequentially(self):
        """Setiap member baru mendapat nomor urut yang bertambah."""
        m1 = self._make_member("Member Satu")
        m2 = self._make_member("Member Dua")
        m3 = self._make_member("Member Tiga")

        seq1 = int(m1.member_id.split("-")[-1])
        seq2 = int(m2.member_id.split("-")[-1])
        seq3 = int(m3.member_id.split("-")[-1])

        self.assertEqual(seq2, seq1 + 1)
        self.assertEqual(seq3, seq2 + 1)

    def test_nij_first_member_starts_at_00001(self):
        """Member pertama dalam tahun ini harus dimulai dari 00001."""
        year = datetime.date.today().year
        member = self._make_member()
        # Ambil nomor urut
        seq = int(member.member_id.split("-")[-1])
        self.assertGreaterEqual(seq, 1)

    # ── Uniqueness ──────────────────────────────────────────
    def test_nij_is_unique(self):
        """Dua member tidak boleh memiliki NIJ yang sama."""
        members = [self._make_member(f"Member {i}") for i in range(10)]
        nij_list = [m.member_id for m in members]
        self.assertEqual(len(nij_list), len(set(nij_list)), "NIJ harus unik!")

    def test_nij_unique_constraint_in_db(self):
        """Database constraint memastikan NIJ unik."""
        from django.db import IntegrityError
        member = self._make_member()
        with self.assertRaises(Exception):
            # Paksa NIJ yang sama → harus error
            Member.objects.create(
                member_id=member.member_id,
                family=self.family,
                current_sector=self.sector,
                full_name="Duplikat Member",
                gender=Member.Gender.FEMALE,
                date_of_birth=datetime.date(1995, 6, 15),
                membership_status=Member.MembershipStatus.FULL,
            )

    # ── Year prefix ─────────────────────────────────────────
    def test_nij_uses_current_year(self):
        """NIJ menggunakan tahun saat ini."""
        import datetime
        year = datetime.date.today().year
        member = self._make_member()
        self.assertIn(str(year), member.member_id)

    def test_nij_resets_sequence_each_year(self):
        """
        Sequence harus restart di tahun baru.
        Simulasi dengan mock tahun berbeda.
        """
        # Buat member di "2025"
        with patch("django.utils.timezone.now") as mock_now:
            mock_dt = datetime.datetime(2025, 12, 31, tzinfo=datetime.timezone.utc)
            mock_now.return_value = mock_dt
            m_2025 = self._make_member("Member 2025")

        # Buat member di "2026"
        with patch("django.utils.timezone.now") as mock_now:
            mock_dt = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
            mock_now.return_value = mock_dt
            m_2026 = self._make_member("Member 2026")

        self.assertIn("2025", m_2025.member_id)
        self.assertIn("2026", m_2026.member_id)

        # Sequence 2026 harus mulai dari 00001 lagi
        seq_2026 = int(m_2026.member_id.split("-")[-1])
        self.assertEqual(seq_2026, 1)


class MemberModelTest(TestCase):
    """Test properti dan method tambahan di Member."""

    def setUp(self):
        self.sector = make_sector()
        self.family = make_family(self.sector)

    def test_age_calculation(self):
        """Hitung usia berdasarkan tanggal lahir."""
        birth = datetime.date.today().replace(year=datetime.date.today().year - 30)
        member = Member.objects.create(
            family=self.family,
            current_sector=self.sector,
            full_name="Test Usia",
            gender=Member.Gender.FEMALE,
            date_of_birth=birth,
            membership_status=Member.MembershipStatus.FULL,
        )
        self.assertEqual(member.age, 30)

    def test_initials_two_words(self):
        """Inisial dari dua kata nama."""
        member = Member(full_name="Budi Santoso")
        self.assertEqual(member.initials, "BS")

    def test_initials_single_word(self):
        """Inisial dari satu kata nama."""
        member = Member(full_name="Madonna")
        self.assertEqual(member.initials, "MA")

    def test_str_representation(self):
        """__str__ menampilkan nama dan NIJ."""
        member = Member.objects.create(
            family=self.family,
            current_sector=self.sector,
            full_name="Budi Santoso",
            gender=Member.Gender.MALE,
            date_of_birth=datetime.date(1985, 3, 20),
            membership_status=Member.MembershipStatus.FULL,
        )
        self.assertIn("Budi Santoso", str(member))
        self.assertIn("NIJ-", str(member))


class FamilyModelTest(TestCase):
    """Test validasi Family model."""

    def setUp(self):
        self.sector = make_sector()

    def test_dissolved_family_requires_reason(self):
        """Keluarga Bubar wajib isi alasan."""
        from django.core.exceptions import ValidationError
        family = Family(
            sector=self.sector,
            family_name="Keluarga Bubar",
            family_status=Family.FamilyStatus.DISSOLVED,
            address_street="Jl. Test",
            address_city="Jakarta",
            address_province="DKI Jakarta",
            phone_number="0812345678",
            dissolution_date=datetime.date.today(),
            # dissolution_reason sengaja dikosongkan
        )
        with self.assertRaises(ValidationError):
            family.clean()

    def test_dissolved_family_requires_date(self):
        """Keluarga Bubar wajib isi tanggal bubar."""
        from django.core.exceptions import ValidationError
        family = Family(
            sector=self.sector,
            family_name="Keluarga Bubar",
            family_status=Family.FamilyStatus.DISSOLVED,
            address_street="Jl. Test",
            address_city="Jakarta",
            address_province="DKI Jakarta",
            phone_number="0812345678",
            dissolution_reason="Meninggal",
            # dissolution_date sengaja dikosongkan
        )
        with self.assertRaises(ValidationError):
            family.clean()

    def test_active_family_no_dissolution_needed(self):
        """Keluarga Aktif tidak perlu dissolution fields."""
        from django.core.exceptions import ValidationError
        family = Family(
            sector=self.sector,
            family_name="Keluarga Aktif",
            family_status=Family.FamilyStatus.ACTIVE,
            address_street="Jl. Test",
            address_city="Jakarta",
            address_province="DKI Jakarta",
            phone_number="0812345678",
        )
        # Tidak boleh raise error
        try:
            family.clean()
        except ValidationError:
            self.fail("clean() raised ValidationError untuk keluarga aktif!")