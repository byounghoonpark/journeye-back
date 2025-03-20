from django.contrib.gis.db import models as gis_models
from django.db import models
from django.contrib.auth.models import User


class BaseSpace(gis_models.Model):
    name = models.CharField(max_length=255, verbose_name='이름')
    location = gis_models.PointField(geography=True, verbose_name='위치')
    address = models.CharField(max_length=255, verbose_name='주소')
    phone = models.CharField(max_length=20, verbose_name='전화번호')
    introduction = models.TextField(verbose_name='소개글')
    is_featured = models.BooleanField(default=False, verbose_name='상단 노출 여부')
    managers = models.ManyToManyField(
        User,
        blank=True,
        related_name='managed_spaces',
        verbose_name = '관리자',
        help_text="이 공간을 관리하는 사용자들"
    )

    def __str__(self):
        return self.name

class Floor(models.Model):
    basespace = models.ForeignKey(BaseSpace, on_delete=models.CASCADE, related_name='floors')
    floor_number = models.CharField(max_length=10, verbose_name="층 번호")
    # 추가 정보가 필요하면 description 같은 필드를 더 넣을 수 있습니다.

    class Meta:
        unique_together = ('basespace', 'floor_number')
        ordering = ['floor_number']

    def __str__(self):
        return f"{self.basespace.name} - {self.floor_number}층"


class BaseSpacePhoto(models.Model):
    basespace = models.ForeignKey(BaseSpace, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='basespace_photos/', verbose_name='공간 사진')

    def __str__(self):
        return f"Photo for {self.basespace.name}"


# Hotel은 다중 테이블 상속 사용 (BaseSpace를 상속)
class Hotel(BaseSpace):
    additional_services = models.TextField(blank=True, null=True, verbose_name='부가서비스')
    facilities = models.TextField(blank=True, null=True, verbose_name='시설안내')
    star_rating = models.PositiveIntegerField(null=True, blank=True, verbose_name='별 등급')

    # Hotel 고유 필드가 더 있다면 추가
    def __str__(self):
        return self.name


class Facility(BaseSpace):
    FACILITY_TYPES = [
        ('transport', '교통'),
        ('tourist_attraction', '관광 명소'),
        ('activity', '액티비티'),
        ('cultural_performance', '문화 공연'),
        ('tour_program', '투어 프로그램'),
        ('restaurant', '음식점'),
        ('delivery', '배달'),
        ('shopping', '쇼핑'),
        ('rental_space', '공간 대여'),
        ('medical', '의료'),
        ('beauty', '미용'),
        ('kids', '어린이'),
    ]

    facility_type = models.CharField(max_length=50, choices=FACILITY_TYPES, verbose_name="시설 유형")
    opening_time = models.TimeField(blank=True, null=True, verbose_name="오픈 시간")
    closing_time = models.TimeField(blank=True, null=True, verbose_name="마감 시간")
    additional_info = models.JSONField(blank=True, null=True, verbose_name="기타 정보")

    class Meta:
        verbose_name = "시설"
        verbose_name_plural = "시설 목록"

    def __str__(self):
        return f"{self.name} ({self.get_facility_type_display()})"


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


class Space(models.Model):
    name = models.CharField(max_length=255, verbose_name='호실 또는 테이블명')
    nickname = models.CharField(max_length=255, blank=True, null=True, verbose_name='별칭')
    description = models.TextField(blank=True, verbose_name='설명')
    # price 테이블 따로 빼서 시즌별 요금제 바뀔수있어야함
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='가격')
    capacity = models.PositiveIntegerField(null=True, blank=True, verbose_name='수용 인원')
    basespace = models.ForeignKey(BaseSpace, on_delete=models.CASCADE, related_name='spaces')

    def __str__(self):
        return f"{self.name} at {self.basespace.name}"


# SpacePhoto 모델: 한 Space에 여러 사진을 연결하는 1:N 관계를 구성합니다.
class SpacePhoto(models.Model):
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='space_photos/')

    def __str__(self):
        return f"Photo for {self.space.name}"


class HotelRoomType(Space):
    view = models.CharField(max_length=255, verbose_name="객실 뷰", blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.view})" if self.view else self.name


# 실제 호텔 객실: HotelRoomType과 1:n 관계로 연결되어 실제 객실 정보를 저장합니다.
class HotelRoom(models.Model):
    room_type = models.ForeignKey(HotelRoomType, on_delete=models.CASCADE, related_name='rooms')
    floor = models.ForeignKey(Floor, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="층")
    room_number = models.CharField(max_length=50, verbose_name="호실", null=True, blank=True)
    status = models.CharField(max_length=50, verbose_name="객실 상태", null=True, blank=True)
    non_smoking = models.BooleanField(default=True, verbose_name="금연 여부")

    def __str__(self):
        return f"Room {self.room_number} (Floor {self.floor}) - {self.room_type.name}"


class HotelRoomMemo(models.Model):
    hotel_room = models.ForeignKey(HotelRoom, on_delete=models.CASCADE, related_name='memos')
    memo_date = models.DateField(verbose_name="메모 날짜")
    memo_content = models.TextField(verbose_name="메모 내용")

    def __str__(self):
        return f"Memo on {self.memo_date} for Room {self.hotel_room.room_number}"

# HotelRoomHistory 모델: 객실 이력 정보를 저장합니다.
class HotelRoomHistory(models.Model):
    hotel_room = models.ForeignKey(HotelRoom, on_delete=models.CASCADE, related_name='histories')
    history_date = models.DateTimeField(auto_now_add=True, verbose_name="이력 날짜")
    history_content = models.TextField(verbose_name="이력 내용")

    def __str__(self):
        return f"History on {self.history_date} for Room {self.hotel_room.room_number}"

# HotelRoomUsage 모델: 객실 이용 내역을 저장합니다.
class HotelRoomUsage(models.Model):
    hotel_room = models.ForeignKey(HotelRoom, on_delete=models.CASCADE, related_name='usages')
    usage_date = models.DateTimeField(auto_now_add=True, verbose_name="이용 날짜")
    usage_content = models.TextField(verbose_name="이용 내용")

    def __str__(self):
        return f"Usage on {self.usage_date} for Room {self.hotel_room.room_number}"


