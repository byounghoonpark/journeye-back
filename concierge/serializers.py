from rest_framework import serializers
from .models import AIConcierge, ConciergeAssignment
from spaces.models import BaseSpacePhoto, Space
from django.contrib.gis.geos import Point


class BaseSpacePhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaseSpacePhoto
        fields = ['image']


class SpaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Space
        fields = ['name', 'price']


class ConciergeAssignmentSerializer(serializers.ModelSerializer):
    basespace_photos = serializers.SerializerMethodField()
    usage_time = serializers.SerializerMethodField()

    class Meta:
        model = ConciergeAssignment
        fields = ['basespace', 'name','usage_time', 'instructions', 'basespace_photos']

    def get_basespace_photos(self, obj):
        photos = BaseSpacePhoto.objects.filter(basespace=obj.basespace)
        return BaseSpacePhotoSerializer(photos, many=True).data

    def get_usage_time(self, obj):
        return obj.usage_time.strftime('%I:%M %p')



class AIConciergeSerializer(serializers.ModelSerializer):
    assignments = ConciergeAssignmentSerializer(many=True, read_only=True)
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()

    class Meta:
        model = AIConcierge
        fields = ['name', 'description', 'latitude', 'longitude', 'assignments']

    def get_longitude(self, obj):
        return obj.location.x

    def get_latitude(self, obj):
        return obj.location.y


class AIConciergeCreateSerializer(serializers.ModelSerializer):
    latitude = serializers.FloatField(write_only=True)
    longitude = serializers.FloatField(write_only=True)

    class Meta:
        model = AIConcierge
        fields = ['name', 'description', 'latitude', 'longitude']

    def create(self, validated_data):
        latitude = validated_data.pop('latitude')
        longitude = validated_data.pop('longitude')
        validated_data['location'] = Point(longitude, latitude)
        return super().create(validated_data)


class ConciergeAssignmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConciergeAssignment
        fields = ['concierge', 'basespace', 'usage_time', 'instructions']