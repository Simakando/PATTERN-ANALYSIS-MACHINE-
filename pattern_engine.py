"""
Pattern Detection Engine — BetPawa Virtual Football
Detects and records signals/patterns for Over 3.5 Goals.

Pattern categories analysed:
  1. Odds-range patterns  (e.g., "when over35 odds are 1.6–1.9, hit rate is X%")
  2. Team-specific patterns (teams that consistently appear in high-scoring games)
  3. League-level patterns (leagues with above-average over 3.5 rates)
  4. Consecutive-match patterns (hot streaks)
  5. Head-to-head patterns (specific team pairings)
  6. Odds-ratio patterns (relationship between 1X2 odds spread and goals)
  7. Time-session patterns (if time data available)
  8. Score-line distribution patterns
  9. Draw-adjusted patterns (games priced as draws tend to → more goals?)
 10. Under-pressure patterns (away underdog scenario goals)

Minimum occurrences for a pattern to qualify: 10
"""

import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

MIN_OCCURRENCES = 10  # Must appear in at least this many matches


def signal_strength(rate, occurrences):
    """
    Compute signal strength (0–100) combining hit-rate and sample size.
    Uses a simplified Wilson-like score.
    """
    # Penalise small samples; reward high rates
    size_factor = min(occurrences / 50, 1.0)  # caps at 50 matches
    return round((rate / 100) * 70 + size_factor * 30, 1)


