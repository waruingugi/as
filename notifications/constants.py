from enum import Enum


class NotificationChannel(str, Enum):
    SMS = "SMS"
    PUSH = "PUSH"


class NotificationProvider(str, Enum):
    HOSTPINNACLESMS = "HOSTPINNACLESMS"
    ONESIGNAL = "ONESIGNAL"


class NotificationType(str, Enum):
    OTP = "OTP"
    MARKETING = "MARKETING"
    DEPOSIT = "DEPOSIT"
    SIGNAL = "SIGNAL"
