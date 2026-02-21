from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from members.models import Member, Family, Sector
import datetime


@login_required
def dashboard_home(request):
    """
    Dashboard utama dengan statistik real-time dari database.
    """
    
    # ── Basic Stats ──
    total_members = Member.objects.filter(is_active=True).count()
    total_families = Family.objects.filter(family_status=Family.FamilyStatus.ACTIVE).count()
    total_sectors = Sector.objects.count()
    
    # Members this month
    today = datetime.date.today()
    first_day_of_month = today.replace(day=1)
    members_this_month = Member.objects.filter(
        created_at__gte=first_day_of_month,
        is_active=True
    ).count()
    
    # Inactive members
    inactive_members = Member.objects.filter(is_active=False).count()
    
    # Membership status breakdown
    full_members = Member.objects.filter(
        is_active=True,
        membership_status=Member.MembershipStatus.FULL
    ).count()
    
    preparation_members = Member.objects.filter(
        is_active=True,
        membership_status=Member.MembershipStatus.PREPARATION
    ).count()
    
    # ── Attendance Stats (Placeholder for Phase 2) ──
    # TODO: Replace with real attendance data in Phase 2
    attendance_this_week = 0
    attendance_percent = 0
    attendance_chart_data = [0, 0, 0, 0, 0, 0, 0, 0]
    attendance_chart_labels = [
        "8 minggu lalu", "7 minggu lalu", "6 minggu lalu", "5 minggu lalu",
        "4 minggu lalu", "3 minggu lalu", "2 minggu lalu", "Minggu lalu"
    ]
    
    # ── Recent Members ──
    recent_members = Member.objects.select_related(
        'family', 'current_sector'
    ).filter(is_active=True).order_by('-created_at')[:5]
    
    # ── Upcoming Birthdays (Next 7 days) ──
    upcoming_birthdays = []
    for i in range(7):
        check_date = today + datetime.timedelta(days=i)
        members_on_day = Member.objects.filter(
            is_active=True,
            date_of_birth__month=check_date.month,
            date_of_birth__day=check_date.day
        ).select_related('family', 'current_sector')
        
        for member in members_on_day:
            member.days_until = i
            upcoming_birthdays.append(member)
    
    # Sort by days until birthday
    upcoming_birthdays.sort(key=lambda x: x.days_until)
    
    # ── Absent Members Alert (Placeholder for Phase 2) ──
    # TODO: Get members who haven't attended in 4+ weeks
    absent_members = []
    
    context = {
        # Stats for cards
        'stats': {
            'total_members': total_members,
            'members_this_month': members_this_month,
            'total_families': total_families,
            'total_sectors': total_sectors,
            'attendance_this_week': attendance_this_week,
            'attendance_percent': attendance_percent,
            'inactive_members': inactive_members,
            'full_members': full_members,
            'preparation_members': preparation_members,
        },
        
        # Chart data
        'attendance_chart_data': attendance_chart_data,
        'attendance_chart_labels': attendance_chart_labels,
        
        # Lists
        'recent_members': recent_members,
        'upcoming_birthdays': upcoming_birthdays[:5],  # Max 5
        'absent_members': absent_members,
    }
    
    return render(request, 'dashboard/home.html', context)