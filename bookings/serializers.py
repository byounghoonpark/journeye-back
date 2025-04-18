from rest_framework import serializers
from django.contrib.auth.models import User

from chat.models import ChatRoom
from spaces.models import HotelRoomMemo, HotelRoomHistory
from .models import CheckIn, Reservation, Review, ReviewPhoto, Like
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
        fields = ['phone_number', 'nationality']

class ReservationSerializer(serializers.ModelSerializer):
    """예약 정보를 저장하는 시리얼라이저"""
    class Meta:
        model = Reservation
        fields = ['id', 'user', 'space', 'start_date', 'start_time', 'end_date', 'end_time', 'people', 'is_approved']

class ReservationPeopleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = ['guest']

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
    room_id = serializers.IntegerField(required=True, help_text="객실 ID")
    is_day_use = serializers.BooleanField(required=False, help_text="대실 여부 (워크인 고객인 경우)")
    start_date = serializers.DateField(required=False, help_text="체크인 날짜 (워크인 고객인 경우)")
    start_time = serializers.TimeField(required=False, help_text="체크인 시간 (워크인 고객인 경우)")
    end_date = serializers.DateField(required=True, help_text="체크아웃 날짜")
    end_time = serializers.TimeField(required=True, help_text="체크아웃 시간")
    people = serializers.CharField(required=False, help_text="인원 수 (워크인 고객인 경우)")
    nationality = serializers.CharField(required=False, help_text="국적 (워크인 고객인 경우)")
    language = serializers.CharField(required=False, help_text="언어 (워크인 고객인 경우)")
    guest_name = serializers.CharField(required=False, help_text="이름 (워크인 고객인 경우)")
    email = serializers.EmailField(required=False, help_text="이메일 (워크인 고객인 경우)")
    phone = serializers.CharField(required=False, allow_blank=True, help_text="전화번호 (워크인 고객인 경우)")
    guest = serializers.JSONField(required=True, help_text="예약 인원")

class CheckInResponseSerializer(serializers.ModelSerializer):
    """체크인 응답 시리얼라이저"""
    user = UserSerializer()
    reservation = ReservationSerializer()

    class Meta:
        model = CheckIn
        fields = ['id', 'user', 'reservation', 'check_in_date', 'check_in_time', 'check_out_date', 'check_out_time', 'temp_code', 'is_day_use']


class CheckInUpdateSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=True)
    guest = serializers.JSONField(required=False)

    class Meta:
        model = CheckIn
        fields = ['id', 'is_day_use', 'check_in_date', 'check_in_time', 'check_out_date', 'check_out_time', 'guest']

    def update(self, instance, validated_data):
        guest_data = validated_data.pop('guest', None)

        # CheckIn 인스턴스 업데이트
        instance = super().update(instance, validated_data)

        # Reservation 인스턴스 업데이트
        if guest_data:
            reservation = instance.reservation
            reservation.guest = guest_data
            reservation.save()

        return instance

class CheckOutRequestSerializer(serializers.Serializer):
    room_id = serializers.CharField(required=True, help_text="체크아웃할 객실 ID")

    def validate(self, data):
        """현재 체크인 중인 고객이 있는지 확인"""
        check_in = CheckIn.objects.filter(hotel_room__id=data["room_id"]).first()
        if not check_in:
            raise serializers.ValidationError("현재 체크인 중인 고객이 없습니다.")
        return data


class ReviewSerializer(serializers.ModelSerializer):
    photos = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            'id', 'user', 'check_in', 'content', 'rating', 'created_at', 'updated_at', 'photos'
        ]
        read_only_fields = ["user"]

    def get_photos(self, obj):
        return [photo.image.url for photo in obj.photos.all()]

    def create(self, validated_data):
        photos = validated_data.pop("photos", [])

        review = Review.objects.create(**validated_data)

        # 사진 저장
        for photo in photos:
            ReviewPhoto.objects.create(review=review, image=photo)

        return review

    def update(self, instance, validated_data):
        photos = validated_data.pop("photos", [])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # 새로운 사진 저장
        for photo in photos:
            ReviewPhoto.objects.create(review=instance, image=photo)

        return instance

class HotelRoomMemoSerializer(serializers.ModelSerializer):
    class Meta:
        model = HotelRoomMemo
        fields = '__all__'


class HotelRoomHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = HotelRoomHistory
        fields = '__all__'


class CheckInCustomerUpdateSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=True)
    guest_name = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False)
    nationality = serializers.CharField(required=False)
    language = serializers.CharField(required=False)


class UserReservationSerializer(serializers.ModelSerializer):
    checkin_id = serializers.SerializerMethodField()
    hotel_name = serializers.CharField(source='space.basespace.name')
    space_name = serializers.CharField(source='space.name')
    hotel_address = serializers.CharField(source='space.basespace.address')
    hotel_phone = serializers.CharField(source='space.basespace.phone')
    checkin_status = serializers.SerializerMethodField()
    has_review = serializers.SerializerMethodField()
    has_chatroom = serializers.SerializerMethodField()
    reservation_date = serializers.SerializerMethodField()
    start_date = serializers.SerializerMethodField()
    end_date = serializers.SerializerMethodField()
    space_photo = serializers.SerializerMethodField()

    class Meta:
        model = Reservation
        fields = [
            'checkin_id', 'reservation_date', 'hotel_name', 'space_name', 'start_date', 'end_date',
            'hotel_address', 'hotel_phone', 'checkin_status', 'has_review', 'has_chatroom', 'space_photo'
        ]

    def get_checkin_id(self, obj):
        checkin = CheckIn.objects.filter(reservation=obj).first()
        return checkin.id if checkin else None

    def get_checkin_status(self, obj):
        return CheckIn.objects.filter(reservation=obj).exists()

    def get_has_review(self, obj):
        checkin = CheckIn.objects.filter(reservation=obj).first()
        return Review.objects.filter(check_in=checkin).exists() if checkin else False

    def get_has_chatroom(self, obj):
        checkin = CheckIn.objects.filter(reservation=obj).first()
        if checkin:
            chatroom = ChatRoom.objects.filter(checkin=checkin).first()
            return chatroom.id if chatroom else []
        return []

    def get_reservation_date(self, obj):
        return obj.reservation_date.strftime('%m/%d/%Y')

    def get_start_date(self, obj):
        return obj.start_date.strftime('%m/%d/%Y')

    def get_end_date(self, obj):
        return obj.end_date.strftime('%m/%d/%Y')

    def get_space_photo(self, obj):
        return obj.space.photos.first().image.url if obj.space.photos.exists() else None


class CheckInReservationSerializer(serializers.ModelSerializer):
    hotel_name = serializers.CharField(source='hotel_room.room_type.basespace.name')
    room_type = serializers.CharField(source='hotel_room.room_type.name')
    start_date = serializers.SerializerMethodField()
    end_date = serializers.SerializerMethodField()
    hotel_address = serializers.CharField(source='hotel_room.room_type.basespace.address')
    room_photo = serializers.SerializerMethodField()

    class Meta:
        model = CheckIn
        fields = ['hotel_name', 'room_type', 'start_date', 'end_date', 'hotel_address', 'room_photo']

    def get_room_photo(self, obj):
        return obj.hotel_room.room_type.photos.first().image.url if obj.hotel_room.room_type.photos.exists() else None

    def get_start_date(self, obj):
        return obj.reservation.start_date.strftime('%m/%d/%Y')

    def get_end_date(self, obj):
        return obj.reservation.end_date.strftime('%m/%d/%Y')


class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        fields = ['id', 'user', 'basespace', 'created_at']