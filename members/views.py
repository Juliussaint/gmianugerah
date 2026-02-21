from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.template.loader import render_to_string
from .models import Member, Family, Sector, SectorHistory
from .forms import (MemberForm, MemberSearchForm, SectorTransferForm, 
                    FamilyForm, FamilySearchForm, SectorForm)


# ════════════════════════════════════════════════════════════
# MEMBER LIST (HTMX-enabled)
# ════════════════════════════════════════════════════════════
@login_required
def member_list(request):
    """
    Daftar semua jemaat dengan fitur HTMX:
    - Real-time search
    - Dynamic filter
    - Infinite scroll pagination
    """
    members = Member.objects.select_related(
        'family', 'current_sector'
    ).all()
    
    # ── Search & Filter ──
    form = MemberSearchForm(request.GET)
    if form.is_valid():
        q = form.cleaned_data.get('q')
        if q:
            members = members.filter(
                Q(full_name__icontains=q) |
                Q(member_id__icontains=q) |
                Q(phone_number__icontains=q)
            )
        
        sector = form.cleaned_data.get('sector')
        if sector:
            members = members.filter(current_sector=sector)
        
        membership_status = form.cleaned_data.get('membership_status')
        if membership_status:
            members = members.filter(membership_status=membership_status)
        
        is_active = form.cleaned_data.get('is_active')
        if is_active == 'true':
            members = members.filter(is_active=True)
        elif is_active == 'false':
            members = members.filter(is_active=False)
    
    # ── Pagination ──
    paginator = Paginator(members, 20)  # 20 per halaman
    page_num  = request.GET.get('page', 1)
    page_obj  = paginator.get_page(page_num)
    
    context = {
        'page_obj': page_obj,
        'form': form,
        'total_count': members.count(),
    }
    
    # ── HTMX: Return partial HTML untuk table body saja ──
    if request.htmx:
        # Jika infinite scroll (load more)
        if request.GET.get('page'):
            return render(request, 'members/partials/member_rows.html', context)
        # Jika search/filter
        return render(request, 'members/partials/member_table.html', context)
    
    # Full page render
    return render(request, 'members/member_list.html', context)


# ════════════════════════════════════════════════════════════
# MEMBER DETAIL
# ════════════════════════════════════════════════════════════
@login_required
def member_detail(request, pk):
    """Detail informasi 1 jemaat + riwayat sektor."""
    member = get_object_or_404(
        Member.objects.select_related('family', 'current_sector'),
        pk=pk
    )
    
    # Ambil riwayat sektor
    sector_history = member.sector_history.select_related(
        'from_sector', 'to_sector', 'created_by'
    ).order_by('-transfer_date')[:10]
    
    context = {
        'member': member,
        'sector_history': sector_history,
    }
    return render(request, 'members/member_detail.html', context)


# ════════════════════════════════════════════════════════════
# MEMBER CREATE (HTMX Modal)
# ════════════════════════════════════════════════════════════
@login_required
def member_create(request):
    """Tambah jemaat baru via HTMX modal."""
    if request.method == 'POST':
        form = MemberForm(request.POST, request.FILES)
        if form.is_valid():
            member = form.save()
            
            # HTMX: Return success message + new row
            if request.htmx:
                messages.success(
                    request,
                    f'Jemaat {member.full_name} berhasil ditambahkan dengan NIJ {member.member_id}'
                )
                # Trigger client-side refresh atau prepend row baru
                response = HttpResponse(status=204)
                response['HX-Trigger'] = 'memberCreated'
                return response
            
            messages.success(
                request,
                f'Jemaat {member.full_name} berhasil ditambahkan dengan NIJ {member.member_id}'
            )
            return redirect('members:detail', pk=member.pk)
    else:
        form = MemberForm()
    
    context = {
        'form': form,
        'title': 'Tambah Jemaat Baru',
        'submit_text': 'Simpan',
    }
    
    # HTMX: Return modal content only
    if request.htmx:
        return render(request, 'members/partials/member_form_modal.html', context)
    
    return render(request, 'members/member_form.html', context)


