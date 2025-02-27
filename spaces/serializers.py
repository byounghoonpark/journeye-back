from rest_framework import serializers
from spaces.models import Hotel, BaseSpacePhoto, SpacePhoto, HotelRoom, HotelRoomType
from django.contrib.gis.geos import Point

class HotelCreateSerializer(serializers.ModelSerializer):
    latitude = serializers.FloatField(write_only=True, required=True, help_text="위도 (예: 37.5665)")
    longitude = serializers.FloatField(write_only=True, required=True, help_text="경도 (예: 126.9780)")

    class Meta:
        model = Hotel
        fields = ["name", "address", "phone", "introduction", "latitude", "longitude"]

    def create(self, validated_data):
        latitude = validated_data.pop("latitude")
        longitude = validated_data.pop("longitude")
        validated_data["location"] = Point(longitude, latitude)  # GeoDjango의 Point 객체 사용
        hotel = Hotel.objects.create(**validated_data)
        request = self.context.get("request")
        if request:
            print("request.FILES keys:", list(request.FILES.keys()))
            photos = request.FILES.getlist("photos")
            print("Number of photos received:", len(photos))
            for image_file in photos:
                BaseSpacePhoto.objects.create(basespace=hotel, image=image_file)
        return hotel


class HotelRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = HotelRoom
        fields = [
            'id',
            'room_type',  # 객실 타입의 ID
            'floor',
            'room_number',
            'room_memo'
        ]

    def validate_room_type(self, value):
        # 요청한 사용자가 해당 호텔(BaseSpace) 관리자인지 확인
        user = self.context['request'].user
        if not value.basespace.managers.filter(id=user.id).exists():
            raise serializers.ValidationError("해당 호텔의 관리자가 아닙니다.")
        return value

    def create(self, validated_data):
        return HotelRoom.objects.create(**validated_data)


class HotelRoomTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = HotelRoomType
        fields = '__all__'

    def validate_basespace(self, value):
        # basespace(호텔)에 대한 관리 권한 검증
        user = self.context['request'].user
        if not value.managers.filter(id=user.id).exists():
            raise serializers.ValidationError("해당 호텔의 관리자가 아닙니다.")
        return value

    def create(self, validated_data):
        # 객실 타입 인스턴스 생성
        instance = HotelRoomType.objects.create(**validated_data)
        request = self.context.get("request")
        if request:
            # 'photos' 키로 전달된 파일 목록을 가져옴
            files = request.FILES.getlist("photos")
            for image in files:
                SpacePhoto.objects.create(space=instance, image=image)
        return instance