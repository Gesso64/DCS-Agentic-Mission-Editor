"""Importer: .miz → MissionSpec.

NOT YET IMPLEMENTED — see PLAN.md Phase 6.

The importer is the symmetric inverse of pipeline/builders/. Every
build_<concern>(mission, spec, report) in builders/ should be paired
with a read_<concern>(mission, report) -> partial_spec_data here.
Round-trip equality (spec → miz → spec) is the acceptance criterion.
"""