# ════════════════════════════════════════════════════════════
# MEMBER UPDATE (HTMX Modal)
# ════════════════════════════════════════════════════════════
@login_required
def member_update(request, pk):
    """Edit data jemaat via HTMX modal."""
    member = get_object_or_404(Member, pk=pk)
    
    if request.method == 'POST':
        form = MemberForm(request.POST, request.FILES, instance=member)
        if form.is_valid():
            form.save()
            
            # HTMX: Return success
            if request.htmx:
                messages.success(request, f'Data {member.full_name} berhasil diperbarui.')
                response = HttpResponse(status=204)
                response['HX-Trigger'] = 'memberUpdated'
                return response
            
            messages.success(request, f'Data {member.full_name} berhasil diperbarui.')
            return redirect('members:detail', pk=member.pk)
    else:
        form = MemberForm(instance=member)
    
    context = {
        'form': form,
        'member': member,
        'title': f'Edit Data {member.full_name}',
        'submit_text': 'Simpan Perubahan',
    }
    
    # HTMX: Return modal content only
    if request.htmx:
        return render(request, 'members/partials/member_form_modal.html', context)
    
    return render(request, 'members/member_form.html', context)


# ════════════════════════════════════════════════════════════
# MEMBER DELETE (HTMX Inline)
# ════════════════════════════════════════════════════════════
@login_required
def member_delete(request, pk):
    """
    Hapus jemaat (soft delete = set is_active=False).
    HTMX: Inline confirmation + row removal.
    """
    member = get_object_or_404(Member, pk=pk)
    
    if request.method == 'POST':
        # Soft delete
        member.is_active = False
        member.inactive_reason = request.POST.get('reason', 'Dihapus oleh admin')
        member.save()
        
        # HTMX: Return empty response to remove row
        if request.htmx:
            messages.warning(
                request,
                f'{member.full_name} telah dinonaktifkan.'
            )
            return HttpResponse(status=204)
        
        messages.warning(
            request,
            f'{member.full_name} telah dinonaktifkan. Data masih tersimpan di database.'
        )
        return redirect('members:list')
    
    context = {'member': member}
    
    # HTMX: Return inline confirmation form
    if request.htmx:
        return render(request, 'members/partials/member_delete_confirm.html', context)
    
    return render(request, 'members/member_confirm_delete.html', context)


# ════════════════════════════════════════════════════════════
# SECTOR TRANSFER (HTMX Modal)
# ════════════════════════════════════════════════════════════
@login_required
def member_transfer_sector(request, pk):
    """Pindahkan jemaat ke sektor lain via HTMX modal."""
    member = get_object_or_404(Member, pk=pk)
    
    if request.method == 'POST':
        form = SectorTransferForm(request.POST)
        if form.is_valid():
            new_sector = form.cleaned_data['new_sector']
            
            # Validasi: tidak boleh pindah ke sektor yang sama
            if new_sector == member.current_sector:
                messages.error(request, 'Sektor tujuan sama dengan sektor saat ini.')
            else:
                # Catat riwayat
                SectorHistory.objects.create(
                    member=member,
                    from_sector=member.current_sector,
                    to_sector=new_sector,
                    transfer_date=form.cleaned_data['transfer_date'],
                    reason=form.cleaned_data.get('reason', ''),
                    notes=form.cleaned_data.get('notes', ''),
                    created_by=request.user,
                )
                
                # Update current_sector
                member.current_sector = new_sector
                member.save()
                
                # HTMX: Return success
                if request.htmx:
                    messages.success(
                        request,
                        f'{member.full_name} berhasil dipindahkan ke {new_sector.name}'
                    )
                    response = HttpResponse(status=204)
                    response['HX-Trigger'] = 'sectorTransferred'
                    return response
                
                messages.success(
                    request,
                    f'{member.full_name} berhasil dipindahkan ke {new_sector.name}'
                )
                return redirect('members:detail', pk=member.pk)
    else:
        import datetime
        form = SectorTransferForm(initial={
            'transfer_date': datetime.date.today()
        })
    
    context = {
        'member': member,
        'form': form,
    }
    
    # HTMX: Return modal content only
    if request.htmx:
        return render(request, 'members/partials/member_transfer_modal.html', context)
    
    return render(request, 'members/member_transfer_sector.html', context)