class PatternEngine:

    def detect_patterns(self, matches):
        """Run all detectors and return qualifying patterns."""
        if not matches:
            return []

        all_patterns = []
        all_patterns.extend(self._odds_range_patterns(matches))
        all_patterns.extend(self._team_patterns(matches))
        all_patterns.extend(self._league_patterns(matches))
        all_patterns.extend(self._h2h_patterns(matches))
        all_patterns.extend(self._odds_ratio_patterns(matches))
        all_patterns.extend(self._draw_odds_patterns(matches))
        all_patterns.extend(self._underdog_patterns(matches))
        all_patterns.extend(self._scoreline_patterns(matches))
        all_patterns.extend(self._consecutive_patterns(matches))

        # Sort by signal strength descending
        all_patterns.sort(key=lambda p: p.get("signal_strength", 0), reverse=True)

        logger.info(f"Total qualifying patterns: {len(all_patterns)}")
        return all_patterns

    # ── 1. Odds-range patterns ─────────────────────────────────────────────

    def _odds_range_patterns(self, matches):
        """When over35 odds fall in a certain range, what is the hit rate?"""
        patterns = []
        ranges = [
            (1.00, 1.50, "1.00–1.50"),
            (1.51, 1.80, "1.51–1.80"),
            (1.81, 2.10, "1.81–2.10"),
            (2.11, 2.50, "2.11–2.50"),
            (2.51, 3.00, "2.51–3.00"),
            (3.01, 4.00, "3.01–4.00"),
            (4.01, 99.0, "4.01+"),
        ]
        for lo, hi, label in ranges:
            bucket = [
                m for m in matches
                if m.get("odds", {}).get("over35") is not None
                and lo <= m["odds"]["over35"] <= hi
            ]
            if len(bucket) < MIN_OCCURRENCES:
                continue
            over35_count = sum(1 for m in bucket if m.get("over35"))
            rate = round(over35_count / len(bucket) * 100, 1)
            avg_goals = round(sum(m.get("total_goals", 0) for m in bucket) / len(bucket), 2)
            patterns.append({
                "type": "Odds Range",
                "league": "ALL",
                "description": f"Over 3.5 odds in range {label} → {rate}% hit rate",
                "occurrences": len(bucket),
                "over35_rate": rate,
                "avg_goals": avg_goals,
                "signal_strength": signal_strength(rate, len(bucket)),
                "details": f"Odds range: {label} | Matches: {len(bucket)} | Over3.5: {over35_count}",
            })
        return patterns

    # ── 2. Team-specific patterns ──────────────────────────────────────────

    def _team_patterns(self, matches):
        """Teams that appear most often in over 3.5 matches."""
        patterns = []
        team_stats = defaultdict(lambda: {"total": 0, "over35": 0, "goals": 0})
        for m in matches:
            for team_key in ("home_team", "away_team"):
                team = m.get(team_key, "")
                if team:
                    team_stats[team]["total"] += 1
                    if m.get("over35"):
                        team_stats[team]["over35"] += 1
                    team_stats[team]["goals"] += m.get("total_goals", 0)

        for team, stats in team_stats.items():
            if stats["total"] < MIN_OCCURRENCES:
                continue
            rate = round(stats["over35"] / stats["total"] * 100, 1)
            avg_goals = round(stats["goals"] / stats["total"], 2)
            if rate < 45:  # Only record teams with meaningful over 3.5 signal
                continue
            patterns.append({
                "type": "Team Signal",
                "league": "ALL",
                "description": f"{team} appears in Over 3.5 matches {rate}% of the time",
                "occurrences": stats["total"],
                "over35_rate": rate,
                "avg_goals": avg_goals,
                "signal_strength": signal_strength(rate, stats["total"]),
                "details": f"Team: {team} | Matches: {stats['total']} | Over3.5 appearances: {stats['over35']}",
            })
        return patterns

    # ── 3. League-level patterns ───────────────────────────────────────────

    def _league_patterns(self, matches):
        """Which leagues have the highest over 3.5 rates overall?"""
        patterns = []
        league_stats = defaultdict(lambda: {"total": 0, "over35": 0, "goals": 0})
        for m in matches:
            lg = m.get("league", "Unknown")
            league_stats[lg]["total"] += 1
            if m.get("over35"):
                league_stats[lg]["over35"] += 1
            league_stats[lg]["goals"] += m.get("total_goals", 0)

        for league, stats in league_stats.items():
            if stats["total"] < MIN_OCCURRENCES:
                continue
            rate = round(stats["over35"] / stats["total"] * 100, 1)
            avg_goals = round(stats["goals"] / stats["total"], 2)
            patterns.append({
                "type": "League Pattern",
                "league": league,
                "description": f"{league}: {rate}% Over 3.5 rate across {stats['total']} matches",
                "occurrences": stats["total"],
                "over35_rate": rate,
                "avg_goals": avg_goals,
                "signal_strength": signal_strength(rate, stats["total"]),
                "details": (
                    f"League: {league} | Total: {stats['total']} | "
                    f"Over3.5: {stats['over35']} | Avg Goals: {avg_goals}"
                ),
            })
        return patterns

    # ── 4. Head-to-head patterns ───────────────────────────────────────────

    def _h2h_patterns(self, matches):
        """Specific matchup pairings that consistently go over 3.5."""
        patterns = []
        h2h = defaultdict(lambda: {"total": 0, "over35": 0, "goals": 0, "leagues": set()})
        for m in matches:
            home = m.get("home_team", "")
            away = m.get("away_team", "")
            if not home or not away:
                continue
            key = tuple(sorted([home, away]))
            h2h[key]["total"] += 1
            if m.get("over35"):
                h2h[key]["over35"] += 1
            h2h[key]["goals"] += m.get("total_goals", 0)
            h2h[key]["leagues"].add(m.get("league", ""))

        for (t1, t2), stats in h2h.items():
            if stats["total"] < MIN_OCCURRENCES:
                continue
            rate = round(stats["over35"] / stats["total"] * 100, 1)
            avg_goals = round(stats["goals"] / stats["total"], 2)
            if rate < 50:
                continue
            leagues_str = ", ".join(stats["leagues"])
            patterns.append({
                "type": "Head-to-Head",
                "league": leagues_str,
                "description": f"{t1} vs {t2}: {rate}% Over 3.5 in {stats['total']} meetings",
                "occurrences": stats["total"],
                "over35_rate": rate,
                "avg_goals": avg_goals,
                "signal_strength": signal_strength(rate, stats["total"]),
                "details": f"H2H: {t1} vs {t2} | Meetings: {stats['total']} | Avg Goals: {avg_goals}",
            })
        return patterns

    # ── 5. Odds ratio patterns ─────────────────────────────────────────────

    def _odds_ratio_patterns(self, matches):
        """
        When the spread between home_win odds and away_win odds is large
        (big favourite vs underdog), do we see more/fewer goals?
        """
        patterns = []
        buckets = {
            "big_home_fav": [],   # home odds < 1.5, spread > 2.0
            "even_match":   [],   # both odds 1.8–2.5
            "big_away_fav": [],   # away odds < 1.5
            "high_draw":    [],   # draw odds < 3.0
        }
        for m in matches:
            odds = m.get("odds", {})
            ho = odds.get("home_win")
            ao = odds.get("away_win")
            do = odds.get("draw")
            if ho and ao:
                if ho < 1.5 and ao > 3.0:
                    buckets["big_home_fav"].append(m)
                elif ao < 1.5 and ho > 3.0:
                    buckets["big_away_fav"].append(m)
                elif 1.8 <= ho <= 2.5 and 1.8 <= ao <= 2.5:
                    buckets["even_match"].append(m)
            if do and do < 3.0:
                buckets["high_draw"].append(m)

        labels = {
            "big_home_fav": "Big Home Favourite (home odds < 1.5)",
            "even_match":   "Even Match (both sides 1.8–2.5 odds)",
            "big_away_fav": "Big Away Favourite (away odds < 1.5)",
            "high_draw":    "Low Draw Odds (draw < 3.0)",
        }
        for key, bucket in buckets.items():
            if len(bucket) < MIN_OCCURRENCES:
                continue
            over35_count = sum(1 for m in bucket if m.get("over35"))
            rate = round(over35_count / len(bucket) * 100, 1)
            avg_goals = round(sum(m.get("total_goals", 0) for m in bucket) / len(bucket), 2)
            patterns.append({
                "type": "Odds Ratio Signal",
                "league": "ALL",
                "description": f"{labels[key]}: {rate}% Over 3.5",
                "occurrences": len(bucket),
                "over35_rate": rate,
                "avg_goals": avg_goals,
                "signal_strength": signal_strength(rate, len(bucket)),
                "details": f"Scenario: {labels[key]} | Matches: {len(bucket)} | Over3.5: {over35_count}",
            })
        return patterns

    # ── 6. Draw-odds patterns ──────────────────────────────────────────────

    def _draw_odds_patterns(self, matches):
        """
        When draw odds are high (teams rarely draw), does that predict goals?
        High draw odds (e.g., 4.0+) may indicate attacking teams.
        """
        patterns = []
        buckets = {
            "very_high_draw": [m for m in matches if m.get("odds", {}).get("draw", 0) >= 4.0],
            "high_draw":      [m for m in matches if 3.5 <= m.get("odds", {}).get("draw", 0) < 4.0],
            "low_draw":       [m for m in matches if 0 < m.get("odds", {}).get("draw", 0) < 3.0],
        }
        labels = {
            "very_high_draw": "Very High Draw Odds (4.0+)",
            "high_draw":      "High Draw Odds (3.5–3.99)",
            "low_draw":       "Low Draw Odds (<3.0)",
        }
        for key, bucket in buckets.items():
            if len(bucket) < MIN_OCCURRENCES:
                continue
            over35_count = sum(1 for m in bucket if m.get("over35"))
            rate = round(over35_count / len(bucket) * 100, 1)
            avg_goals = round(sum(m.get("total_goals", 0) for m in bucket) / len(bucket), 2)
            patterns.append({
                "type": "Draw Odds Pattern",
                "league": "ALL",
                "description": f"{labels[key]}: {rate}% Over 3.5 rate",
                "occurrences": len(bucket),
                "over35_rate": rate,
                "avg_goals": avg_goals,
                "signal_strength": signal_strength(rate, len(bucket)),
                "details": f"Draw odds category: {labels[key]} | Matches: {len(bucket)}",
            })
        return patterns

    # ── 7. Underdog patterns ───────────────────────────────────────────────

    def _underdog_patterns(self, matches):
        """
        Away underdog (away odds > 3.5) vs away favourite patterns.
        """
        patterns = []
        underdog_away = [m for m in matches if m.get("odds", {}).get("away_win", 0) > 3.5]
        favourite_away = [m for m in matches if 0 < m.get("odds", {}).get("away_win", 0) < 1.8]

        for label, bucket in [("Away Underdog (away odds >3.5)", underdog_away),
                               ("Away Favourite (away odds <1.8)", favourite_away)]:
            if len(bucket) < MIN_OCCURRENCES:
                continue
            over35_count = sum(1 for m in bucket if m.get("over35"))
            rate = round(over35_count / len(bucket) * 100, 1)
            avg_goals = round(sum(m.get("total_goals", 0) for m in bucket) / len(bucket), 2)
            patterns.append({
                "type": "Underdog Signal",
                "league": "ALL",
                "description": f"{label}: {rate}% Over 3.5",
                "occurrences": len(bucket),
                "over35_rate": rate,
                "avg_goals": avg_goals,
                "signal_strength": signal_strength(rate, len(bucket)),
                "details": f"Scenario: {label} | Matches: {len(bucket)} | Over3.5: {over35_count}",
            })
        return patterns

    # ── 8. Scoreline distribution ──────────────────────────────────────────

    def _scoreline_patterns(self, matches):
        """Most frequent scorelines overall and in over 3.5 matches."""
        patterns = []
        scorelines = defaultdict(int)
        for m in matches:
            h, a = m.get("home_score", 0), m.get("away_score", 0)
            scorelines[f"{h}-{a}"] += 1

        for score, count in scorelines.items():
            if count < MIN_OCCURRENCES:
                continue
            try:
                h, a = map(int, score.split("-"))
                total = h + a
                over35 = total > 3
            except Exception:
                continue
            patterns.append({
                "type": "Scoreline Pattern",
                "league": "ALL",
                "description": f"Score {score} appeared {count} times ({'Over' if over35 else 'Under'} 3.5)",
                "occurrences": count,
                "over35_rate": 100.0 if over35 else 0.0,
                "avg_goals": total,
                "signal_strength": signal_strength(100.0 if over35 else 0.0, count),
                "details": f"Scoreline: {score} | Total Goals: {total} | Occurrences: {count}",
            })
        return patterns

    # ── 9. Consecutive patterns ────────────────────────────────────────────

    def _consecutive_patterns(self, matches):
        """
        Detect streaks: leagues/teams with N consecutive over 3.5 results.
        """
        patterns = []
        by_league = defaultdict(list)
        for m in matches:
            by_league[m.get("league", "Unknown")].append(m)

        for league, lg_matches in by_league.items():
            if len(lg_matches) < MIN_OCCURRENCES:
                continue
            # Find longest streak
            current_streak = 0
            max_streak = 0
            streak_counts = defaultdict(int)  # streak_length → how many times seen

            for m in lg_matches:
                if m.get("over35"):
                    current_streak += 1
                    max_streak = max(max_streak, current_streak)
                    if current_streak >= 3:
                        streak_counts[current_streak] += 1
                else:
                    current_streak = 0

            for streak_len, freq in streak_counts.items():
                if freq < MIN_OCCURRENCES // 3:  # relax threshold for streaks
                    continue
                patterns.append({
                    "type": "Consecutive Streak",
                    "league": league,
                    "description": (
                        f"{league}: {streak_len}-game Over 3.5 streak "
                        f"occurred {freq} times"
                    ),
                    "occurrences": freq,
                    "over35_rate": 100.0,
                    "avg_goals": 0,
                    "signal_strength": signal_strength(100.0, freq * streak_len),
                    "details": (
                        f"League: {league} | Streak Length: {streak_len} | "
                        f"Streak Frequency: {freq} | Max Streak: {max_streak}"
                    ),
                })
        return patterns
