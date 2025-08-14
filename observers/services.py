from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta

from django.core.cache import cache

from commons.constants import CacheKeys
from observers.models import Multiplier


@dataclass
class SignalRecord:
    """
    A class to represent a signal record.
    This is a placeholder for the actual implementation.
    """

    app_name: str
    worker_id: str
    trigger_by_payout_id: str | None = field(default=None)
    triggered_at: datetime | None = field(default=None)
    remaining_rounds: int = field(default=0)
    profit_window_rounds: int = field(default=15)
    triggered_recently: bool = field(default=False)


@dataclass(frozen=True)
class SignalConfig:
    payout_to_monitor: float = (
        20.00  # The payout we're interesed in monitoring, e.g., 20×
    )
    min_payouts_in_cluster: int = (
        7  # minimum payouts in the last 60 minutes with multiplier ≥ 20×
    )
    max_rounds: int = 4  # Max rounds since last ≥20×
    huge_payout: float = 80.00  # Size of payout to be considered "huge"
    burst_rounds: int = 20  # Lookback 20 rounds for burst
    min_payouts_in_bust: int = 3  # Number of ≥20× payout needed in last burst rounds
    window_rounds: int = 15  # rounds to watch after we send a signal

    # Redis fallback TTL (seconds) to auto-clean the cooldown key in case
    # a process dies. 2 hours is plenty for a 15-round window in practice.
    redis_ttl_seconds: int = 2 * 60 * 60


class SignalEngineService:
    """
    A service class that provides access to the signal engine.
    """

    SIGNAL_RECORD_KEY = CacheKeys.SIGNAL_RECORD

    def __init__(self):
        self.instance = None
        self.signal_config = SignalConfig()

    def _has_cluster(self) -> bool:
        """
        Check if in the past 60 minutes, there were at least 7 payouts with a multiplier of ≥ 20x.
        This indicates a busy hour with significant activity.
        It helps identify clusters of high payouts, suggesting a favorable environment for big wins.
        """

        time_now = self.instance.created_at
        one_hour_ago = time_now - timedelta(hours=1)
        # Fetch payouts in the last 60 minutes with multiplier ≥ 20
        high_payouts_count = Multiplier.objects.filter(
            worker=self.instance.worker,
            created_at__lte=self.instance.created_at,
            created_at__gte=one_hour_ago,
            crash__gte=self.signal_config.payout_to_monitor,
        ).count()

        return high_payouts_count >= self.signal_config.min_payouts_in_cluster

    def _has_short_streak(self) -> bool:
        """
        Check if either the last ≥20× was very recent (≤ 4 rounds ago) or it was huge (≥ 80×).
        """
        # Step 1: Find the last ≥20× payout
        last_high20 = (
            Multiplier.objects.filter(
                worker=self.instance.worker,
                created_at_lte=self.instance.created_at,
                crash__gte=self.signal_config.payout_to_monitor,
            )
            .order_by("-created_at")
            .first()
        )

        if not last_high20:
            return False

        # Step 2: Count the number of rounds between last_high20 and current payout
        rounds_since_last_high20 = Multiplier.objects.filter(
            worker=self.instance.worker,
            created_at__gt=last_high20.created_at,
            created_at__lte=self.instance.created_at,
        ).count()

        # Step 3: Check if it was recent
        is_recent = rounds_since_last_high20 <= self.signal_config.max_rounds

        # Step 4: last_high20_multiplier >= 80
        is_huge_payout = float(last_high20) >= self.signal_config.huge_payout

        return is_recent or is_huge_payout

    def _has_short_burst(self) -> bool:
        """
        Check if in the last 20 rounds, there were at least 3 payouts ≥ 20×.
        """
        # Get the last 20 payouts including the current one
        last_20 = Multiplier.objects.filter(
            worker=self.instance.worker, created_at__lte=self.instance.created_at
        ).order_by(  # Includes the current round but locked for real time calculations
            "-created_at"
        )[: self.signal_config.burst_rounds]

        # Count how many have crash ≥ 20
        high20_count = sum(
            float(payout.crash) >= self.signal_config.payout_to_monitor
            for payout in last_20
        )

        return high20_count >= self.signal_config.min_payouts_in_bust

    def _has_been_triggered_recently(self) -> bool:
        """
        Check if the signal has been triggered recently.
        This prevents sending multiple signals in a short time frame.
        """
        cache_key = self.SIGNAL_RECORD_KEY.format(self.instance.worker_id)
        signal_record_data = cache.get(cache_key)
        return signal_record_data.get("triggered_recently", False)

    def _should_send_signal(self) -> bool:
        """
        Run all checks to determine if the signal engine should be active.
        """
        return (
            self._has_cluster()
            and self._has_short_streak()
            and self._has_short_burst()
            and not self._has_been_triggered_recently()
        )

    def _update_signal(self) -> dict:
        """
        Update the signal engine with a new signal record.
        Decrements the remaining_rounds for the signal record in the cache by 1.
        """
        cache_key = self.SIGNAL_RECORD_KEY.format(self.instance.worker_id)
        signal_record_data = cache.get(cache_key) or {}

        # Decrement remaining_rounds, but not below 0
        remaining = max(
            0,
            signal_record_data.get("remaining_rounds", self.signal_config.window_rounds)
            - 1,
        )
        signal_record_data["remaining_rounds"] = remaining
        updated_signal_record = SignalRecord(**signal_record_data)
        cache.set(
            cache_key,
            asdict(updated_signal_record),
            self.signal_config.redis_ttl_seconds,
        )
        return asdict(updated_signal_record)

    def _reset_signal(self) -> dict:
        """Update the status of the signal record"""
        cache_key = self.SIGNAL_RECORD_KEY.format(self.instance.worker_id)
        default_values = {
            "app_name": self.instance.worker.app,
            "worker_id": self.instance.worker_id,
            "trigger_by_payout_id": None,  # Resetting the trigger payout ID
            "triggered_at": None,
            "remaining_rounds": self.signal_config.window_rounds,
            "profit_window_rounds": self.signal_config.window_rounds,
            "triggered_recently": False,
        }

        signal_record_data = cache.get(cache_key) or {}
        # Merge existing data with defaults, prioritizing reset values
        signal_record_data.update(default_values)
        signal_record = SignalRecord(**signal_record_data)

        cache.set(
            cache_key, asdict(signal_record), self.signal_config.redis_ttl_seconds
        )
        return asdict(signal_record)

    def _trigger_signal(self) -> dict:
        """
        Trigger the signal engine with a new signal record.
        Stores the signal record in cache and returns it.
        """
        cache_key = self.SIGNAL_RECORD_KEY.format(self.instance.worker_id)
        signal_record = SignalRecord(
            app_name=self.instance.worker.app,
            worker_id=self.instance.worker_id,
            trigger_by_payout_id=str(
                self.instance.id
            ),  # Use the current instance ID as the trigger payout ID
            triggered_at=self.instance.created_at.isoformat(),
            remaining_rounds=self.signal_config.window_rounds,
            profit_window_rounds=self.signal_config.window_rounds,
            triggered_recently=True,
        )
        cache.set(
            cache_key, asdict(signal_record), self.signal_config.redis_ttl_seconds
        )
        return asdict(signal_record)

    def _send_notification(self, signal_record: dict) -> None:
        """
        Send a notification about the triggered signal.
        This is a placeholder for the actual implementation.
        """
        # Here you would typically send a notification to the user or system
        # about the triggered signal, e.g., via email, push notification, etc.
        pass

    def process_latest_payout(self, instance: Multiplier):
        self.instance = instance

        payout = float(self.instance.crash)
        threshold = self.signal_config.payout_to_monitor

        if payout >= threshold:
            # Reset the signal engine if the payout is greater than or equal to the threshold
            return self._reset_signal()

        if self._should_send_signal():
            signal_record = self._trigger_signal()
            self._send_notification(signal_record)
            return signal_record
        else:
            return self._update_signal()


