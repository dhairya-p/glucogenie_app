"""Application-wide constants."""
from __future__ import annotations

# Timezone
SINGAPORE_TIMEZONE = "Asia/Singapore"

# Data fetching defaults
DEFAULT_HISTORY_DAYS = 7
MAX_LOG_LIMIT = 50
MAX_MEAL_LOG_LIMIT = 10
MAX_MEDICATION_LOG_LIMIT = 10

# Timestamp formatting
UTC_OFFSET_SUFFIX = "+00:00"
UTC_Z_SUFFIX = "Z"

# Medication detection keywords and phrases
MEDICATION_PHRASES = [
    "have i taken my medication", "have i taken my med", "have i taken medication",
    "have i taken medicine", "have i taken insulin", "have i taken my medicine",
    "did i take my medication", "did i take my med", "did i take medication",
    "did i take medicine", "did i take insulin", "did i take my medicine",
    "taken my medication", "taken my med", "taken medication",
    "taken medicine", "taken insulin", "taken my medicine",
    "take my medication", "take my med", "take medication",
    "take medicine", "take insulin", "take my medicine",
    "medication i", "meds i", "my medication", "my med", "my medicine", "my insulin",
    "logged medication", "medication log", "medication logs",
    "recent medication", "recent med", "medication history"
]

MEDICATION_KEYWORDS_SPECIFIC = [
    "medication", "medications", "med ", "meds", "medicine", "insulin"
]

ADHERENCE_PHRASES = [
    "have i taken my medication", "have i taken my med", "have i taken medication",
    "have i taken medicine", "have i taken insulin", "have i taken my medicine",
    "did i take my medication", "did i take my med", "did i take medication",
    "did i take medicine", "did i take insulin", "did i take my medicine",
    "taken my medication today", "take my medication today",
    "taken medicine today", "taken insulin today"
]

MEAL_KEYWORDS = [
    "meal", "meals", "food", "eat", "ate", "eating", "what did i", "recent meal"
]

WEIGHT_KEYWORDS = [
    "weight", "weigh", "weighed", "weighing", "kg", "kilogram", "pound", "lbs",
    "weight change", "weight loss", "weight gain", "losing weight", "gaining weight",
    "bmi", "body mass", "current weight", "my weight", "weight trend"
]

ACTIVITY_KEYWORDS = [
    "activity", "activities", "exercise", "exercised", "exercising", "workout", "workouts",
    "active", "inactive", "activity level", "how much activity", "activity minutes",
    "activity log", "activity logs", "recent activity", "activity trend", "activity summary"
]

