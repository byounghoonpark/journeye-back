from django.contrib.auth.models import User
from rest_framework import serializers
from accounts.models import UserProfile, UserRole  # UserProfile 모델 사용

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            'profile_picture',
            'nationality',
        ]

class UserRegistrationSerializer(serializers.ModelSerializer):
    profile_picture = serializers.ImageField(required=False)
    nationality = serializers.CharField(max_length=100, required=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'profile_picture', 'nationality']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        UserProfile.objects.create(
            user=user,
            profile_picture=validated_data.get('profile_picture'),
            nationality=validated_data.get('nationality'),
            role='GENERAL',
            email_verified=False,
            phone_verified=False
        )
        return user

class SpaceManagerAssignSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ["role"]

    def update(self, instance, validated_data):
        instance.role = "SPACE_MANAGER"
        instance.save()
        return instance