from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from accounts.models import UserProfile, UserRole  # UserProfile 모델 사용

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            'profile_picture',
            'nationality',
            'phone_number'
        ]

class UserRegistrationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all(), message="이미 등록된 이메일입니다.")]
    )
    phone_number = serializers.CharField(required=False, allow_blank=True)
    profile_picture = serializers.ImageField(required=False)
    nationality = serializers.CharField(max_length=100, required=False)

    class Meta:
        model = User
        fields = ['email', 'password', 'profile_picture', 'nationality', 'first_name', 'last_name', 'phone_number']

    def create(self, validated_data):
        username = validated_data['first_name'] + ' ' + validated_data['last_name']
        user = User.objects.create_user(
            username=username,
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name']
        )
        UserProfile.objects.create(
            user=user,
            profile_picture=validated_data.get('profile_picture'),
            nationality=validated_data.get('nationality'),
            phone_number=validated_data.get('phone_number'),
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
        instance.role = "MANAGER"
        instance.save()
        return instance

class UserProfileDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['profile_picture', 'nationality', 'email_verified', 'phone_verified']

class UserDetailSerializer(serializers.ModelSerializer):
    profile = UserProfileDetailSerializer()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'profile']


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 기본 serializer에 있는 username 필드를 제거합니다.
        self.fields.pop('username', None)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        if not email or not password:
            raise serializers.ValidationError("이메일과 비밀번호를 입력해주세요.")

        try:
            # 이메일은 회원가입 시 UniqueValidator로 중복검증했으므로 단일 사용자만 존재합니다.
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("해당 이메일의 사용자가 존재하지 않습니다.")

        if not user.check_password(password):
            raise serializers.ValidationError("비밀번호가 올바르지 않습니다.")

        refresh = self.get_token(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }