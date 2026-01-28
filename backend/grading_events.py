"""
Grading Event System with Raistlin Voice Feedback Triggers
Hooks into the grading workflow to provide verbal confirmations

Authority Level: 11.0
Commander: Bobby Don McWilliams II
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable, List, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger("GradingEvents")


class GradingEventType(Enum):
    """Types of grading events"""
    GRADING_STARTED = "grading_started"
    IMAGE_PROCESSED = "image_processed"
    AI_RESPONSE_RECEIVED = "ai_response_received"
    CONSENSUS_CALCULATED = "consensus_calculated"
    GRADING_COMPLETE = "grading_complete"
    READY_FOR_DATABASE = "ready_for_database"
    DATABASE_SAVED = "database_saved"
    ERROR_OCCURRED = "error_occurred"
    KEY_ISSUE_DETECTED = "key_issue_detected"
    BATCH_STARTED = "batch_started"
    BATCH_COMPLETE = "batch_complete"


@dataclass
class GradingEvent:
    """Event data for grading operations"""
    event_type: GradingEventType
    timestamp: datetime = field(default_factory=datetime.now)
    comic_title: str = ""
    issue_number: str = ""
    grade: Optional[float] = None
    confidence: Optional[float] = None
    is_key_issue: bool = False
    defects: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class GradingEventBus:
    """
    Event bus for grading system.
    Allows components to subscribe to grading events and trigger actions.
    """

    def __init__(self):
        self._subscribers: Dict[GradingEventType, List[Callable]] = {}
        self._async_subscribers: Dict[GradingEventType, List[Callable]] = {}
        self._global_subscribers: List[Callable] = []
        self._async_global_subscribers: List[Callable] = []

    def subscribe(
        self,
        event_type: GradingEventType,
        callback: Callable[[GradingEvent], None],
        is_async: bool = False
    ):
        """Subscribe to a specific event type"""
        if is_async:
            if event_type not in self._async_subscribers:
                self._async_subscribers[event_type] = []
            self._async_subscribers[event_type].append(callback)
        else:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)

    def subscribe_all(self, callback: Callable[[GradingEvent], None], is_async: bool = False):
        """Subscribe to all events"""
        if is_async:
            self._async_global_subscribers.append(callback)
        else:
            self._global_subscribers.append(callback)

    def unsubscribe(self, event_type: GradingEventType, callback: Callable):
        """Unsubscribe from an event type"""
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                cb for cb in self._subscribers[event_type] if cb != callback
            ]
        if event_type in self._async_subscribers:
            self._async_subscribers[event_type] = [
                cb for cb in self._async_subscribers[event_type] if cb != callback
            ]

    async def emit(self, event: GradingEvent):
        """Emit an event to all subscribers"""
        logger.debug(f"Event: {event.event_type.value} - {event.comic_title}")

        # Call sync subscribers
        for callback in self._subscribers.get(event.event_type, []):
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Subscriber error: {e}")

        for callback in self._global_subscribers:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Global subscriber error: {e}")

        # Call async subscribers
        async_tasks = []
        for callback in self._async_subscribers.get(event.event_type, []):
            async_tasks.append(callback(event))

        for callback in self._async_global_subscribers:
            async_tasks.append(callback(event))

        if async_tasks:
            await asyncio.gather(*async_tasks, return_exceptions=True)

    def emit_sync(self, event: GradingEvent):
        """Emit event synchronously (only calls sync subscribers)"""
        for callback in self._subscribers.get(event.event_type, []):
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Subscriber error: {e}")

        for callback in self._global_subscribers:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Global subscriber error: {e}")


# =============================================================================
# VOICE PERSONALITY SELECTION
# =============================================================================

class VoicePersonality(Enum):
    """Available voice personalities"""
    RAISTLIN = "raistlin"  # Wise, mystical, measured
    BREE = "bree"          # Vulgar, brutally honest, dynamic


# =============================================================================
# RAISTLIN VOICE INTEGRATION
# =============================================================================

class RaistlinVoiceTriggers:
    """
    Connects Raistlin voice feedback to grading events.
    Automatically provides verbal confirmations at key points.
    """

    def __init__(self, event_bus: GradingEventBus, enabled: bool = True):
        self.event_bus = event_bus
        self.enabled = enabled
        self._raistlin = None
        self._setup_triggers()

    def _get_raistlin(self):
        """Lazy load Raistlin to avoid circular imports"""
        if self._raistlin is None:
            try:
                from raistlin_voice_feedback import get_raistlin
                self._raistlin = get_raistlin()
            except Exception as e:
                logger.error(f"Could not load Raistlin: {e}")
                self.enabled = False
        return self._raistlin

    def _setup_triggers(self):
        """Setup event subscriptions for voice feedback
        
        SIMPLIFIED: Raistlin ONLY speaks on GRADING_COMPLETE
        Nothing else. No double-speak.
        """
        # ONLY subscribe to GRADING_COMPLETE - ONE event, ONE response
        self.event_bus.subscribe(
            GradingEventType.GRADING_COMPLETE,
            self._on_grading_complete,
            is_async=True
        )
        # ERROR handling only
        self.event_bus.subscribe(
            GradingEventType.ERROR_OCCURRED,
            self._on_error,
            is_async=True
        )

    async def _on_grading_started(self, event: GradingEvent):
        """Called when grading begins"""
        if not self.enabled:
            return

        raistlin = self._get_raistlin()
        if raistlin and raistlin.enabled:
            await raistlin.greet()

    async def _on_grading_complete(self, event: GradingEvent):
        """Called when grading completes with final grade"""
        if not self.enabled:
            return

        raistlin = self._get_raistlin()
        if raistlin and raistlin.enabled and event.grade is not None:
            await raistlin.announce_grade(
                grade=event.grade,
                title=event.comic_title or "this specimen",
                confidence=event.confidence or 0.9
            )

    async def _on_ready_for_database(self, event: GradingEvent):
        """Called when comic is ready to be saved"""
        if not self.enabled:
            return

        raistlin = self._get_raistlin()
        if raistlin and raistlin.enabled:
            # Full summary if we have all the info
            if event.grade is not None and event.comic_title:
                await raistlin.full_grading_summary(
                    title=event.comic_title,
                    issue_number=event.issue_number or "unknown",
                    grade=event.grade,
                    confidence=event.confidence or 0.9,
                    is_key_issue=event.is_key_issue,
                    defects=event.defects
                )
            else:
                await raistlin.confirm_ready_for_database(event.comic_title)

    async def _on_database_saved(self, event: GradingEvent):
        """Called after comic is saved to database"""
        if not self.enabled:
            return

        raistlin = self._get_raistlin()
        if raistlin and raistlin.enabled:
            await raistlin.prompt_next_comic()

    async def _on_key_issue_detected(self, event: GradingEvent):
        """Called when a key issue is detected"""
        if not self.enabled:
            return

        raistlin = self._get_raistlin()
        if raistlin and raistlin.enabled:
            significance = event.metadata.get("significance", "")
            await raistlin.announce_key_issue(significance)

    async def _on_error(self, event: GradingEvent):
        """Called when an error occurs"""
        if not self.enabled:
            return

        raistlin = self._get_raistlin()
        if raistlin and raistlin.enabled:
            await raistlin.report_error(event.error or "Unknown error")

    async def _on_batch_complete(self, event: GradingEvent):
        """Called when a batch of comics is complete"""
        if not self.enabled:
            return

        raistlin = self._get_raistlin()
        if raistlin and raistlin.enabled:
            count = event.metadata.get("count", 0)
            from raistlin_voice_feedback import EmotionType
            await raistlin.speak(
                f"Batch complete. {count} specimens have been judged.",
                EmotionType.TRIUMPHANT
            )


# =============================================================================
# BREE VOICE INTEGRATION (UNCENSORED)
# =============================================================================

class BreeVoiceTriggers:
    """
    Connects Bree voice feedback to grading events.
    Provides brutally honest, vulgar commentary based on grade quality.
    Uses Claude for dynamic response generation.
    """

    def __init__(self, event_bus: GradingEventBus, enabled: bool = True):
        self.event_bus = event_bus
        self.enabled = enabled
        self._bree = None
        self._setup_triggers()

    def _get_bree(self):
        """Lazy load Bree to avoid circular imports"""
        if self._bree is None:
            try:
                from bree_voice_feedback import get_bree
                self._bree = get_bree()
            except Exception as e:
                logger.error(f"Could not load Bree: {e}")
                self.enabled = False
        return self._bree

    def _setup_triggers(self):
        """Setup event subscriptions for voice feedback
        
        BREE ONLY speaks on READY_FOR_DATABASE (after Raistlin finishes grading)
        This prevents double-speaking with Raistlin who handles GRADING_COMPLETE
        """
        # Bree comments AFTER grading is complete and ready to save
        self.event_bus.subscribe(
            GradingEventType.READY_FOR_DATABASE,
            self._on_ready_for_database,
            is_async=True
        )
        self.event_bus.subscribe(
            GradingEventType.ERROR_OCCURRED,
            self._on_error,
            is_async=True
        )

    # NOTE: _on_grading_complete removed - Raistlin handles GRADING_COMPLETE
    # Bree only speaks on READY_FOR_DATABASE to avoid double-speaking

    async def _on_ready_for_database(self, event: GradingEvent):
        """Called when comic is ready to be saved - full Bree commentary"""
        if not self.enabled:
            return

        bree = self._get_bree()
        if bree and bree.enabled and event.grade is not None:
            await bree.full_grading_commentary(
                title=event.comic_title or "Unknown",
                issue=event.issue_number or "?",
                grade=event.grade,
                confidence=event.confidence or 0.9,
                value=event.metadata.get("value", 0),
                is_key_issue=event.is_key_issue,
                defects=event.defects,
                writer=event.metadata.get("writer", ""),
                artist=event.metadata.get("artist", ""),
                publisher=event.metadata.get("publisher", "")
            )

    async def _on_error(self, event: GradingEvent):
        """Called when an error occurs - Bree gets annoyed"""
        if not self.enabled:
            return

        bree = self._get_bree()
        if bree and bree.enabled:
            await bree.insult_user(f"causing error: {event.error}")


# =============================================================================
# GLOBAL EVENT BUS & TRIGGERS
# =============================================================================

# Global event bus instance
_event_bus: Optional[GradingEventBus] = None
_voice_triggers: Optional[RaistlinVoiceTriggers] = None
_bree_triggers: Optional[BreeVoiceTriggers] = None
_active_personality: VoicePersonality = VoicePersonality.RAISTLIN


def get_event_bus() -> GradingEventBus:
    """Get or create the global event bus"""
    global _event_bus
    if _event_bus is None:
        _event_bus = GradingEventBus()
    return _event_bus


def init_voice_triggers(
    enabled: bool = True,
    personality: VoicePersonality = VoicePersonality.RAISTLIN
) -> Any:
    """
    Initialize voice triggers on the global event bus.

    Args:
        enabled: Whether voice feedback is enabled
        personality: Which personality to use (RAISTLIN or BREE)

    Returns:
        The voice triggers instance
    """
    global _voice_triggers, _bree_triggers, _active_personality
    event_bus = get_event_bus()
    _active_personality = personality

    if personality == VoicePersonality.BREE:
        _bree_triggers = BreeVoiceTriggers(event_bus, enabled=enabled)
        return _bree_triggers
    else:
        _voice_triggers = RaistlinVoiceTriggers(event_bus, enabled=enabled)
        return _voice_triggers


def init_both_voice_systems(enabled: bool = True):
    """Initialize both Raistlin and Bree voice systems"""
    global _voice_triggers, _bree_triggers
    event_bus = get_event_bus()
    _voice_triggers = RaistlinVoiceTriggers(event_bus, enabled=enabled)
    _bree_triggers = BreeVoiceTriggers(event_bus, enabled=enabled)
    return _voice_triggers, _bree_triggers


def set_active_personality(personality: VoicePersonality):
    """Switch active voice personality"""
    global _active_personality, _voice_triggers, _bree_triggers
    _active_personality = personality

    # Enable/disable based on selection
    if _voice_triggers:
        _voice_triggers.enabled = (personality == VoicePersonality.RAISTLIN)
    if _bree_triggers:
        _bree_triggers.enabled = (personality == VoicePersonality.BREE)


def get_voice_triggers() -> Optional[RaistlinVoiceTriggers]:
    """Get Raistlin voice triggers instance"""
    return _voice_triggers


def get_bree_triggers() -> Optional[BreeVoiceTriggers]:
    """Get Bree voice triggers instance"""
    return _bree_triggers


def get_active_personality() -> VoicePersonality:
    """Get currently active voice personality"""
    return _active_personality


# =============================================================================
# CONVENIENCE FUNCTIONS FOR EMITTING EVENTS
# =============================================================================

async def emit_grading_started(title: str = "", issue: str = "", metadata: Dict = None):
    """Emit grading started event"""
    event = GradingEvent(
        event_type=GradingEventType.GRADING_STARTED,
        comic_title=title,
        issue_number=issue,
        metadata=metadata or {}
    )
    await get_event_bus().emit(event)


async def emit_grading_complete(
    title: str,
    issue: str,
    grade: float,
    confidence: float,
    defects: List[str] = None,
    is_key_issue: bool = False,
    metadata: Dict = None
):
    """Emit grading complete event"""
    event = GradingEvent(
        event_type=GradingEventType.GRADING_COMPLETE,
        comic_title=title,
        issue_number=issue,
        grade=grade,
        confidence=confidence,
        defects=defects or [],
        is_key_issue=is_key_issue,
        metadata=metadata or {}
    )
    await get_event_bus().emit(event)


async def emit_ready_for_database(
    title: str,
    issue: str,
    grade: float,
    confidence: float,
    defects: List[str] = None,
    is_key_issue: bool = False,
    metadata: Dict = None
):
    """Emit ready for database event - triggers full Raistlin summary"""
    event = GradingEvent(
        event_type=GradingEventType.READY_FOR_DATABASE,
        comic_title=title,
        issue_number=issue,
        grade=grade,
        confidence=confidence,
        defects=defects or [],
        is_key_issue=is_key_issue,
        metadata=metadata or {}
    )
    await get_event_bus().emit(event)


async def emit_database_saved(title: str = "", issue: str = ""):
    """Emit database saved event - triggers next comic prompt"""
    event = GradingEvent(
        event_type=GradingEventType.DATABASE_SAVED,
        comic_title=title,
        issue_number=issue
    )
    await get_event_bus().emit(event)


async def emit_key_issue_detected(title: str, issue: str, significance: str = ""):
    """Emit key issue detected event"""
    event = GradingEvent(
        event_type=GradingEventType.KEY_ISSUE_DETECTED,
        comic_title=title,
        issue_number=issue,
        is_key_issue=True,
        metadata={"significance": significance}
    )
    await get_event_bus().emit(event)


async def emit_error(error_message: str, title: str = "", issue: str = ""):
    """Emit error event"""
    event = GradingEvent(
        event_type=GradingEventType.ERROR_OCCURRED,
        comic_title=title,
        issue_number=issue,
        error=error_message
    )
    await get_event_bus().emit(event)


async def emit_batch_complete(count: int):
    """Emit batch complete event"""
    event = GradingEvent(
        event_type=GradingEventType.BATCH_COMPLETE,
        metadata={"count": count}
    )
    await get_event_bus().emit(event)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'GradingEventType',
    'GradingEvent',
    'GradingEventBus',
    'VoicePersonality',
    'RaistlinVoiceTriggers',
    'BreeVoiceTriggers',
    'get_event_bus',
    'init_voice_triggers',
    'init_both_voice_systems',
    'set_active_personality',
    'get_voice_triggers',
    'get_bree_triggers',
    'get_active_personality',
    'emit_grading_started',
    'emit_grading_complete',
    'emit_ready_for_database',
    'emit_database_saved',
    'emit_key_issue_detected',
    'emit_error',
    'emit_batch_complete',
]


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    async def test_events():
        print("=" * 60)
        print("GRADING EVENT SYSTEM TEST")
        print("=" * 60)
        print()

        # Initialize event bus and voice triggers
        event_bus = get_event_bus()
        voice_triggers = init_voice_triggers(enabled=True)

        print(f"Event Bus: {event_bus}")
        print(f"Voice Triggers: {voice_triggers}")
        print(f"Voice Enabled: {voice_triggers.enabled}")
        print()

        # Test event emission
        print("Testing: Grading Started...")
        await emit_grading_started("Amazing Spider-Man", "129")
        await asyncio.sleep(1)

        print("\nTesting: Grading Complete...")
        await emit_grading_complete(
            title="Amazing Spider-Man",
            issue="129",
            grade=9.4,
            confidence=0.92,
            defects=["minor spine stress"],
            is_key_issue=True
        )
        await asyncio.sleep(1)

        print("\nTesting: Ready for Database (Full Summary)...")
        await emit_ready_for_database(
            title="Amazing Spider-Man",
            issue="129",
            grade=9.4,
            confidence=0.92,
            defects=["minor spine stress", "light corner wear"],
            is_key_issue=True
        )
        await asyncio.sleep(1)

        print("\nTesting: Database Saved (Next Comic Prompt)...")
        await emit_database_saved("Amazing Spider-Man", "129")
        await asyncio.sleep(1)

        print("\nTest complete!")

    asyncio.run(test_events())
