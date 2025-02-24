from rest_framework import serializers
from spaces.models import Hotel
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
        return Hotel.objects.create(**validated_data)
