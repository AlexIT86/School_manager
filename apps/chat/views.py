from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.db.models import Q
from .models import Conversation, Message, ChatAttachment
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.utils import timezone


@login_required
def inbox_view(request):
    conversations = Conversation.objects.filter(participants=request.user).prefetch_related('participants').order_by('-updated_at')

    # Utilizatori și status online
    try:
        active_sessions = Session.objects.filter(expire_date__gte=timezone.now())
        user_ids_online = set()
        for s in active_sessions:
            try:
                data = s.get_decoded()
                uid = int(data.get('_auth_user_id')) if data.get('_auth_user_id') else None
                if uid:
                    user_ids_online.add(uid)
            except Exception:
                continue
    except Exception:
        user_ids_online = set()

    all_users = User.objects.exclude(id=request.user.id).order_by('username')
    return render(request, 'chat/inbox.html', {
        'conversations': conversations,
        'all_users': all_users,
        'user_ids_online': user_ids_online,
    })


@login_required
def conversation_view(request, convo_id):
    convo = get_object_or_404(Conversation, id=convo_id, participants=request.user)
    messages = convo.messages.select_related('sender').prefetch_related('attachments').all()
    # Marchează ca citite
    try:
        for m in messages:
            m.read_by.add(request.user)
    except Exception:
        pass
    try:
        last_id = messages.last().id if messages else 0
    except Exception:
        last_id = 0
    return render(request, 'chat/conversation.html', {'conversation': convo, 'messages': messages, 'last_id': last_id})


@login_required
def start_conversation_view(request):
    if request.method == 'POST':
        username = (request.POST.get('username') or '').strip()
        is_group = bool(request.POST.get('is_group'))
        title = (request.POST.get('title') or '').strip()
        users = []
        if username:
            try:
                users = [User.objects.get(username=username)]
            except User.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Utilizator inexistent'}, status=400)
        # Încearcă să reutilizezi conversațiile 1:1 existente
        convo = None
        if not is_group and users:
            existing = Conversation.objects.filter(is_group=False, participants=request.user).filter(participants=users[0]).first()
            if existing:
                convo = existing
        if convo is None:
            convo = Conversation.objects.create(is_group=is_group, title=title)
            convo.participants.add(request.user, *users)
        return JsonResponse({'success': True, 'conversation_id': convo.id})
    return JsonResponse({'success': False, 'error': 'Metodă invalidă'}, status=405)


@login_required
def send_message_view(request, convo_id):
    convo = get_object_or_404(Conversation, id=convo_id, participants=request.user)
    if request.method == 'POST':
        content = (request.POST.get('content') or '').strip()
        if not content and not request.FILES:
            return JsonResponse({'success': False, 'error': 'Mesajul este gol'}, status=400)
        msg = Message.objects.create(conversation=convo, sender=request.user, content=content)
        # Attachments
        for f in request.FILES.getlist('files'):
            att = ChatAttachment.objects.create(message=msg, file=f, content_type=getattr(f, 'content_type', ''))
        convo.updated_at = msg.created_at
        convo.save(update_fields=['updated_at'])
        return JsonResponse({'success': True, 'message_id': msg.id, 'created_at': timezone.localtime(msg.created_at).strftime('%d.%m.%Y %H:%M'), 'sender': request.user.username})
    return JsonResponse({'success': False, 'error': 'Metodă invalidă'}, status=405)


@login_required
def fetch_messages_view(request, convo_id):
    convo = get_object_or_404(Conversation, id=convo_id, participants=request.user)
    after_id = int(request.GET.get('after_id') or 0)
    qs = convo.messages.select_related('sender').filter(id__gt=after_id).order_by('id')
    data = [
        {
            'id': m.id,
            'sender': m.sender.username,
            'content': m.content,
            'created_at': timezone.localtime(m.created_at).strftime('%d.%m.%Y %H:%M')
        }
        for m in qs
    ]
    # Attachments info
    files_map = {}
    for m in qs:
        arr = []
        for a in m.attachments.all():
            arr.append({'url': a.file.url, 'name': a.name, 'is_image': a.is_image})
        files_map[m.id] = arr
    # Marchează cele noi ca citite
    try:
        for m in qs:
            m.read_by.add(request.user)
    except Exception:
        pass
    return JsonResponse({'success': True, 'messages': data, 'attachments': files_map})


