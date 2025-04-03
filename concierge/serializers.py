from rest_framework import serializers
from .models import AIConcierge, ConciergeAssignment
from spaces.models import BaseSpacePhoto, Space
from django.contrib.gis.geos import Point
from django.db.models import Sum

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
        fields = ['concierge', 'basespace', 'usage_time', 'instructions', 'name']


class DetailedAIConciergeSerializer(serializers.ModelSerializer):
    assignments = serializers.SerializerMethodField()
    space_prices = serializers.SerializerMethodField()
    full_charge = serializers.SerializerMethodField()
    type_name = serializers.CharField(source='name')
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()

    class Meta:
        model = AIConcierge
        fields = ['type_name', 'description', 'latitude', 'longitude', 'assignments', 'space_prices', 'full_charge']

    def get_assignments(self, obj):
        assignments = ConciergeAssignment.objects.filter(concierge=obj).order_by('usage_time')
        result = []
        for index, assignment in enumerate(assignments):
            basespace = assignment.basespace
            basespace_photo = BaseSpacePhoto.objects.filter(basespace=basespace).first()
            result.append({
                'content_name': assignment.name,
                'usage_time': assignment.usage_time.strftime('%I:%M %p'),
                'instructions': assignment.instructions,
                'phone': basespace.phone if index % 2 == 0 else '',
                'basespace': basespace.pk,
                'basespace_photos': basespace_photo.image.url if basespace_photo and index % 2 == 0 else ''
            })
        return result

    def get_space_prices(self, obj):
        assignments = ConciergeAssignment.objects.filter(concierge=obj)
        spaces = Space.objects.filter(basespace__concierge_assignments__in=assignments)
        return SpaceSerializer(spaces, many=True).data

    def get_full_charge(self, obj):
        assignments = ConciergeAssignment.objects.filter(concierge=obj)
        spaces = Space.objects.filter(basespace__concierge_assignments__in=assignments)
        return spaces.aggregate(Sum('price'))['price__sum']

    def get_latitude(self, obj):
        return obj.location.y

    def get_longitude(self, obj):
        return obj.location.x