from django.urls import reverse
from django.test import override_settings
from django.contrib.auth.models import User
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from django.core import mail
from accounts.models import UserProfile
from django.contrib.gis.geos import Point


# 1. 회원가입 테스트
@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class UserRegistrationTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("user-register")  # urls.py: register/  name="user-register"

    def test_registration_success(self):
        data = {
            "first_name": "Test",
            "last_name": "User",
            "email": "testuser@example.com",
            "password": "StrongPass123!",
            # "profile_picture": None,
            "nationality": "KR",
            "phone_number": "01012345678",
            "language": "ko"
        }
        # 회원가입 엔드포인트는 파일 업로드 포맷(multipart)을 사용함
        response = self.client.post(self.url, data, format="multipart")
        self.assertEqual(response.status_code, 201)
        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)
        self.assertEqual(response.data["username"], f"{data['first_name']} {data['last_name']}")

    def test_registration_invalid_data(self):
        data = {
            "first_name": "",
            "last_name": "",
            "email": "invalid_email",
            "password": "123",
            # "profile_picture": None,
            "nationality": "",
            "phone_number": "",
            "language": ""
        }
        response = self.client.post(self.url, data, format="multipart")
        self.assertEqual(response.status_code, 400)


# 2. 이메일 인증 관련 테스트 (이메일 발송)
@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class EmailVerificationTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.send_email_url = reverse("resend-email-verification")
        # User 객체 생성 후, UserProfile을 수동 생성합니다.
        self.user = User.objects.create_user(
            username="verifyuser", email="verifyuser@example.com", password="TestPass123!"
        )
        UserProfile.objects.create(user=self.user, email_code="654321", email_verified=False)

    def test_send_email_verification(self):
        data = {"email": "newuser@example.com"}
        response = self.client.post(self.send_email_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("verification_code", response.data)
        self.assertEqual(len(mail.outbox), 1)


# 3. 이메일 코드 로그인 테스트
@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class EmailCodeLoginTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("email_code_login")  # urls.py: login/email-code/  name="email_code_login"
        # 테스트용 사용자 및 프로필 생성, 이메일 인증 코드 설정
        self.user = User.objects.create_user(username="codeuser", email="codeuser@example.com", password="TestPass123!")
        UserProfile.objects.create(user=self.user, email_code="111111")

    def test_email_code_login_success(self):
        data = {"email_code": "111111"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)
        self.assertEqual(response.data["message"], "로그인 성공")

    def test_email_code_login_failure(self):
        data = {"email_code": "000000"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["message"], "유효하지 않은 이메일 인증 코드입니다.")


# 4. 이메일/비밀번호를 통한 JWT 로그인 테스트
class EmailLoginTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("로그인")  # urls.py: login/  name="로그인"
        self.user = User.objects.create_user(username="loginuser", email="loginuser@example.com",
                                             password="TestPass123!")
        UserProfile.objects.create(user=self.user)

    def test_email_login_success(self):
        data = {"email": "loginuser@example.com", "password": "TestPass123!"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_email_login_failure(self):
        data = {"email": "loginuser@example.com", "password": "WrongPass"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 400)


# 5. 비밀번호 변경 테스트
class ChangePasswordTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("change-password")  # urls.py: change-password/  name="change-password"
        self.user = User.objects.create_user(username="changepass", email="changepass@example.com",
                                             password="OldPass123!")
        refresh = RefreshToken.for_user(self.user)
        token = f"Bearer {str(refresh.access_token)}"
        self.client.credentials(HTTP_AUTHORIZATION=token)

    def test_change_password_success(self):
        data = {
            "current_password": "OldPass123!",
            "new_password": "NewPass123!",
            "confirm_password": "NewPass123!"
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPass123!"))

    def test_change_password_wrong_current(self):
        data = {
            "current_password": "WrongPass",
            "new_password": "NewPass123!",
            "confirm_password": "NewPass123!"
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["message"], "현재 비밀번호가 올바르지 않습니다.")


# 6. 비밀번호 초기화(Reset) 테스트
@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class ResetPasswordTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("reset-password")  # urls.py: reset-password/  name="reset-password"
        self.user = User.objects.create_user(username="resetuser", email="resetuser@example.com",
                                             password="InitPass123!")

    def test_reset_password_success(self):
        data = {"email": "resetuser@example.com"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "임시 비밀번호가 이메일로 전송되었습니다.")
        # 메일 백엔드에 이메일이 전송되었는지 확인
        self.assertEqual(len(mail.outbox), 1)

    def test_reset_password_unknown_email(self):
        data = {"email": "unknown@example.com"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["message"], "등록되지 않은 이메일입니다.")


# 7. 회원 프로필 수정 테스트
class UserProfileUpdateTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("profile-update")  # urls.py: profile/update/  name="profile-update"
        self.user = User.objects.create_user(username="profileuser", email="profileuser@example.com",
                                             password="ProfilePass123!")
        UserProfile.objects.create(user=self.user, phone_number="01000000000", nationality="KR", language="ko")
        refresh = RefreshToken.for_user(self.user)
        token = f"Bearer {str(refresh.access_token)}"
        self.client.credentials(HTTP_AUTHORIZATION=token)

    def test_profile_update_success(self):
        data = {
            "phone_number": "01011112222",
            "nationality": "US",
            "language": "en"
        }
        response = self.client.patch(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.get("phone_number"), "01011112222")
        self.assertEqual(response.data.get("nationality"), "US")
        self.assertEqual(response.data.get("language"), "en")


# 8. 비밀번호 검증 테스트
class VerifyPasswordTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("verify-password")  # urls.py: verify-password/  name="verify-password"
        self.user = User.objects.create_user(username="verifypass", email="verifypass@example.com",
                                             password="VerifyPass123!")
        refresh = RefreshToken.for_user(self.user)
        token = f"Bearer {str(refresh.access_token)}"
        self.client.credentials(HTTP_AUTHORIZATION=token)

    def test_verify_password_success(self):
        data = {"password": "VerifyPass123!"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "비밀번호가 올바릅니다.")

    def test_verify_password_failure(self):
        data = {"password": "WrongPass"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["message"], "비밀번호가 올바르지 않습니다.")


# 9. 이메일 중복 및 가입 여부 확인 테스트
class CheckEmailTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("check-email")  # urls.py: check-email/  name="check-email"
        self.user = User.objects.create_user(username="checkuser", email="checkuser@example.com",
                                             password="SomePass123!")

    def test_check_existing_email(self):
        data = {"email": "checkuser@example.com"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "이미 가입된 이메일입니다.")

    def test_check_nonexistent_email(self):
        data = {"email": "nonexistent@example.com"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "가입되지 않은 이메일입니다.")


# 10. 공간 관리자 지정(AssignSpaceManager) 테스트
#     ※ 이 테스트는 관리자 권한 및 BaseSpace 모델의 managers 관계를 활용합니다.
@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AssignSpaceManagerTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        # 관리자 계정 생성
        self.admin_user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="AdminPass123!"
        )
        # 일반 사용자 생성 및 프로필 수동 생성
        self.regular_user = User.objects.create_user(
            username="user", email="user@example.com", password="UserPass123!"
        )
        UserProfile.objects.create(user=self.regular_user, role="GENERAL")
        # BaseSpace 생성 시, location 필드에 유효한 Point 객체를 전달합니다.
        from spaces.models import BaseSpace
        self.basespace = BaseSpace.objects.create(
            name="Test Space",
            location=Point(0, 0)  # 올바른 GEOS Point 객체 전달
        )
        self.url = reverse("assign-hotel-manager")  # urls.py: assign-space-manager/  name="assign-hotel-manager"
        refresh = RefreshToken.for_user(self.admin_user)
        token = f"Bearer {str(refresh.access_token)}"
        self.client.credentials(HTTP_AUTHORIZATION=token)

    def test_assign_manager_success(self):
        data = {
            "user_email": "user@example.com",
            "basespace_id": self.basespace.id
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.basespace.managers.filter(email="user@example.com").exists())

    def test_assign_manager_missing_data(self):
        data = {"user_email": ""}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 400)

