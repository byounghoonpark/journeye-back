from geopy.distance import geodesic
from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils.timezone import localtime, now
from django.utils.translation import gettext_lazy as _
from accounts.models import UserProfile
from bookings.models import Review, ReviewPhoto, Like
from concierge.models import AIConcierge
from spaces.models import (
    Hotel,
    Facility,
    SpacePhoto,
    HotelRoom,
    HotelRoomType,
    BaseSpacePhoto,
    Floor,
    Service
)
from django.contrib.gis.geos import Point
from django.db.models import Avg

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
        validated_data.setdefault("star_rating", 1)
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

class ReviewUserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['profile_picture', 'nationality', 'language']

class ReviewUserSerializer(serializers.ModelSerializer):
    profile = ReviewUserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['username', 'profile']

class HotelReviewSerializer(serializers.ModelSerializer):
    user = ReviewUserSerializer(read_only=True)
    created_at = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ['id', 'user', 'check_in', 'content', 'rating', 'created_at']

    def get_created_at(self, obj):
        created_at = localtime(obj.created_at)
        today = localtime(now()).date()
        delta = today - created_at.date()

        if delta.days == 0:
            return created_at.strftime("%I:%M %p")
        elif delta.days == 1:
            return _("Yesterday")
        elif 2 <= delta.days <= 5:
            return _("%d days ago") % delta.days
        else:
            return created_at.strftime("%m/%d/%Y")


class HotelDetailSerializer(serializers.ModelSerializer):
    services = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    nearby_basespaces = serializers.SerializerMethodField()
    photos = serializers.SerializerMethodField()
    review_photos = serializers.SerializerMethodField()
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    nearby_aiconcierges = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()
    star_rating = serializers.SerializerMethodField()

    class Meta:
        model = Hotel
        fields = [
            'id', 'photos', 'name', 'introduction', 'latitude', 'longitude', 'address', 'phone', 'star_rating',
            'services', 'average_rating', 'review_count', 'nearby_basespaces', 'nearby_aiconcierges', 'review_photos',
            'reviews', 'like_count'
        ]

    def get_star_rating(self, obj):
        return obj.star_rating if obj.star_rating is not None else 0

    def get_like_count(self, obj):
        return Like.objects.filter(basespace=obj).count()

    def get_services(self, obj):
        services = Service.objects.filter(basespace=obj)
        return [{'name': service.name, 'description': service.description, 'price': service.price} for service in services]

    def get_nearby_basespaces(self, obj):
        nearby_facilities = Facility.objects.filter(location__distance_lte=(obj.location, 1000))
        hotel_location = (obj.location.y, obj.location.x)
        result = []
        for facility in nearby_facilities:
            facility_location = (facility.location.y, facility.location.x)
            distance = round(geodesic(hotel_location, facility_location).meters)
            result.append({
                'name': facility.name,
                'address': facility.address,
                'phone': facility.phone,
                'latitude': facility.location.y if facility.location else None,
                'longitude': facility.location.x if facility.location else None,
                'photo': facility.photos.first().image.url if facility.photos.exists() else None,
                'basespace_id': facility.basespace_ptr_id,
                'distance': distance
            })
        return result

    def get_reviews(self, obj):
        reviews = Review.objects.filter(check_in__hotel_room__room_type__basespace=obj)
        return HotelReviewSerializer(reviews, many=True).data

    def get_average_rating(self, obj):
        reviews = Review.objects.filter(check_in__hotel_room__room_type__basespace=obj)
        if reviews.exists():
            return reviews.aggregate(average_rating=Avg('rating'))['average_rating']
        return 0

    def get_review_count(self, obj):
        return Review.objects.filter(check_in__hotel_room__room_type__basespace=obj).count()

    def get_photos(self, obj):
        return [photo.image.url for photo in obj.photos.all()]

    def get_review_photos(self, obj):
        review_photos = ReviewPhoto.objects.filter(review__check_in__hotel_room__room_type__basespace=obj).order_by('-id')[:20]
        return [photo.image.url for photo in review_photos]

    def get_latitude(self, obj):
        return obj.location.y if obj.location else None

    def get_longitude(self, obj):
        return obj.location.x if obj.location else None

    def get_nearby_aiconcierges(self, obj):
        nearby_concierges = AIConcierge.objects.filter(location__distance_lte=(obj.location, 5000))
        return [{'pk': concierge.pk, 'name': concierge.name} for concierge in nearby_concierges]


class FacilitySerializer(serializers.ModelSerializer):
    photos = serializers.SerializerMethodField()
    latitude = serializers.FloatField(required=True, write_only=True, help_text="위도 (예: 37.5665)")
    longitude = serializers.FloatField(required=True, write_only=True, help_text="경도 (예: 126.9780)")

    class Meta:
        model = Facility
        fields = ['id', 'name', 'address', 'phone', 'introduction', 'is_featured', 'facility_type', 'opening_time',
                  'closing_time', 'latitude', 'longitude', 'photos', 'additional_info']

    def get_photos(self, obj):
        return [photo.image.url for photo in obj.photos.all()]

    def create(self, validated_data):
        latitude = validated_data.pop('latitude')
        longitude = validated_data.pop('longitude')
        validated_data['location'] = Point(longitude, latitude)
        photos = self.context['request'].FILES.getlist('photos')
        facility = Facility.objects.create(**validated_data)

        for photo in photos:
            BaseSpacePhoto.objects.create(basespace=facility, image=photo)

        return facility

    def update(self, instance, validated_data):
        latitude = validated_data.pop('latitude', None)
        longitude = validated_data.pop('longitude', None)

        if latitude is not None and longitude is not None:
            instance.location = Point(longitude, latitude)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        photos = self.context['request'].FILES.getlist('photos')
        for photo in photos:
            BaseSpacePhoto.objects.create(basespace=instance, image=photo)

        return instance


class FacilityDetailSerializer(serializers.ModelSerializer):
    nearby_basespaces = serializers.SerializerMethodField()
    photos = serializers.SerializerMethodField()
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    nearby_aiconcierges = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()

    class Meta:
        model = Facility
        fields = [
            'id', 'photos', 'name', 'introduction', 'latitude', 'longitude', 'address', 'phone', 'facility_type',
            'opening_time', 'closing_time', 'additional_info', 'nearby_basespaces', 'nearby_aiconcierges', 'like_count'
        ]


    def get_like_count(self, obj):
        return Like.objects.filter(basespace=obj).count()

    def get_nearby_basespaces(self, obj):
        nearby_basespaces = Hotel.objects.filter(location__distance_lte=(obj.location, 1000))
        return [{
            'name': hotel.name,
            'address': hotel.address,
            'phone': hotel.phone,
            'latitude': hotel.location.y if hotel.location else None,
            'longitude': hotel.location.x if hotel.location else None,
            'photo': hotel.photos.first().image.url if hotel.photos.exists() else None,
            'basespace_id': hotel.basespace_ptr_id
        } for hotel in nearby_basespaces]

    def get_photos(self, obj):
        return [photo.image.url for photo in obj.photos.all()]

    def get_latitude(self, obj):
        return obj.location.y if obj.location else None

    def get_longitude(self, obj):
        return obj.location.x if obj.location else None

    def get_nearby_aiconcierges(self, obj):
        nearby_concierges = AIConcierge.objects.filter(location__distance_lte=(obj.location, 1000))
        return [{'pk': concierge.pk, 'name': concierge.name} for concierge in nearby_concierges]