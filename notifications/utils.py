from asgiref.sync import sync_to_async
from channels.layers import get_channel_layer
from .models import Notification, NotificationReadStatus

async def send_notification_to_users(user_ids, message):
    channel_layer = get_channel_layer()
    for user_id in user_ids:
        await channel_layer.group_send(
            f"notifications_{user_id}",
            {
                "type": "send_notification",
                "message": {
                    "id": message.get("id"),
                    "title": message.get("title"),
                    "content": message.get("content"),
                    "notification_type": message.get("notification_type"),
                    "created_at": message.get("created_at"),
                    "chat_room": message.get("chat_room")
                }
            }
        )

    # 알림 DB에 저장
    notification = await sync_to_async(Notification.objects.create)(
        sender=message.get("sender"),
        title=message.get("title"),
        content=message.get("content"),
        notification_type=message.get("notification_type"),
        chat_room = message.get("chat_room")
    )
    await sync_to_async(NotificationReadStatus.objects.bulk_create)([
        NotificationReadStatus(notification=notification, recipient_id=user_id)
        for user_id in user_ids
    ],
        batch_size=None,
        ignore_conflicts=False,
        update_conflicts=False,
        update_fields=None,
        unique_fields=None
    )