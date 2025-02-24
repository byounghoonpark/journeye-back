from django.db import models
from spaces.models import BaseSpace


# AIConcierge: 컨시어지 정보를 저장하는 모델
class AIConcierge(models.Model):
    name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name if self.name else f"AIConcierge {self.id}"

# ConciergeAssignment: 한 AIConcierge가 여러 BaseSpace(호텔/식당 등)와 연결되어,
# 예를 들어 '어떤 레스토랑에 몇 시에 갈지' 등의 정보를 저장하는 1:N 테이블.
class ConciergeAssignment(models.Model):
    concierge = models.ForeignKey(AIConcierge, on_delete=models.CASCADE, related_name='assignments')
    basespace = models.ForeignKey(BaseSpace, on_delete=models.CASCADE, related_name='concierge_assignments')
    usage_time = models.DateTimeField(help_text="이용 시간 (예: 방문 또는 예약 시간)", verbose_name='이용 시간')
    instructions = models.TextField(blank=True, null=True, help_text="추가 지시 사항", verbose_name='추가 지시 사항')

    def __str__(self):
        return f"{self.concierge} -> {self.basespace.name} at {self.usage_time}"


from django.db import models

# Create your models here.