"""
Great—here’s each check explained simply, with what it measures, how you count it, why it matters, and how to tune it.

---

# 1) Busy (last 60 minutes) — **“Is the hour already lively?”**

**What it asks:**
In the past **60 minutes**, how many payouts were **≥ 20×**? We want **at least 7**.

**How to count (conceptually):**

* Take the current payout’s timestamp.
* Look back exactly **60 minutes**.
* Count all payouts in that window where **multiplier ≥ 20**.
* If the count **≥ 7**, this check passes.

**Why it matters:**
Big wins tend to **cluster**. If the last hour is already busy with high payouts, you’re more likely in a “storm” rather than a quiet stretch.

**Example:**

* Last hour had: 9 high-20s → **Pass** (≥7).
* Last hour had: 5 high-20s → **Fail**.

**Tuning:**

* Want **fewer but cleaner** signals? Raise the bar to **≥8**.
* Want **more** signals? Keep it at **7** (don’t go lower—it invites noise).

**Common pitfall:**

* Make sure this is **time-based** (60 minutes), not “last N rounds”.

---

# 2) Recent **or** Huge — **“Was the last big win very soon, or very big?”**

**What it asks (either is enough):**

* **Recent:** Did the last ≥20× happen **within the last 4 rounds**?
  *(Short gaps = clusters continue.)*
  **OR**
* **Huge:** Was the most recent ≥20× **≥ 80×**?
  *(Huge wins often have “aftershocks.”)*

**How to check (conceptually):**

* Track the **round index** of the last ≥20× and its **multiplier**.
* **Recent:** current\_round\_index − last\_high20\_round\_index **≤ 4**?
* **Huge:** last\_high20\_multiplier **≥ 80**?

**Why it matters:**
Two different “heat” signals:

* **Short gap** means the system just produced a big one → clustering likely.
* **Huge** means an unusual spike → the next few rounds often run hot.

**Example:**

* Last ≥20× was 3 rounds ago (Recent = 3) → **Pass**.
* Last ≥20× was 15 rounds ago but it was **120×** → **Pass** (Huge).
* Last ≥20× was 8 rounds ago and only **25×** → **Fail** here.

**Tuning:**

* Tighten **Recent** to **≤3** for slightly better precision.
* Raise **Huge** to **≥100×** if you want fewer, cleaner signals.

**Common pitfall:**

* This check is **OR**: passing **either** Recent **or** Huge is enough.

---

# 3) Burst20 — **“Are we in a mini-flurry right now?”**

**What it asks:**
In the **last 20 rounds** (not including the current one), were there **at least 3** payouts **≥ 20×**?

**How to count (conceptually):**

* Look at the **previous 20 rounds only** (exclude the current round to avoid “peeking”).
* Count rounds with multiplier **≥ 20**.
* If the count **≥ 3**, this check passes.

**Why it matters:**
This confirms **short-term heat**. Even if the hour is busy, we want to see that the **immediate** past is also active.

**Example:**

* In rounds t−20…t−1 you see: 4 high-20s → **Pass**.
* You only see 2 high-20s → **Fail**.

**Tuning:**

* For **fewer/cleaner** signals, raise to **Burst20 ≥ 4**.
* For **more** signals with similar accuracy, consider **Burst30 ≥ 3** (use the last 30 rounds).

**Common pitfall:**

* Always **exclude the current round** when counting Burst20.

---

## Putting them together (the “hot now?” test)

A round “passes” when:

* **Busy ≥ 7** (hour is lively), **AND**
* **(Recent ≤ 4 OR Huge ≥ 80×)** (last big win is fresh or massive), **AND**
* **Burst20 ≥ 3** (mini-flurry is happening).

When all three pass, the environment is **hot now**.
In the simple algorithm, you then **start the 15-round window on the next round** and ignore new triggers until the window ends.

That’s the whole idea: **hour hot** + **last big win favorable** + **short-term flurry** → **go next round for 15 rounds**.
"""
