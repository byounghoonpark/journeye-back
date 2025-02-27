from django.contrib.gis.db import models as gis_models
from django.db import models
from django.contrib.auth.models import User


# BaseSpace를 추상 모델이 아니라 구체 모델로 변경
class BaseSpace(gis_models.Model):
    name = models.CharField(max_length=255, verbose_name='이름')
    location = gis_models.PointField(geography=True, verbose_name='위치')
    address = models.CharField(max_length=255, verbose_name='주소')
    phone = models.CharField(max_length=20, verbose_name='전화번호')
    introduction = models.TextField(verbose_name='소개글')
    managers = models.ManyToManyField(
        User,
        blank=True,
        related_name='managed_spaces',
        verbose_name = '관리자',
        help_text="이 공간을 관리하는 사용자들"
    )

    def __str__(self):
        return self.name


class BaseSpacePhoto(models.Model):
    basespace = models.ForeignKey(BaseSpace, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='basespace_photos/', verbose_name='공간 사진')

    def __str__(self):
        return f"Photo for {self.basespace.name}"


# Hotel은 다중 테이블 상속 사용 (BaseSpace를 상속)
class Hotel(BaseSpace):
    additional_services = models.TextField(blank=True, null=True, verbose_name='부가서비스')
    facilities = models.TextField(blank=True, null=True, verbose_name='시설안내')

    # Hotel 고유 필드가 더 있다면 추가
    def __str__(self):
        return self.name


# Restaurant도 BaseSpace를 상속받음
class Restaurant(BaseSpace):
    # Restaurant 전용 필드가 있다면 추가
    def __str__(self):
        return self.name

class Service(models.Model):
    basespace = models.ForeignKey(
        BaseSpace,
        on_delete=models.CASCADE,
        related_name='services',
        help_text="이 서비스가 제공되는 공간 (호텔, 식당 등)"
    )
    name = models.CharField(max_length=255, verbose_name='서비스 이름')
    description = models.TextField(blank=True, null=True, verbose_name='서비스 설명')
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='가격',
        help_text="서비스 가격 (무료이면 null 또는 0)"
    )
    available = models.BooleanField(default=True, verbose_name='이용 가능 여부')

    def __str__(self):
        return f"{self.name} for {self.basespace.name}"

# Space: 예약 가능한 구체적인 단위(예: 호텔의 객실, 식당의 테이블 등)
# BaseSpace와 일반 ForeignKey로 연결하여 어느 공간에 속하는지 지정합니다.
class Space(models.Model):
    name = models.CharField(max_length=255, verbose_name='호실 또는 테이블명')
    description = models.TextField(blank=True, verbose_name='설명')
    # price 테이블 따로 빼서 시즌별 요금제 바뀔수있어야함
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='가격')
    capacity = models.PositiveIntegerField(null=True, blank=True, verbose_name='수용 인원')
    basespace = models.ForeignKey(BaseSpace, on_delete=models.CASCADE, related_name='spaces')

    def __str__(self):
        return f"{self.name} at {self.basespace.name}"


class HotelRoomType(Space):
    view = models.CharField(max_length=255, verbose_name="객실 뷰", blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.view})" if self.view else self.name


# 실제 호텔 객실: HotelRoomType과 1:n 관계로 연결되어 실제 객실 정보를 저장합니다.
class HotelRoom(models.Model):
    room_type = models.ForeignKey(HotelRoomType, on_delete=models.CASCADE, related_name='rooms')
    floor = models.IntegerField(verbose_name="층", null=True, blank=True)
    room_number = models.CharField(max_length=50, verbose_name="호실", null=True, blank=True)
    room_memo = models.TextField(verbose_name="객실 메모", null=True, blank=True)

    def __str__(self):
        return f"Room {self.room_number} (Floor {self.floor}) - {self.room_type.name}"


# SpacePhoto 모델: 한 Space에 여러 사진을 연결하는 1:N 관계를 구성합니다.
class SpacePhoto(models.Model):
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='space_photos/')

    def __str__(self):
        return f"Photo for {self.space.name}"


