"""Hard limits. These are enforced in code (paycheck/safety.py), never by the prompt."""

PER_PAYMENT_CAP_RUPEES = 50_000   # one payment can't exceed this
APP_DAILY_CAP_RUPEES = 50_000     # all payments in one day, so splitting doesn't help
MAX_NOTE_CHARS = 60
MAX_WARNING_CHARS = 200
