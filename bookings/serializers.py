from rest_framework import serializers
from django.contrib.auth.models import User
from .models import CheckIn, Reservation
from accounts.models import UserProfile
from django.utils.timezone import now


class UserSerializer(serializers.ModelSerializer):
    """워크인 고객 정보를 저장하는 시리얼라이저"""
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']

class UserProfileSerializer(serializers.ModelSerializer):
    """워크인 고객의 추가 정보 (국적, 전화번호 등)"""
    class Meta:
        model = UserProfile
        fields = ['phone_number', 'natinality']

class ReservationSerializer(serializers.ModelSerializer):
    """예약 정보를 저장하는 시리얼라이저"""
    class Meta:
        model = Reservation
        fields = ['id', 'user', 'space', 'start_date', 'start_time', 'end_date', 'end_time', 'people']

class CheckInSerializer(serializers.ModelSerializer):
    """체크인 정보를 저장하는 시리얼라이저"""
    class Meta:
        model = CheckIn
        fields = ['id', 'user', 'hotel_room', 'reservation', 'check_in_date', 'check_in_time', 'check_out_date', 'check_out_time', 'temp_code']

class CheckInRequestSerializer(serializers.Serializer):
    """체크인 요청을 위한 시리얼라이저"""
    reservation_id = serializers.IntegerField(required=False, help_text="예약 ID (기존 예약 고객인 경우)")
    user_id = serializers.IntegerField(required=False, help_text="예약한 사용자 ID (기존 예약 고객인 경우)")
    hotel_id = serializers.IntegerField(required=True, help_text="체크인할 호텔 ID")
    room_number = serializers.CharField(required=True, help_text="객실 번호")
    start_date = serializers.DateField(required=False, help_text="체크인 날짜 (워크인 고객인 경우)")
    start_time = serializers.TimeField(required=False, help_text="체크인 시간 (워크인 고객인 경우)")
    end_date = serializers.DateField(required=True, help_text="체크아웃 날짜")
    end_time = serializers.TimeField(required=True, help_text="체크아웃 시간")
    natinality = serializers.CharField(required=False, help_text="국적 (워크인 고객인 경우)")
    first_name = serializers.CharField(required=False, help_text="이름 (워크인 고객인 경우)")
    last_name = serializers.CharField(required=False, help_text="성 (워크인 고객인 경우)")
    email = serializers.EmailField(required=False, help_text="이메일 (워크인 고객인 경우)")
    phone = serializers.CharField(required=False, help_text="전화번호 (워크인 고객인 경우)")

class CheckInResponseSerializer(serializers.ModelSerializer):
    """체크인 응답 시리얼라이저"""
    user = UserSerializer()
    reservation = ReservationSerializer()

    class Meta:
        model = CheckIn
        fields = ['id', 'user', 'reservation', 'check_in_date', 'check_in_time', 'check_out_date', 'check_out_time', 'temp_code']


class CheckOutRequestSerializer(serializers.Serializer):
    room_number = serializers.CharField(required=True, help_text="체크아웃할 객실 번호")

    def validate(self, data):
        """현재 체크인 중인 고객이 있는지 확인"""
        check_in = CheckIn.objects.filter(hotel_room__room_number=data["room_number"], check_out_date__gte=now().date()).first()
        if not check_in:
            raise serializers.ValidationError("현재 체크인 중인 고객이 없습니다.")
        return data
