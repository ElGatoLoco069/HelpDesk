from django.shortcuts import render
from notifications.models import Notification, NotificationType, UserNotification
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
# Create your views here.

class SendNotification():
    
    def success(request, title, descript, send_to_all, send_to):
        
        type = NotificationType.objects.filter(name__iexact="Sucesso").first()
        
        notification = Notification.objects.create(
            title=title,
            description=descript,
            type=type,
            send_all=send_to_all
        )        

        UserNotification.objects.create(
            notification=notification,
            user=send_to,
            read=False,
            hidden=False
        )


@login_required
def mark_notifications_read(request):

    if request.method == "POST":

        UserNotification.objects.filter(
            user=request.user,
            read=False
        ).update(read=True)

        return JsonResponse({
            "success": True
        })

    return JsonResponse({
        "success": False
    }, status=400)