from django import forms
from django.core.exceptions import ValidationError
from .models import Member, Family, Sector
from django.db.models import Q
import re


class MemberForm(forms.ModelForm):
    """
    Form untuk tambah/edit Member (Jemaat).
    
    Fitur:
    - Photo upload dengan preview
    - Validasi phone number Indonesia
    - Validasi email
    - NIJ readonly (auto-generate)
    - Current sector default dari family sector
    """

    class Meta:
        model = Member
        fields = [
            'full_name', 'gender', 'date_of_birth', 'blood_type',
            'phone_number', 'email', 'photo',
            'family', 'current_sector',
            'baptism_date', 'sidi_date', 'marriage_date',
            'membership_status', 'is_active', 'inactive_reason'
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'input-field',
                'placeholder': 'Nama lengkap jemaat'
            }),
            'gender': forms.Select(attrs={'class': 'input-field'}),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'input-field',
                'type': 'date'
            }),
            'blood_type': forms.Select(attrs={'class': 'input-field'}),
            'phone_number': forms.TextInput(attrs={
                'class': 'input-field',
                'placeholder': '08123456789'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'input-field',
                'placeholder': 'email@example.com'
            }),
            'photo': forms.FileInput(attrs={
                'class': 'input-field',
                'accept': 'image/*'
            }),
            'family': forms.Select(attrs={'class': 'input-field'}),
            'current_sector': forms.Select(attrs={'class': 'input-field'}),
            'baptism_date': forms.DateInput(attrs={
                'class': 'input-field',
                'type': 'date'
            }),
            'sidi_date': forms.DateInput(attrs={
                'class': 'input-field',
                'type': 'date'
            }),
            'marriage_date': forms.DateInput(attrs={
                'class': 'input-field',
                'type': 'date'
            }),
            'membership_status': forms.Select(attrs={'class': 'input-field'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'checkbox'}),
            'inactive_reason': forms.TextInput(attrs={
                'class': 'input-field',
                'placeholder': 'Alasan tidak aktif (opsional)'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set field labels dalam Bahasa Indonesia
        self.fields['full_name'].label = "Nama Lengkap"
        self.fields['gender'].label = "Jenis Kelamin"
        self.fields['date_of_birth'].label = "Tanggal Lahir"
        self.fields['blood_type'].label = "Golongan Darah"
        self.fields['phone_number'].label = "Nomor HP"
        self.fields['email'].label = "Email"
        self.fields['photo'].label = "Foto"
        self.fields['family'].label = "Keluarga"
        self.fields['current_sector'].label = "Sektor Saat Ini"
        self.fields['baptism_date'].label = "Tanggal Baptis"
        self.fields['sidi_date'].label = "Tanggal Sidi"
        self.fields['marriage_date'].label = "Tanggal Nikah"
        self.fields['membership_status'].label = "Status Keanggotaan"
        self.fields['is_active'].label = "Aktif"
        self.fields['inactive_reason'].label = "Alasan Tidak Aktif"
        
        # Set field yang tidak wajib
        self.fields['blood_type'].required = False
        self.fields['phone_number'].required = False
        self.fields['email'].required = False
        self.fields['photo'].required = False
        self.fields['baptism_date'].required = False
        self.fields['sidi_date'].required = False
        self.fields['marriage_date'].required = False
        self.fields['inactive_reason'].required = False
        
        # Jika edit (ada instance), set current_sector default dari family
        if not self.instance.pk and self.initial.get('family'):
            try:
                family = Family.objects.get(pk=self.initial['family'])
                self.fields['current_sector'].initial = family.sector
            except Family.DoesNotExist:
                pass

    def clean_phone_number(self):
        """Validasi format nomor HP Indonesia."""
        phone = self.cleaned_data.get('phone_number', '').strip()
        if not phone:
            return phone
        
        # Hapus spasi dan tanda hubung
        phone = re.sub(r'[\s\-]', '', phone)
        
        # Format valid: 08xxx atau +628xxx atau 628xxx
        if not re.match(r'^(\+?62|0)8\d{8,11}$', phone):
            raise ValidationError(
                'Format nomor HP tidak valid. Gunakan format 08xxxxxxxxxx atau +628xxxxxxxxxx'
            )
        
        # Normalisasi ke format 08xxx
        if phone.startswith('+62'):
            phone = '0' + phone[3:]
        elif phone.startswith('62'):
            phone = '0' + phone[2:]
        
        return phone

    def clean_email(self):
        """Validasi email unik per member."""
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email:
            return email
        
        # Cek duplikasi email (kecuali untuk member yang sedang diedit)
        qs = Member.objects.filter(email=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        
        if qs.exists():
            raise ValidationError('Email ini sudah digunakan oleh jemaat lain.')
        
        return email

    def clean(self):
        """Validasi lintas field."""
        cleaned_data = super().clean()
        
        baptism_date = cleaned_data.get('baptism_date')
        sidi_date = cleaned_data.get('sidi_date')
        date_of_birth = cleaned_data.get('date_of_birth')
        
        # Tanggal baptis harus setelah tanggal lahir
        if baptism_date and date_of_birth:
            if baptism_date < date_of_birth:
                self.add_error('baptism_date', 'Tanggal baptis tidak boleh sebelum tanggal lahir.')
        
        # Tanggal sidi harus setelah baptis
        if sidi_date and baptism_date:
            if sidi_date < baptism_date:
                self.add_error('sidi_date', 'Tanggal sidi tidak boleh sebelum tanggal baptis.')
        
        # Jika tidak aktif, wajib isi alasan
        is_active = cleaned_data.get('is_active')
        inactive_reason = cleaned_data.get('inactive_reason')
        if not is_active and not inactive_reason:
            self.add_error('inactive_reason', 'Alasan tidak aktif wajib diisi.')
        
        return cleaned_data


class MemberSearchForm(forms.Form):
    """Form pencarian jemaat."""
    
    q = forms.CharField(
        required=False,
        label='',
        widget=forms.TextInput(attrs={
            'class': 'input-field',
            'placeholder': 'Cari nama, NIJ, atau nomor HP...',
        })
    )
    
    sector = forms.ModelChoiceField(
        queryset=Sector.objects.all(),
        required=False,
        label='Sektor',
        empty_label='Semua Sektor',
        widget=forms.Select(attrs={'class': 'input-field'})
    )
    
    membership_status = forms.ChoiceField(
        required=False,
        label='Status',
        choices=[('', 'Semua Status')] + list(Member.MembershipStatus.choices),
        widget=forms.Select(attrs={'class': 'input-field'})
    )
    
    is_active = forms.ChoiceField(
        required=False,
        label='Aktif',
        choices=[
            ('', 'Semua'),
            ('true', 'Aktif'),
            ('false', 'Tidak Aktif')
        ],
        widget=forms.Select(attrs={'class': 'input-field'})
    )


class SectorTransferForm(forms.Form):
    """Form untuk pindah sektor."""
    
    new_sector = forms.ModelChoiceField(
        queryset=Sector.objects.all(),
        label='Sektor Baru',
        widget=forms.Select(attrs={'class': 'input-field'})
    )
    
    transfer_date = forms.DateField(
        label='Tanggal Pindah',
        widget=forms.DateInput(attrs={
            'class': 'input-field',
            'type': 'date'
        })
    )
    
    reason = forms.CharField(
        required=False,
        label='Alasan',
        widget=forms.TextInput(attrs={
            'class': 'input-field',
            'placeholder': 'Alasan pindah sektor (opsional)'
        })
    )
    
    notes = forms.CharField(
        required=False,
        label='Catatan',
        widget=forms.Textarea(attrs={
            'class': 'input-field',
            'rows': 3,
            'placeholder': 'Catatan tambahan (opsional)'
        })
    )


# ════════════════════════════════════════════════════════════
# FAMILY FORMS
# ════════════════════════════════════════════════════════════

class FamilyForm(forms.ModelForm):
    """Form untuk tambah/edit Family (Keluarga)."""
    
    class Meta:
        model = Family
        fields = [
            'family_name', 'sector', 'head_of_family',
            'family_status', 'dissolution_reason', 'dissolution_date',
            'address_street', 'address_city', 'address_province',
            'address_postal_code', 'phone_number'
        ]
        widgets = {
            'family_name': forms.TextInput(attrs={
                'class': 'input-field',
                'placeholder': 'Nama keluarga'
            }),
            'sector': forms.Select(attrs={'class': 'input-field'}),
            'head_of_family': forms.Select(attrs={'class': 'input-field'}),
            'family_status': forms.Select(attrs={'class': 'input-field'}),
            'dissolution_reason': forms.TextInput(attrs={
                'class': 'input-field',
                'placeholder': 'Alasan bubar (jika status DISSOLVED)'
            }),
            'dissolution_date': forms.DateInput(attrs={
                'class': 'input-field',
                'type': 'date'
            }),
            'address_street': forms.TextInput(attrs={
                'class': 'input-field',
                'placeholder': 'Jalan dan nomor rumah'
            }),
            'address_city': forms.TextInput(attrs={
                'class': 'input-field',
                'placeholder': 'Kota'
            }),
            'address_province': forms.TextInput(attrs={
                'class': 'input-field',
                'placeholder': 'Provinsi'
            }),
            'address_postal_code': forms.TextInput(attrs={
                'class': 'input-field',
                'placeholder': 'Kode pos'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'input-field',
                'placeholder': '08123456789'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set labels
        self.fields['family_name'].label = "Nama Keluarga"
        self.fields['sector'].label = "Sektor"
        self.fields['head_of_family'].label = "Kepala Keluarga"
        self.fields['family_status'].label = "Status Keluarga"
        self.fields['dissolution_reason'].label = "Alasan Bubar"
        self.fields['dissolution_date'].label = "Tanggal Bubar"
        self.fields['address_street'].label = "Alamat Jalan"
        self.fields['address_city'].label = "Kota"
        self.fields['address_province'].label = "Provinsi"
        self.fields['address_postal_code'].label = "Kode Pos"
        self.fields['phone_number'].label = "Nomor Telepon"
        
        # Optional fields
        self.fields['head_of_family'].required = False
        self.fields['dissolution_reason'].required = False
        self.fields['dissolution_date'].required = False
        self.fields['address_postal_code'].required = False
        
        # Filter head_of_family choices - only active members
        if self.instance.pk:
            # Edit: show members from this family + current head
            self.fields['head_of_family'].queryset = Member.objects.filter(
                Q(family=self.instance, is_active=True) |
                Q(pk=self.instance.head_of_family_id)
            ).distinct()
        else:
            # Create: show all active members
            self.fields['head_of_family'].queryset = Member.objects.filter(
                is_active=True
            )
    
    def clean_phone_number(self):
        """Validasi format nomor HP Indonesia."""
        phone = self.cleaned_data.get('phone_number', '').strip()
        if not phone:
            raise ValidationError('Nomor telepon wajib diisi.')
        
        # Hapus spasi dan tanda hubung
        phone = re.sub(r'[\s\-]', '', phone)
        
        # Format valid: 08xxx atau +628xxx atau 628xxx
        if not re.match(r'^(\+?62|0)8\d{8,11}$', phone):
            raise ValidationError(
                'Format nomor HP tidak valid. Gunakan format 08xxxxxxxxxx'
            )
        
        # Normalisasi ke format 08xxx
        if phone.startswith('+62'):
            phone = '0' + phone[3:]
        elif phone.startswith('62'):
            phone = '0' + phone[2:]
        
        return phone
    
    def clean(self):
        """Validasi lintas field."""
        cleaned_data = super().clean()
        
        family_status = cleaned_data.get('family_status')
        dissolution_reason = cleaned_data.get('dissolution_reason')
        dissolution_date = cleaned_data.get('dissolution_date')
        
        # Jika status DISSOLVED, wajib isi dissolution fields
        if family_status == Family.FamilyStatus.DISSOLVED:
            if not dissolution_reason:
                self.add_error('dissolution_reason', 
                    'Alasan bubar wajib diisi jika status Bubar.')
            if not dissolution_date:
                self.add_error('dissolution_date', 
                    'Tanggal bubar wajib diisi jika status Bubar.')
        
        return cleaned_data


class FamilySearchForm(forms.Form):
    """Form pencarian keluarga."""
    
    q = forms.CharField(
        required=False,
        label='',
        widget=forms.TextInput(attrs={
            'class': 'input-field',
            'placeholder': 'Cari nama keluarga atau alamat...',
        })
    )
    
    sector = forms.ModelChoiceField(
        queryset=Sector.objects.all(),
        required=False,
        label='Sektor',
        empty_label='Semua Sektor',
        widget=forms.Select(attrs={'class': 'input-field'})
    )
    
    family_status = forms.ChoiceField(
        required=False,
        label='Status',
        choices=[('', 'Semua Status')] + list(Family.FamilyStatus.choices),
        widget=forms.Select(attrs={'class': 'input-field'})
    )


# ════════════════════════════════════════════════════════════
# SECTOR FORMS
# ════════════════════════════════════════════════════════════

class SectorForm(forms.ModelForm):
    """Form untuk tambah/edit Sector."""
    
    class Meta:
        model = Sector
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'input-field',
                'placeholder': 'Nama sektor'
            }),
            'description': forms.Textarea(attrs={
                'class': 'input-field',
                'rows': 3,
                'placeholder': 'Keterangan atau deskripsi sektor (opsional)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].label = "Nama Sektor"
        self.fields['description'].label = "Keterangan"
        self.fields['description'].required = False