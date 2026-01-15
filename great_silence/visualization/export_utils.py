"""
Visualization export utilities.

Exports simulation data in formats suitable for various visualization types:
- Chord diagrams (crisis flows)
- Time series plots (development trajectories)
- Network graphs (cooperation networks)
- Summary statistics
- Interactive dashboards
"""

import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import numpy as np


@dataclass
class VisualizationExport:
    """
    Container for exported visualization data.

    Attributes:
        chord_data: Data for chord diagram (crisis flows)
        timeseries_data: Data for time series plots
        network_data: Data for cooperation network graphs
        summary_stats: Summary statistics
        metadata: Additional metadata about the simulation
    """
    chord_data: Dict[str, Any]
    timeseries_data: Dict[str, Any]
    network_data: Dict[str, Any]
    summary_stats: Dict[str, Any]
    metadata: Dict[str, Any]

    def to_json(self, filepath: str) -> None:
        """
        Export to JSON file.

        Args:
            filepath: Path to output JSON file
        """
        data = {
            'chord_data': self.chord_data,
            'timeseries_data': self.timeseries_data,
            'network_data': self.network_data,
            'summary_stats': self.summary_stats,
            'metadata': self.metadata
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    @classmethod
    def from_json(cls, filepath: str) -> 'VisualizationExport':
        """
        Load from JSON file.

        Args:
            filepath: Path to JSON file

        Returns:
            VisualizationExport instance
        """
        with open(filepath, 'r') as f:
            data = json.load(f)

        return cls(
            chord_data=data['chord_data'],
            timeseries_data=data['timeseries_data'],
            network_data=data['network_data'],
            summary_stats=data['summary_stats'],
            metadata=data['metadata']
        )


class VisualizationExporter:
    """
    Exports simulation data for visualization.

    Processes telemetry, cooperation, and development data into
    formats suitable for various visualization libraries.
    """

    def __init__(self):
        """Initialize visualization exporter."""
        pass

    def export_chord_diagram_data(
        self,
        telemetry_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Export data for crisis flow chord diagram.

        Shows flows between crisis types and outcomes.

        Args:
            telemetry_data: Telemetry data from simulation

        Returns:
            Chord diagram data structure
        """
        # Extract crisis events
        crisis_events = telemetry_data.get('crisis_events', [])

        # Build flow matrix: crisis_type → outcome
        flows = {}

        for event in crisis_events:
            crisis_type = event.get('crisis_type', 'unknown')
            outcome = event.get('outcome', 'unknown')

            key = f"{crisis_type}→{outcome}"
            flows[key] = flows.get(key, 0) + 1

        # Convert to chord diagram format
        nodes = set()
        for key in flows.keys():
            source, target = key.split('→')
            nodes.add(source)
            nodes.add(target)

        node_list = sorted(list(nodes))
        node_indices = {name: i for i, name in enumerate(node_list)}

        # Build matrix
        matrix = [[0] * len(node_list) for _ in range(len(node_list))]

        for key, count in flows.items():
            source, target = key.split('→')
            src_idx = node_indices[source]
            tgt_idx = node_indices[target]
            matrix[src_idx][tgt_idx] = count

        return {
            'nodes': node_list,
            'matrix': matrix,
            'total_events': len(crisis_events)
        }

    def export_timeseries_data(
        self,
        civilization_histories: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Export development trajectory time series.

        Args:
            civilization_histories: List of civilization development histories

        Returns:
            Time series data structure
        """
        timeseries = {
            'civilizations': []
        }

        for civ_history in civilization_histories:
            civ_id = civ_history.get('id', 0)
            snapshots = civ_history.get('development_snapshots', [])

            if not snapshots:
                continue

            times = [s.get('time_myr', 0) for s in snapshots]
            kardashev = [s.get('kardashev_level', 0) for s in snapshots]
            maturity = [s.get('maturity_level', 0) for s in snapshots]
            velocity = [s.get('development_velocity', 0) for s in snapshots]

            timeseries['civilizations'].append({
                'id': civ_id,
                'times': times,
                'kardashev_levels': kardashev,
                'maturity_levels': maturity,
                'development_velocities': velocity,
                'path_type': civ_history.get('development_path_type', 'unknown')
            })

        return timeseries

    def export_cooperation_network(
        self,
        cooperation_records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Export cooperation network graph data.

        Args:
            cooperation_records: List of cooperation records

        Returns:
            Network graph data structure
        """
        # Build nodes (civilizations)
        nodes = {}
        edges = []

        for record in cooperation_records:
            helper_id = record.get('helper_id')
            receiver_id = record.get('receiver_id')
            effectiveness = record.get('effectiveness', 0)
            coop_type = record.get('cooperation_type', 'unknown')

            # Add nodes
            if helper_id not in nodes:
                nodes[helper_id] = {
                    'id': helper_id,
                    'aid_given': 0,
                    'aid_received': 0
                }
            if receiver_id not in nodes:
                nodes[receiver_id] = {
                    'id': receiver_id,
                    'aid_given': 0,
                    'aid_received': 0
                }

            # Update counts
            nodes[helper_id]['aid_given'] += 1
            nodes[receiver_id]['aid_received'] += 1

            # Add edge
            edges.append({
                'source': helper_id,
                'target': receiver_id,
                'weight': effectiveness,
                'type': coop_type
            })

        return {
            'nodes': list(nodes.values()),
            'edges': edges,
            'total_cooperations': len(cooperation_records)
        }

    def calculate_summary_statistics(
        self,
        telemetry_data: Dict[str, Any],
        civilization_histories: List[Dict[str, Any]],
        cooperation_records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate summary statistics across simulation.

        Args:
            telemetry_data: Telemetry data
            civilization_histories: Development histories
            cooperation_records: Cooperation records

        Returns:
            Summary statistics
        """
        stats = {}

        # Crisis statistics
        crisis_events = telemetry_data.get('crisis_events', [])
        stats['total_crises'] = len(crisis_events)

        survived = sum(1 for e in crisis_events if e.get('outcome') == 'survived')
        failed = sum(1 for e in crisis_events if e.get('outcome') == 'failed')

        stats['crises_survived'] = survived
        stats['crises_failed'] = failed
        stats['survival_rate'] = survived / len(crisis_events) if crisis_events else 0.0

        # Count by crisis type
        crisis_types = {}
        for event in crisis_events:
            ctype = event.get('crisis_type', 'unknown')
            crisis_types[ctype] = crisis_types.get(ctype, 0) + 1

        stats['crises_by_type'] = crisis_types

        # Development path statistics
        path_types = {}
        avg_velocities = []

        for civ_hist in civilization_histories:
            path_type = civ_hist.get('development_path_type', 'unknown')
            path_types[path_type] = path_types.get(path_type, 0) + 1

            snapshots = civ_hist.get('development_snapshots', [])
            if snapshots:
                velocities = [s.get('development_velocity', 0) for s in snapshots]
                avg_velocities.append(np.mean(velocities))

        stats['development_paths'] = path_types
        stats['avg_development_velocity'] = float(np.mean(avg_velocities)) if avg_velocities else 0.0

        # Cooperation statistics
        stats['total_cooperations'] = len(cooperation_records)

        coop_types = {}
        for record in cooperation_records:
            ctype = record.get('cooperation_type', 'unknown')
            coop_types[ctype] = coop_types.get(ctype, 0) + 1

        stats['cooperations_by_type'] = coop_types

        # Calculate cooperation effectiveness
        if cooperation_records:
            effectiveness_values = [r.get('effectiveness', 0) for r in cooperation_records]
            stats['avg_cooperation_effectiveness'] = float(np.mean(effectiveness_values))
        else:
            stats['avg_cooperation_effectiveness'] = 0.0

        return stats

    def export_all(
        self,
        telemetry_data: Dict[str, Any],
        civilization_histories: List[Dict[str, Any]],
        cooperation_records: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> VisualizationExport:
        """
        Export all visualization data.

        Args:
            telemetry_data: Telemetry data from simulation
            civilization_histories: Development histories
            cooperation_records: Cooperation records
            metadata: Optional metadata about simulation

        Returns:
            VisualizationExport with all data
        """
        chord_data = self.export_chord_diagram_data(telemetry_data)
        timeseries_data = self.export_timeseries_data(civilization_histories)
        network_data = self.export_cooperation_network(cooperation_records)
        summary_stats = self.calculate_summary_statistics(
            telemetry_data,
            civilization_histories,
            cooperation_records
        )

        return VisualizationExport(
            chord_data=chord_data,
            timeseries_data=timeseries_data,
            network_data=network_data,
            summary_stats=summary_stats,
            metadata=metadata or {}
        )


def print_summary_report(export: VisualizationExport) -> None:
    """
    Print a human-readable summary report.

    Args:
        export: VisualizationExport to summarize
    """
    stats = export.summary_stats

    print("\n" + "="*60)
    print("SIMULATION SUMMARY REPORT")
    print("="*60)

    # Crisis statistics
    print("\n📊 CRISIS STATISTICS")
    print("-" * 60)
    print(f"Total crises:        {stats['total_crises']}")
    print(f"Survived:            {stats['crises_survived']}")
    print(f"Failed:              {stats['crises_failed']}")
    print(f"Survival rate:       {stats['survival_rate']:.1%}")

    print("\nCrises by type:")
    for ctype, count in sorted(stats['crises_by_type'].items()):
        print(f"  {ctype:30s} {count:3d}")

    # Development statistics
    print("\n🚀 DEVELOPMENT STATISTICS")
    print("-" * 60)
    print(f"Avg development velocity: {stats['avg_development_velocity']:.4f} K/Myr")

    print("\nDevelopment paths:")
    for path, count in sorted(stats['development_paths'].items()):
        print(f"  {path:30s} {count:3d}")

    # Cooperation statistics
    print("\n🤝 COOPERATION STATISTICS")
    print("-" * 60)
    print(f"Total cooperations:     {stats['total_cooperations']}")
    print(f"Avg effectiveness:      {stats['avg_cooperation_effectiveness']:.2f}")

    if stats['cooperations_by_type']:
        print("\nCooperations by type:")
        for ctype, count in sorted(stats['cooperations_by_type'].items()):
            print(f"  {ctype:30s} {count:3d}")

    # Chord diagram info
    print("\n📈 VISUALIZATION DATA")
    print("-" * 60)
    print(f"Chord nodes:         {len(export.chord_data['nodes'])}")
    print(f"Timeseries civs:     {len(export.timeseries_data['civilizations'])}")
    print(f"Network nodes:       {len(export.network_data['nodes'])}")
    print(f"Network edges:       {len(export.network_data['edges'])}")

    print("\n" + "="*60 + "\n")