# ════════════════════════════════════════════════════════════
# FAMILY LIST (HTMX-enabled)
# ════════════════════════════════════════════════════════════
@login_required
def family_list(request):
    """
    Daftar semua keluarga dengan fitur HTMX:
    - Real-time search
    - Dynamic filter
    - Pagination
    """
    families = Family.objects.select_related('sector', 'head_of_family').annotate(
        member_count=Count('members', filter=Q(members__is_active=True), distinct=True)
    ).all()
    
    # ── Search & Filter ──
    form = FamilySearchForm(request.GET)
    if form.is_valid():
        q = form.cleaned_data.get('q')
        if q:
            families = families.filter(
                Q(family_name__icontains=q) |
                Q(address_street__icontains=q) |
                Q(address_city__icontains=q)
            )
        
        sector = form.cleaned_data.get('sector')
        if sector:
            families = families.filter(sector=sector)
        
        family_status = form.cleaned_data.get('family_status')
        if family_status:
            families = families.filter(family_status=family_status)
    
    # ── Pagination ──
    paginator = Paginator(families, 20)
    page_num  = request.GET.get('page', 1)
    page_obj  = paginator.get_page(page_num)
    
    context = {
        'page_obj': page_obj,
        'form': form,
        'total_count': families.count(),
    }
    
    # ── HTMX: Return partial HTML ──
    if request.htmx:
        if request.GET.get('page'):
            return render(request, 'members/partials/family_rows.html', context)
        return render(request, 'members/partials/family_table.html', context)
    
    return render(request, 'members/family_list.html', context)


# ════════════════════════════════════════════════════════════
# FAMILY DETAIL
# ════════════════════════════════════════════════════════════
@login_required
def family_detail(request, pk):
    """Detail informasi 1 keluarga + list members."""
    family = get_object_or_404(
        Family.objects.select_related('sector', 'head_of_family'),
        pk=pk
    )
    
    # Ambil semua anggota keluarga
    members = family.members.select_related('current_sector').all()
    
    context = {
        'family': family,
        'members': members,
        'active_count': members.filter(is_active=True).count(),
    }
    return render(request, 'members/family_detail.html', context)


# ════════════════════════════════════════════════════════════
# FAMILY CREATE (HTMX Modal)
# ════════════════════════════════════════════════════════════
@login_required
def family_create(request):
    """Tambah keluarga baru via HTMX modal."""
    if request.method == 'POST':
        form = FamilyForm(request.POST)
        if form.is_valid():
            family = form.save()
            
            # HTMX: Return success
            if request.htmx:
                messages.success(
                    request,
                    f'Keluarga {family.family_name} berhasil ditambahkan'
                )
                response = HttpResponse(status=204)
                response['HX-Trigger'] = 'familyCreated'
                return response
            
            messages.success(
                request,
                f'Keluarga {family.family_name} berhasil ditambahkan'
            )
            return redirect('members:family_detail', pk=family.pk)
    else:
        form = FamilyForm()
    
    context = {
        'form': form,
        'title': 'Tambah Keluarga Baru',
        'submit_text': 'Simpan',
    }
    
    # HTMX: Return modal content only
    if request.htmx:
        return render(request, 'members/partials/family_form_modal.html', context)
    
    return render(request, 'members/family_form.html', context)


# ════════════════════════════════════════════════════════════
# FAMILY UPDATE (HTMX Modal)
# ════════════════════════════════════════════════════════════
@login_required
def family_update(request, pk):
    """Edit data keluarga via HTMX modal."""
    family = get_object_or_404(Family, pk=pk)
    
    if request.method == 'POST':
        form = FamilyForm(request.POST, instance=family)
        if form.is_valid():
            form.save()
            
            # HTMX: Return success
            if request.htmx:
                messages.success(request, f'Data {family.family_name} berhasil diperbarui.')
                response = HttpResponse(status=204)
                response['HX-Trigger'] = 'familyUpdated'
                return response
            
            messages.success(request, f'Data {family.family_name} berhasil diperbarui.')
            return redirect('members:family_detail', pk=family.pk)
    else:
        form = FamilyForm(instance=family)
    
    context = {
        'form': form,
        'family': family,
        'title': f'Edit Data {family.family_name}',
        'submit_text': 'Simpan Perubahan',
    }
    
    # HTMX: Return modal content only
    if request.htmx:
        return render(request, 'members/partials/family_form_modal.html', context)
    
    return render(request, 'members/family_form.html', context)


