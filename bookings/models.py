import random
import string
from datetime import datetime

from django.contrib.auth.models import User
from django.db import models

from spaces.models import Space, BaseSpace, HotelRoom


class Reservation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reservations')
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name='reservations')
    start_date = models.DateField(help_text="예약 시작일", verbose_name='예약 시작일')
    start_time = models.TimeField(help_text="예약 시작 시간", verbose_name='예약 시작 시간', null=True, blank=True)
    end_date = models.DateField(help_text="예약 종료일", verbose_name='예약 종료일')
    end_time = models.TimeField(help_text="예약 종료 시간", verbose_name='예약 종료 시간', null=True, blank=True)
    reservation_date = models.DateTimeField(auto_now_add=True, help_text="예약 생성일", verbose_name='예약 생성일')
    people = models.PositiveIntegerField(help_text="예약 인원수", verbose_name='예약 인원수')
    is_approved = models.BooleanField(default=False, help_text="예약 승인 여부", verbose_name='예약 승인 여부')

    def is_valid(self):
        return self.end_date >= datetime.now().date()

    def __str__(self):
        return f"Reservation {self.id} for {self.space.name} by {self.user.username}"


class CheckIn(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='checkins')
    hotel_room = models.ForeignKey(HotelRoom, on_delete=models.CASCADE, related_name='checkins')
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name='checkins')
    check_in_date = models.DateField(help_text="체크인 날짜", verbose_name='체크인 날짜')
    check_in_time = models.TimeField(help_text="체크인 시간", verbose_name='체크인 시간', null=True, blank=True)
    check_out_date = models.DateField(help_text="체크아웃 날짜", verbose_name='체크아웃 날짜')
    check_out_time = models.TimeField(help_text="체크아웃 시간", verbose_name='체크아웃 시간', null=True, blank=True)
    temp_code = models.CharField(max_length=6, unique=True, verbose_name='임시번호')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    checked_out = models.BooleanField(default=False, help_text="체크아웃 여부", verbose_name='체크아웃 여부')
    is_day_use = models.BooleanField(default=False, help_text="대실 여부", verbose_name='대실 여부')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def is_valid(self):
        return self.check_out_date >= datetime.now().date()

    def __str__(self):
        return f"CheckIn {self.id} for {self.user.username} at {self.hotel_room.room_number}"


class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    check_in = models.ForeignKey(CheckIn, on_delete=models.CASCADE, related_name='reviews')
    content = models.TextField()
    rating = models.FloatField(verbose_name='별점')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return f"Review {self.id} by {self.user.username}"

class ReviewPhoto(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='review_photos/')

    def __str__(self):
        return f"Photo for Review {self.review.id}"

# Like: 특정 Space에 대한 좋아요 정보를 저장
class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='likes')
    basespace = models.ForeignKey(BaseSpace, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'basespace')

    def __str__(self):
        return f"{self.user.username} likes {self.basespace.name}"