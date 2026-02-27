# Generated migration file
# members/migrations/0002_add_family_roles_and_deceased_status.py

from django.db import migrations, models
import django.db.models.deletion


def migrate_existing_data(apps, schema_editor):
    """
    Migrate existing data:
    - Set head_of_family sebagai HUSBAND/WIFE berdasarkan gender
    - Set members lainnya sebagai OTHER
    - Semua member default is_deceased=False
    """
    Member = apps.get_model('members', 'Member')
    Family = apps.get_model('members', 'Family')
    
    for family in Family.objects.all():
        if family.head_of_family_id:
            try:
                head = Member.objects.get(pk=family.head_of_family_id)
                # Set kepala keluarga sebagai suami atau istri
                if head.gender == 'M':
                    head.family_role = 'HUSBAND'
                else:
                    head.family_role = 'WIFE'
                head.save(update_fields=['family_role'])
            except Member.DoesNotExist:
                pass
        
        # Set semua anggota lain sebagai OTHER (default)
        # Nanti bisa diubah manual lewat admin
        family.members.filter(family_role='OTHER').update(family_role='OTHER')


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0001_initial'),  # Adjust to your last migration
    ]

    operations = [
        # Add FamilyRole field
        migrations.AddField(
            model_name='member',
            name='family_role',
            field=models.CharField(
                choices=[
                    ('HUSBAND', 'Suami'),
                    ('WIFE', 'Istri'),
                    ('CHILD', 'Anak'),
                    ('PARENT', 'Orang Tua (Kakek/Nenek)'),
                    ('OTHER', 'Lainnya')
                ],
                default='OTHER',
                help_text='Peran anggota dalam struktur keluarga',
                max_length=10,
                verbose_name='Peran dalam Keluarga'
            ),
        ),
        
        # Add birth_order field
        migrations.AddField(
            model_name='member',
            name='birth_order',
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text='Hanya untuk anak: 1 = anak pertama, 2 = anak kedua, dst.',
                null=True,
                verbose_name='Urutan Kelahiran'
            ),
        ),
        
        # Add deceased status fields
        migrations.AddField(
            model_name='member',
            name='is_deceased',
            field=models.BooleanField(
                default=False,
                help_text='Centang jika jemaat sudah meninggal dunia',
                verbose_name='Sudah Meninggal'
            ),
        ),
        
        migrations.AddField(
            model_name='member',
            name='deceased_date',
            field=models.DateField(
                blank=True,
                null=True,
                verbose_name='Tanggal Meninggal'
            ),
        ),
        
        migrations.AddField(
            model_name='member',
            name='deceased_reason',
            field=models.TextField(
                blank=True,
                help_text='Opsional: Sebab meninggal atau catatan lainnya',
                verbose_name='Sebab Meninggal / Catatan'
            ),
        ),
        
        # Add indexes
        migrations.AddIndex(
            model_name='member',
            index=models.Index(fields=['family_role'], name='members_family_role_idx'),
        ),
        
        migrations.AddIndex(
            model_name='member',
            index=models.Index(fields=['is_deceased'], name='members_is_deceased_idx'),
        ),
        
        # Add constraint for unique birth_order per family
        migrations.AddConstraint(
            model_name='member',
            constraint=models.UniqueConstraint(
                condition=models.Q(('birth_order__isnull', False), ('family_role', 'CHILD')),
                fields=('family', 'birth_order'),
                name='unique_birth_order_per_family'
            ),
        ),
        
        # Migrate existing data
        migrations.RunPython(migrate_existing_data, reverse_code=migrations.RunPython.noop),
    ]