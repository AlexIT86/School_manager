from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Message


@receiver(post_save, sender=Message)
def notify_new_message(sender, instance: Message, created, **kwargs):
    if not created:
        return
    convo = instance.conversation
    sender_user = instance.sender

    # Creează notificări pentru ceilalți participanți
    try:
        from apps.core.models import Notification
        for user in convo.participants.exclude(id=sender_user.id):
            Notification.objects.create(
                user=user,
                tip='sistem',
                titlu='Mesaj nou',
                mesaj=f'Ai un mesaj nou de la {sender_user.username}.'
            )
    except Exception:
        pass


