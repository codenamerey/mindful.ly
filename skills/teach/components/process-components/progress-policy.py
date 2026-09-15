from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class ProgressFacts:
    completion_dates: tuple[date, ...]
    completed_assignments: int
    completed_by_phase: dict[int, int]
    required_by_phase: dict[int, int]

    def streak(self, today=None):
        current = today or date.today()
        completed = set(self.completion_dates)
        if current not in completed and current - timedelta(days=1) not in completed:
            return 0
        cursor = current if current in completed else current - timedelta(days=1)
        total = 0
        while cursor in completed:
            total += 1
            cursor -= timedelta(days=1)
        return total

    def achievement_slugs(self):
        earned = set()
        if self.completed_assignments >= 1:
            earned.add("first_completion")
        if self.streak() >= 7:
            earned.add("seven_day_streak")
        for phase, required in self.required_by_phase.items():
            if required > 0 and self.completed_by_phase.get(phase, 0) >= required:
                earned.add(f"phase_{phase}_complete")
        return earned


def level_for(xp, levels):
    eligible = [(threshold, name, icon) for threshold, name, icon in levels if xp >= threshold]
    if not eligible:
        raise ValueError("Levels must include a threshold at or below current XP")
    return max(eligible, key=lambda item: item[0])
