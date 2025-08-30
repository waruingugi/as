from enum import Enum


class ErrorCodes(str, Enum):
    INVALID_PHONE_NUMBER = "This phone number is incorrect. Please try again."
    USERNAME_EXISTS = "This username is already taken."
    USERNAME_IS_INVALID = "Username can only contain letters[a-z] and numbers[0-9]."
    USERNAME_IS_TOO_SHORT = "This username is too short."
    USERNAME_IS_TOO_LONG = "This username is too long."
    USER_IS_VERIFIED = "This user is already verified."
    USER_DOES_NOT_EXIST = "This user does not exist"
    INVALID_MULTIPLIER_STRING = "Multiplier string has an invalid format."
    EMPTY_MULTIPLIER_STRING = "Multiplier string can not be empty or null"
    WORKER_API_KEY_IS_REQUIRED = "Worker API Key is required"
    MULTIPLIERS_NOT_FOUND = "No valid multipliers found."
    INVALID_WORKER_API_KEY = "Invalid or expired worker API key"
    INVALID_APP_NAME = "Invalid app name."
    WORKERS_NOT_FOUND = "No workers found for the specified app."
    PHONE_NUMBER_EXISTS = "This phone number is already taken."
    INVALID_OTP = "The OTP entered is incorrect. Please try again"
    DEACTIVATED_USER = "This account has been deactivated. Please contact support."
