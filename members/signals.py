"""
members/signals.py

Signal handlers untuk:
1. Log SectorHistory otomatis saat current_sector berubah
2. Logging sederhana untuk audit
"""
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Member, SectorHistory
import logging

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Member)
def track_sector_change(sender, instance, **kwargs):
    """
    Simpan sektor lama ke instance sebelum disimpan,
    agar bisa dibandingkan di post_save.
    """
    if instance.pk:
        try:
            old = Member.objects.get(pk=instance.pk)
            instance._old_sector_id = old.current_sector_id
        except Member.DoesNotExist:
            instance._old_sector_id = None
    else:
        # Member baru — tidak ada sektor lama
        instance._old_sector_id = None


@receiver(post_save, sender=Member)
def log_sector_history(sender, instance, created, **kwargs):
    """
    Setelah Member disimpan:
    - Jika baru: catat SectorHistory dengan from_sector=None
    - Jika update dan sektor berubah: catat perpindahan
    """
    if created:
        # Member baru — catat penugasan sektor pertama
        # created_by diisi system user (atau bisa dikosongkan)
        system_user = _get_system_user()
        if system_user:
            SectorHistory.objects.create(
                member=instance,
                from_sector=None,           # Awal, belum ada sektor sebelumnya
                to_sector=instance.current_sector,
                transfer_date=instance.created_at.date() if instance.created_at else None,
                reason="Pendaftaran awal",
                created_by=system_user,
            )
        logger.info(f"Member baru terdaftar: {instance.full_name} ({instance.member_id})")

    else:
        # Member update — cek apakah sektor berubah
        old_sector_id = getattr(instance, "_old_sector_id", None)

        if old_sector_id and old_sector_id != instance.current_sector_id:
            system_user = _get_system_user()
            if system_user:
                from .models import Sector
                try:
                    old_sector = Sector.objects.get(pk=old_sector_id)
                except Sector.DoesNotExist:
                    old_sector = None

                SectorHistory.objects.create(
                    member=instance,
                    from_sector=old_sector,
                    to_sector=instance.current_sector,
                    transfer_date=__import__("datetime").date.today(),
                    reason="Pindah sektor",
                    created_by=system_user,
                )
                logger.info(
                    f"Perpindahan sektor: {instance.full_name} "
                    f"{old_sector} → {instance.current_sector}"
                )


def _get_system_user():
    """
    Ambil user pertama dengan is_superuser=True sebagai 'system user'.
    Di views nyata, gunakan request.user yang diteruskan via update_fields atau middleware.
    """
    return User.objects.filter(is_superuser=True).first()