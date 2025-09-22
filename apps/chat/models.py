from django.db import models
from django.contrib.auth.models import User


class Conversation(models.Model):
    """O conversație (thread) între 2 sau mai mulți utilizatori."""
    participants = models.ManyToManyField(User, related_name='conversations')
    title = models.CharField(max_length=200, blank=True)
    is_group = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.title or f"Conversație #{self.id}"


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read_by = models.ManyToManyField(User, related_name='read_messages', blank=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.username}: {self.content[:30]}"


class ChatAttachment(models.Model):
    """Fișiere atașate la mesaje (imagini, documente etc.)."""
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='chat/')
    name = models.CharField(max_length=200, blank=True)
    size = models.PositiveIntegerField(default=0)
    content_type = models.CharField(max_length=100, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.file and not self.size:
            try:
                self.size = self.file.size
            except Exception:
                self.size = 0
        if self.file and not self.name:
            try:
                import os
                self.name = os.path.basename(self.file.name)
            except Exception:
                pass
        super().save(*args, **kwargs)

    @property
    def is_image(self) -> bool:
        try:
            return (self.content_type or '').startswith('image/') or self.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))
        except Exception:
            return False


