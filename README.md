# 호텔 예약 관리 시스템

## 개요

이 애플리케이션은 Django 프레임워크를 기반으로 한 호텔 예약 관리 시스템입니다. 사용자들은 호텔 객실 또는 기타 공간에 대해 예약, 체크인/체크아웃, 리뷰 작성, 그리고 좋아요 기능 등을 통해 편리하게 서비스를 이용할 수 있습니다. 또한, GIS 기능을 활용하여 공간의 위치 정보를 효과적으로 관리할 수 있습니다.

## 주요 기능

### 예약 관리 (Reservation)
- 사용자가 호텔이나 기타 공간을 예약할 수 있습니다.
- 예약 정보는 시작/종료 날짜, 시작/종료 시간, 예약 인원수 등이 포함되며, 예약 유효성 검사를 통해 현재 사용 가능한 예약만 관리합니다.

### 체크인 관리 (CheckIn)
- 예약 후 사용자가 호텔 객실에서 체크인 및 체크아웃할 수 있도록 지원합니다.
- 체크인 시 임시 번호를 발급하며, 대실(일일 이용) 여부와 체크아웃 여부를 관리하여 객실 사용 상태를 추적합니다.

### 리뷰 및 사진 관리 (Review & ReviewPhoto)
- 숙박 후 사용자는 객실 또는 공간에 대한 리뷰를 작성하고, 별점 평가와 함께 사진을 첨부할 수 있습니다.

### 좋아요 기능 (Like)
- 사용자가 관심 있는 공간(BaseSpace)에 좋아요를 등록하여 즐겨찾기 형태로 관리할 수 있습니다.
- 사용자와 공간 간의 고유한 관계를 유지하여 중복 좋아요를 방지합니다.

### 공간 및 시설 관리
- **BaseSpace**: 호텔, 레스토랑 등 다양한 공간의 기본 정보를 관리합니다. (이름, 위치, 주소, 전화번호, 소개글 등)
- **호텔 및 레스토랑**: BaseSpace를 상속받아 각 공간에 특화된 부가 정보(예: 부가 서비스, 시설 안내 등)를 추가로 제공합니다.
- **객실 및 세부 공간**: 개별 객실(HotelRoom)과 테이블 등의 공간 정보, 가격, 수용 인원, 사진 등을 관리합니다.
- **GIS 기능**: 지리정보(PointField)를 이용하여 공간의 위치를 저장, 관리합니다.

### 사용자 프로필 및 역할 관리
- **UserProfile**: 기본 사용자 모델에 전화번호, 프로필 사진, 국적, 인증 상태 등 추가 정보를 저장하여 확장합니다.
- **UserRole**: 일반 사용자, 관리자, 슈퍼 관리자로 사용자 역할을 구분하여 권한 관리를 지원합니다.

## 기술 스택

- **프레임워크**: Django
- **프로그래밍 언어**: Python
- **데이터베이스**: PostgreSQL (PostGIS 확장 포함)
- **GIS 지원**: Django GIS

## 설치 및 실행 방법

### 1. 저장소 클론

```bash
git clone <repository-url>
cd <repository-directory>
```

### 2. 파이썬 패키지 설치
#### 프로젝트의 의존성은 requirements.txt 파일에 명시되어 있습니다.

```bash
pip install -r requirements.txt
```

### 3. 데이터베이스 설정
#### settings.py 파일을 열어 데이터베이스 설정을 본인의 환경에 맞게 수정합니다. PostgreSQL과 PostGIS가 사전에 설치되어 있어야 합니다.(.env 파일을 사용하여 환경변수를 설정할 수 있습니다.)

```bash
pip install -r requirements.txt
```

### 4. 마이그레이션 실행

```bash
python manage.py migrate
```

### 5. 슈퍼유저 생성

```bash
python manage.py createsuperuser
```

### 6. 개발 서버 실행

```bash
python manage.py runserver
```

## 프로젝트 구조

이 프로젝트는 다양한 기능별로 모델이 모듈화되어 있습니다. 주요 모델은 다음과 같습니다:

#### Reservation, CheckIn, Review, ReviewPhoto, Like
- 예약 및 체크인 처리와 함께, 사용자 리뷰 및 좋아요 기능을 담당합니다.

#### BaseSpace, Floor, BaseSpacePhoto, Hotel, Restaurant, Service
- 호텔, 레스토랑 등 다양한 공간의 기본 정보를 관리하며, 공간 관련 부가 서비스 및 GIS 정보를 포함합니다.

#### Space, SpacePhoto, HotelRoomType, HotelRoom, HotelRoomMemo, HotelRoomHistory, HotelRoomUsage
- 개별 객실 및 공간의 세부 정보를 관리하며, 객실 이력 및 사용 내역 등을 추적합니다.

#### UserProfile, UserRole
- 사용자 정보 확장 및 역할 기반 권한 관리를 위해 기본 사용자 모델을 확장합니다.