# ════════════════════════════════════════════════════════════
# FAMILY DELETE (Soft Delete)
# ════════════════════════════════════════════════════════════
@login_required
def family_delete(request, pk):
    """
    Set family status to INACTIVE (soft delete).
    """
    family = get_object_or_404(Family, pk=pk)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', 'Dihapus oleh admin')
        
        # Set to INACTIVE
        family.family_status = Family.FamilyStatus.INACTIVE
        family.dissolution_reason = reason
        family.dissolution_date = __import__('datetime').date.today()
        family.save()
        
        # HTMX: Return empty response
        if request.htmx:
            messages.warning(
                request,
                f'{family.family_name} telah dinonaktifkan.'
            )
            return HttpResponse(status=204)
        
        messages.warning(
            request,
            f'{family.family_name} telah dinonaktifkan.'
        )
        return redirect('members:family_list')
    
    context = {'family': family}
    
    # HTMX: Return inline confirmation form
    if request.htmx:
        return render(request, 'members/partials/family_delete_confirm.html', context)
    
    return render(request, 'members/family_confirm_delete.html', context)


# ════════════════════════════════════════════════════════════
# SECTOR LIST (HTMX-enabled)
# ════════════════════════════════════════════════════════════
@login_required
def sector_list(request):
    """
    Daftar semua sektor dengan statistik.
    """
    sectors = Sector.objects.annotate(
        family_count=Count('families', filter=Q(families__family_status=Family.FamilyStatus.ACTIVE), distinct=True),
        member_count=Count('members', filter=Q(members__is_active=True), distinct=True)
    ).order_by('name')
    
    context = {
        'sectors': sectors,
        'total_count': sectors.count(),
    }
    
    return render(request, 'members/sector_list.html', context)


# ════════════════════════════════════════════════════════════
# SECTOR DETAIL
# ════════════════════════════════════════════════════════════
@login_required
def sector_detail(request, pk):
    """Detail informasi 1 sektor + list families & members."""
    sector = get_object_or_404(Sector, pk=pk)
    
    # Families in this sector
    families = sector.families.filter(
        family_status=Family.FamilyStatus.ACTIVE
    ).annotate(
        member_count=Count('members', filter=Q(members__is_active=True), distinct=True)
    )
    
    # Members in this sector
    members = sector.members.filter(is_active=True).select_related('family')
    
    context = {
        'sector': sector,
        'families': families,
        'members': members[:10],  # Show first 10
        'family_count': families.count(),
        'member_count': members.count(),
    }
    return render(request, 'members/sector_detail.html', context)


# ════════════════════════════════════════════════════════════
# SECTOR CREATE (HTMX Modal)
# ════════════════════════════════════════════════════════════
@login_required
def sector_create(request):
    """Tambah sektor baru via HTMX modal."""
    if request.method == 'POST':
        form = SectorForm(request.POST)
        if form.is_valid():
            sector = form.save()
            
            # HTMX: Return success
            if request.htmx:
                messages.success(
                    request,
                    f'Sektor {sector.name} berhasil ditambahkan'
                )
                response = HttpResponse(status=204)
                response['HX-Trigger'] = 'sectorCreated'
                return response
            
            messages.success(
                request,
                f'Sektor {sector.name} berhasil ditambahkan'
            )
            return redirect('members:sector_detail', pk=sector.pk)
    else:
        form = SectorForm()
    
    context = {
        'form': form,
        'title': 'Tambah Sektor Baru',
        'submit_text': 'Simpan',
    }
    
    # HTMX: Return modal content only
    if request.htmx:
        return render(request, 'members/partials/sector_form_modal.html', context)
    
    return render(request, 'members/sector_form.html', context)


# ════════════════════════════════════════════════════════════
# SECTOR UPDATE (HTMX Modal)
# ════════════════════════════════════════════════════════════
@login_required
def sector_update(request, pk):
    """Edit data sektor via HTMX modal."""
    sector = get_object_or_404(Sector, pk=pk)
    
    if request.method == 'POST':
        form = SectorForm(request.POST, instance=sector)
        if form.is_valid():
            form.save()
            
            # HTMX: Return success
            if request.htmx:
                messages.success(request, f'Data {sector.name} berhasil diperbarui.')
                response = HttpResponse(status=204)
                response['HX-Trigger'] = 'sectorUpdated'
                return response
            
            messages.success(request, f'Data {sector.name} berhasil diperbarui.')
            return redirect('members:sector_detail', pk=sector.pk)
    else:
        form = SectorForm(instance=sector)
    
    context = {
        'form': form,
        'sector': sector,
        'title': f'Edit Sektor {sector.name}',
        'submit_text': 'Simpan Perubahan',
    }
    
    # HTMX: Return modal content only
    if request.htmx:
        return render(request, 'members/partials/sector_form_modal.html', context)
    
    return render(request, 'members/sector_form.html', context)