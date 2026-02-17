from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def dashboard_home(request):
    """Main dashboard view"""
    context = {
        'title': 'Dashboard',
    }
    return render(request, 'dashboard/home.html', context)