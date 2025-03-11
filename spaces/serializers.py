from rest_framework import serializers
from spaces.models import Hotel, SpacePhoto, HotelRoom, HotelRoomType, BaseSpacePhoto, Floor
from django.contrib.gis.geos import Point

class HotelSerializer(serializers.ModelSerializer):
    latitude = serializers.FloatField(required=True, write_only=True, help_text="위도 (예: 37.5665)")
    longitude = serializers.FloatField(required=True, write_only=True, help_text="경도 (예: 126.9780)")
    photos = serializers.SerializerMethodField()

    class Meta:
        model = Hotel
        fields = [
            "id", "name", "address", "phone", "introduction",
            "latitude", "longitude", "additional_services", "facilities",
            "photos",
        ]

    def get_latitude(self, obj):
        return obj.location.y if obj.location else None  # GeoDjango: y = 위도

    def get_longitude(self, obj):
        return obj.location.x if obj.location else None  # GeoDjango: x = 경도

    def get_photos(self, obj):
        return [photo.image.url for photo in obj.photos.all()]

    def create(self, validated_data):
        photos = validated_data.pop("photos", [])
        latitude = validated_data.pop("latitude")
        longitude = validated_data.pop("longitude")
        validated_data["location"] = Point(longitude, latitude)
        hotel = Hotel.objects.create(**validated_data)

        for photo in photos:
            BaseSpacePhoto.objects.create(basespace=hotel, image=photo)

        return hotel

    def update(self, instance, validated_data):
        photos = validated_data.pop("photos", [])
        latitude = validated_data.pop("latitude", None)
        longitude = validated_data.pop("longitude", None)

        if latitude is not None and longitude is not None:
            instance.location = Point(longitude, latitude)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        for photo in photos:
            BaseSpacePhoto.objects.create(basespace=instance, image=photo)

        return instance



class HotelRoomTypeSerializer(serializers.ModelSerializer):
    photos = serializers.SerializerMethodField()

    class Meta:
        model = HotelRoomType
        fields = [
            "id", "name", "nickname", "description", "price", "capacity",
            "view", "photos", "basespace"
        ]

    def get_photos(self, obj):
        return [photo.image.url for photo in obj.photos.all()]

    def create(self, validated_data):
        photos = validated_data.pop("photos", [])  # 업로드된 사진 목록
        basespace = validated_data.get("basespace")

        if not basespace:
            raise serializers.ValidationError({"basespace": "BaseSpace 값이 필요합니다."})

        hotel_room_type = HotelRoomType.objects.create(**validated_data)

        # 사진 저장
        for photo in photos:
            SpacePhoto.objects.create(space=hotel_room_type, image=photo)

        return hotel_room_type

    def update(self, instance, validated_data):
        photos = validated_data.pop("photos", [])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # 새로운 사진 저장
        for photo in photos:
            SpacePhoto.objects.create(space=instance, image=photo)

        return instance

class HotelRoomSerializer(serializers.ModelSerializer):
    room_type = serializers.PrimaryKeyRelatedField(queryset=HotelRoomType.objects.all())

    class Meta:
        model = HotelRoom
        fields = [
            'id',
            'room_type',  # 객실 타입의 ID
            'floor',
            'room_number',
            'status',
            'non_smoking'
        ]

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        # 반환 시 room_type 필드를 해당 룸타입의 이름으로 변경합니다.
        rep['room_type'] = instance.room_type.nickname if instance.room_type else None
        rep['floor'] = instance.floor.floor_number if instance.floor else None
        return rep

    def validate_room_type(self, value):
        # 요청한 사용자가 해당 호텔(BaseSpace) 관리자인지 확인
        user = self.context['request'].user
        if not value.basespace.managers.filter(id=user.id).exists():
            raise serializers.ValidationError("해당 호텔의 관리자가 아닙니다.")
        return value

    def create(self, validated_data):
        return HotelRoom.objects.create(**validated_data)


class FloorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Floor
        fields = '__all__'