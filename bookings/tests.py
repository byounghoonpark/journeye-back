from datetime import date, time, timedelta
from django.urls import reverse
from django.contrib.gis.geos import Point
from django.test import override_settings
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from accounts.models import UserProfile
from spaces.models import BaseSpace, HotelRoomType, HotelRoom, HotelRoomUsage, HotelRoomMemo
from bookings.models import CheckIn, Reservation, Like
from django.utils.timezone import now


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class CheckInAndOutViewSetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        # 관리자 사용자 생성
        self.admin_user = User.objects.create_superuser(
            username="admin", email="admin@test.com", password="AdminPass123"
        )
        UserProfile.objects.create(user=self.admin_user, role="ADMIN")
        # 일반 예약 고객 생성
        self.user = User.objects.create_user(
            username="user", email="user@test.com", password="UserPass123"
        )
        UserProfile.objects.create(user=self.user, role="GENERAL")
        # BaseSpace 생성
        self.basespace = BaseSpace.objects.create(
            name="Test Hotel", location=Point(0, 0),
            address="Test Address", phone="01011112222", introduction="Test Intro", is_featured=False
        )
        # HotelRoomType 생성 (Reservation.space에 할당할 올바른 인스턴스)
        self.room_type = HotelRoomType.objects.create(
            basespace=self.basespace,
            name="Standard",
            nickname="Std"
        )
        # HotelRoom 생성 – name 필드는 없으므로 room_number, room_type, status 사용
        self.hotel_room = HotelRoom.objects.create(
            room_number="101",
            room_type=self.room_type,
            status="빈 방"
        )
        # 예약 생성: Reservation.space에는 self.room_type 전달
        self.reservation = Reservation.objects.create(
            user=self.user,
            space=self.room_type,  # 수정된 부분: self.room_type는 Space를 상속받음
            start_date=date.today(),
            start_time=time(14, 0),
            end_date=date.today() + timedelta(days=1),
            end_time=time(11, 0),
            people=2,
            guest="user@test.com"
        )
        # 관리자 JWT 토큰 등록
        refresh = RefreshToken.for_user(self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        # URL 설정 – bookings 앱의 urls.py의 URL 이름과 일치해야 함
        self.checkin_url = reverse("checkin")
        self.checkout_url = reverse("checkout")

    def test_reserved_customer_check_in_success(self):
        data = {
            "hotel_id": self.basespace.id,
            "room_id": self.hotel_room.id,
            "reservation_id": self.reservation.id,
            "user_id": self.user.id,
            "end_date": (date.today() + timedelta(days=1)).isoformat(),
            "end_time": "11:00:00",
            "is_day_use": False,
            "guest": {"adults": 1, "children": 1}  # JSON 형식 guest 필드 추가
        }
        response = self.client.post(self.checkin_url, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertIn("temp_code", response.data)

    def test_walkin_customer_check_in_success(self):
        data = {
            "hotel_id": self.basespace.id,
            "room_id": self.hotel_room.id,
            "guest_name": "WalkIn User",
            "email": "walkin@test.com",
            "phone": "01012345678",
            "nationality": "KR",
            "language": "ko",
            "start_date": date.today().isoformat(),
            "start_time": "14:00:00",
            "end_date": (date.today() + timedelta(days=1)).isoformat(),
            "end_time": "11:00:00",
            "is_day_use": False,
            "guest": "walkin@test.com"
        }
        response = self.client.post(self.checkin_url, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertIn("temp_code", response.data)

    def test_check_out_success(self):
        # 워크인 체크인을 수동으로 생성
        temp_code = "123456"
        walkin_user = User.objects.create_user(
            username="walkin", email="walkin@test.com", password="temp"
        )
        UserProfile.objects.create(user=walkin_user, role="TEMP", email_code=temp_code)
        reservation = Reservation.objects.create(
            user=walkin_user,
            space=self.room_type,  # 수정된 부분
            start_date=date.today(),
            start_time=time(14, 0),
            end_date=date.today() + timedelta(days=1),
            end_time=time(11, 0),
            people=1,
            guest="walkin@test.com"
        )
        check_in = CheckIn.objects.create(
            user=walkin_user,
            hotel_room=self.hotel_room,
            reservation=reservation,
            check_in_date=date.today(),
            check_in_time=time(14, 0),
            check_out_date=date.today() + timedelta(days=1),
            check_out_time=time(11, 0),
            temp_code=temp_code,
            is_day_use=False,
            checked_out=False
        )
        data = {"room_id": self.hotel_room.id}
        response = self.client.post(self.checkout_url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("체크아웃 완료", response.data["message"])


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class LikeViewSetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        # Like 테스트용 BaseSpace 생성
        self.like_basespace = BaseSpace.objects.create(name="Like Hotel", location=Point(0, 0))
        # 사용자 생성
        self.user = User.objects.create_user(
            username="likeuser", email="likeuser@test.com", password="Pass123"
        )
        UserProfile.objects.create(user=self.user)
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        self.toggle_like_url = reverse("like-toggle-like")
        self.is_liked_url = reverse("like-is-liked") + f"?basespace_id={self.like_basespace.id}"

    def test_toggle_like_add(self):
        data = {"basespace_id": self.like_basespace.id}
        response = self.client.post(self.toggle_like_url, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["detail"], "좋아요가 추가되었습니다.")

    def test_toggle_like_remove(self):
        data = {"basespace_id": self.like_basespace.id}
        self.client.post(self.toggle_like_url, data, format="json")
        response = self.client.post(self.toggle_like_url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["detail"], "좋아요가 취소되었습니다.")

    def test_is_liked(self):
        data = {"basespace_id": self.like_basespace.id}
        self.client.post(self.toggle_like_url, data, format="json")
        response = self.client.get(self.is_liked_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["liked"])
