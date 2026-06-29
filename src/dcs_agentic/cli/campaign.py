"""CLI command: campaign — multi-mission campaign management.

Usage:
    dcs-agentic campaign init --name op-lion --prompt "..."
    dcs-agentic campaign run --name op-lion
    dcs-agentic campaign report --name op-lion --blue-win
    dcs-agentic campaign inspect --name op-lion
"""

import argparse
import json
import sys
from pathlib import Path

from ..campaign.runner import CampaignRunner
from ..schemas import CampaignSpec, CampaignState


def register_subcommand(subparsers) -> None:
    """Register the 'campaign' subcommand."""
    parser = subparsers.add_parser(
        "campaign",
        help="Manage multi-mission campaigns",
        description="Initialize, run, report, and inspect campaigns. "
                    "A campaign is a sequence of missions with persistent state.",
    )
    sub = parser.add_subparsers(dest="campaign_action", required=True)

    # init
    init_parser = sub.add_parser("init", help="Initialize a new campaign")
    init_parser.add_argument("--name", type=str, required=True, help="Campaign name")
    init_parser.add_argument("--prompt", type=str, required=True, help="Campaign description")
    init_parser.add_argument("--theatre", type=str, default="Caucasus", help="Theatre")
    init_parser.add_argument("--model", type=str, default=None, help="LLM model override")
    init_parser.add_argument("--dir", type=str, default="campaigns", help="Campaigns directory")

    # run
    run_parser = sub.add_parser("run", help="Produce the next mission in the campaign")
    run_parser.add_argument("--name", type=str, required=True, help="Campaign name")
    run_parser.add_argument("--model", type=str, default=None, help="LLM model override")
    run_parser.add_argument("--dir", type=str, default="campaigns", help="Campaigns directory")

    # report
    report_parser = sub.add_parser("report", help="Report the outcome of the last mission")
    report_parser.add_argument("--name", type=str, required=True, help="Campaign name")
    report_parser.add_argument("--winner", type=str, default=None,
                               help="'blue', 'red', or 'draw'")
    report_parser.add_argument("--blue-score", type=int, default=0)
    report_parser.add_argument("--red-score", type=int, default=0)
    report_parser.add_argument("--from", dest="from_file", type=str, default=None,
                               help="Read outcome from a file (.json from Lua hook, or .acmi)")
    report_parser.add_argument("--dir", type=str, default="campaigns", help="Campaigns directory")

    # inspect
    inspect_parser = sub.add_parser("inspect", help="Show campaign state")
    inspect_parser.add_argument("--name", type=str, required=True, help="Campaign name")
    inspect_parser.add_argument("--dir", type=str, default="campaigns", help="Campaigns directory")

    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    """Execute the campaign command."""
    campaign_dir = Path(args.dir) / args.name
    campaign_dir.mkdir(parents=True, exist_ok=True)

    if args.campaign_action == "init":
        from ..agents.campaign_agent import design_campaign
        print(f"\n🧠 Designing campaign from prompt...")
        print(f"  Name: {args.name}")
        print(f"  Prompt: {args.prompt}")
        print()

        campaign = design_campaign(
            prompt=args.prompt,
            theatre=args.theatre,
            model=args.model,
        )

        # Save campaign spec
        spec_path = campaign_dir / "campaign.json"
        with open(spec_path, "w", encoding="utf-8") as f:
            f.write(campaign.model_dump_json(indent=2))

        # Save initial state
        state = campaign.initial_state
        state.current_mission = campaign.start_mission
        state_path = campaign_dir / "state.json"
        with open(state_path, "w", encoding="utf-8") as f:
            f.write(state.model_dump_json(indent=2))

        print(f"✅ Campaign initialized: {campaign.name}")
        print(f"  Missions: {len(campaign.missions)}")
        print(f"  Start: {campaign.start_mission}")
        print(f"  Spec: {spec_path}")
        print(f"  State: {state_path}")

    elif args.campaign_action == "run":
        from ..agents.campaign_agent import render_mission
        runner = CampaignRunner.load(campaign_dir)
        print(f"\n🎯 Running campaign: {runner.campaign.name}")
        print(f"  Current mission: {runner.state.current_mission}")
        print()

        spec = render_mission(
            campaign=runner.campaign,
            state=runner.state,
            template_dir=str(campaign_dir / "templates"),
            model=args.model,
        )

        from ..pipeline import MissionAssembler
        output_path = str(campaign_dir / "missions" / f"{runner.state.current_mission}.miz")
        assembler = MissionAssembler(spec)
        assembler.save(output_path)

        print(f"✅ Mission produced: {output_path}")
        print("Assembly report:")
        print(assembler.report.format())

    elif args.campaign_action == "report":
        runner = CampaignRunner.load(campaign_dir)
        from ..campaign.after_action import AfterAction, load_outcome

        if args.from_file:
            outcome = load_outcome(
                args.from_file,
                mission_name=runner.state.current_mission or None,
            )
            # CLI flags override file values when explicitly set
            if args.winner is not None:
                outcome = outcome.model_copy(update={"winner": args.winner})
            if args.blue_score:
                outcome = outcome.model_copy(update={"blue_score": args.blue_score})
            if args.red_score:
                outcome = outcome.model_copy(update={"red_score": args.red_score})
            print(f"📥 Loaded outcome from: {args.from_file}")
        else:
            outcome = AfterAction(
                mission_name=runner.state.current_mission or "unknown",
                winner=args.winner,
                blue_score=args.blue_score,
                red_score=args.red_score,
            )
        runner.record_outcome(outcome)
        print(f"📊 Outcome recorded for: {outcome.mission_name}")
        print(f"  Winner: {outcome.winner}")
        print(f"  Score: Blue {outcome.blue_score} - Red {outcome.red_score}")
        print(f"  Next: {runner.state.current_mission or '(campaign complete)'}")

    elif args.campaign_action == "inspect":
        runner = CampaignRunner.load(campaign_dir)
        print(f"\n📋 Campaign: {runner.campaign.name}")
        print(f"  Theatre: {runner.campaign.theatre}")
        print(f"  Current mission: {runner.state.current_mission}")
        print(f"  Completed: {len(runner.state.completed_missions)} missions")
        print(f"  Day: {runner.state.day_number}")
        print(f"  Score: Blue {runner.state.score.get('blue', 0)} - "
              f"Red {runner.state.score.get('red', 0)}")
        if runner.state.losses.get("blue"):
            print(f"  Blue losses: {', '.join(runner.state.losses['blue'])}")
        if runner.state.losses.get("red"):
            print(f"  Red losses: {', '.join(runner.state.losses['red'])}")
        if runner.state.captured_airfields:
            print(f"  Captured airfields: {runner.state.captured_airfields}")