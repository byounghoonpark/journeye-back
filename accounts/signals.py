from django.db.models.signals import pre_save
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

def validate_unique_email(sender, instance, **kwargs):
    """모든 앱에서 `User` 모델 저장 시 이메일 중복 검사"""
    if User.objects.filter(email=instance.email).exclude(pk=instance.pk).exists():
        raise ValidationError("이미 등록된 이메일입니다.")

pre_save.connect(validate_unique_email, sender=User)
