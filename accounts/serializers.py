from django.contrib.auth.models import User
from rest_framework import serializers
from accounts.models import UserProfile  # UserProfile 모델 사용

class UserRegistrationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"]
        )
        # UserProfile 생성 (기본값: 일반 사용자)
        UserProfile.objects.create(user=user, role="GENERAL")
        return user

class HotelManagerAssignSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ["role"]

    def update(self, instance, validated_data):
        instance.role = "HOTEL_MANAGER"
        instance.save()
        return instance