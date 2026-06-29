"""Campaign runner — loads/saves state, advances campaign.

Part of Phase 10. Loads campaign spec + state from disk, manages
branching logic, and drives the per-mission render cycle.

Usage:
    runner = CampaignRunner.load(campaign_dir)
    runner.record_outcome(outcome)
    runner.is_complete()
"""

import json
from pathlib import Path
from typing import Optional, Tuple

from ..schemas import CampaignSpec, CampaignState
from .after_action import AfterAction


class CampaignRunner:
    """Loads campaign + state from disk and manages mission-to-mission flow.

    Attributes:
        campaign: The CampaignSpec definition (immutable).
        state: Current mutable CampaignState (written to state.json).
        campaign_dir: Directory containing campaign.json and state.json.
    """

    def __init__(self, campaign: CampaignSpec, state: CampaignState, campaign_dir: Path):
        self.campaign = campaign
        self.state = state
        self.campaign_dir = Path(campaign_dir)

    @classmethod
    def load(cls, campaign_dir: str) -> "CampaignRunner":
        """Load a campaign from its directory.

        Reads campaign.json and state.json from disk and returns a
        CampaignRunner ready to produce the next mission.

        Args:
            campaign_dir: Path to the campaign directory

        Returns:
            CampaignRunner instance
        """
        campaign_dir = Path(campaign_dir)
        with open(campaign_dir / "campaign.json", "r", encoding="utf-8") as f:
            campaign_data = json.load(f)
        campaign = CampaignSpec.model_validate(campaign_data)

        state_path = campaign_dir / "state.json"
        if state_path.exists():
            with open(state_path, "r", encoding="utf-8") as f:
                state_data = json.load(f)
            state = CampaignState.model_validate(state_data)
        else:
            state = campaign.initial_state
            state.current_mission = campaign.start_mission

        return cls(campaign, state, campaign_dir)

    def record_outcome(self, outcome: AfterAction) -> None:
        """Record the outcome of a completed mission and advance the campaign.

        Updates state with scores, losses, captured airfields, and determines
        the next mission to play based on branching rules.

        Args:
            outcome: AfterAction from the just-completed mission
        """
        # Update scores
        self.state.score["blue"] = self.state.score.get("blue", 0) + outcome.blue_score
        self.state.score["red"] = self.state.score.get("red", 0) + outcome.red_score

        # Update losses
        self.state.losses["blue"].extend(outcome.blue_losses)
        self.state.losses["red"].extend(outcome.red_losses)

        # Update captured airfields
        self.state.captured_airfields.update(outcome.captured)

        # Update flags
        self.state.flags.update(outcome.flags_set)

        # Mark mission as completed
        if outcome.mission_name not in self.state.completed_missions:
            self.state.completed_missions.append(outcome.mission_name)

        # Determine next mission
        mission_link = None
        for m in self.campaign.missions:
            if m.name == outcome.mission_name:
                mission_link = m
                break

        if mission_link is None:
            self.state.current_mission = None
        elif mission_link.next_unconditional:
            self.state.current_mission = mission_link.next_unconditional
        elif outcome.winner == "blue" and mission_link.next_on_blue_win:
            self.state.current_mission = mission_link.next_on_blue_win
        elif outcome.winner == "red" and mission_link.next_on_red_win:
            self.state.current_mission = mission_link.next_on_red_win
        elif outcome.winner == "draw" and mission_link.next_on_draw:
            self.state.current_mission = mission_link.next_on_draw
        else:
            # No matching branch — campaign ends
            self.state.current_mission = None

        # Advance day
        self.state.day_number += 1

        # Save state
        self._save_state()

    def _save_state(self) -> None:
        """Persist current state to state.json."""
        state_path = self.campaign_dir / "state.json"
        with open(state_path, "w", encoding="utf-8") as f:
            f.write(self.state.model_dump_json(indent=2))

    def is_complete(self) -> bool:
        """True if the campaign has no more missions to run."""
        return self.state.current_mission is None

    def get_current_mission_link(self) -> Optional[object]:
        """Return the MissionLink object for the current mission."""
        for m in self.campaign.missions:
            if m.name == self.state.current_mission:
                return m
        return None