from django.db import models
from django.contrib.auth.models import User
from enum import Enum

class ChoiceEnum(Enum):
    @classmethod
    def choices(cls):
        return [(choice.name, choice.value) for choice in cls]

class UserRole(ChoiceEnum):
    GENERAL = "일반 사용자"
    SUPER_ADMIN = "수퍼 관리자"
    HOTEL_MANAGER = "호텔 관리자"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, unique=True)
    password = models.CharField(max_length=128)
    email_verified = models.BooleanField(default=False, verbose_name='이메일 인증 여부')
    phone_verified = models.BooleanField(default=False, verbose_name='휴대폰 인증 여부')
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True, verbose_name='프로필 사진')
    nationality = models.CharField(max_length=100, blank=True, null=True,verbose_name='국적')
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices(),
        default=UserRole.GENERAL.name,
        verbose_name="유저 역할"
    )