"""
Interactive Plotly-based visualizations for Jupyter notebooks.

Provides functions for creating interactive 3D galaxy views, timelines,
and statistics dashboards suitable for exploration in JupyterLab.
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
from typing import Dict, Any, Optional, List


def create_3d_galaxy_view(
    data: Dict[str, Any],
    title: str = "Galactic Civilization Map"
) -> go.Figure:
    """
    Create realistic 3D interactive galaxy visualization.

    Args:
        data: Simulation data dictionary with 'civilizations' key
        title: Plot title

    Returns:
        Plotly Figure object with interactive 3D visualization
    """
    fig = go.Figure()

    # Separate civilizations by status and cause of death
    alive_civs = [c for c in data['civilizations'] if c['alive']]
    dead_crisis = [c for c in data['civilizations']
                   if not c['alive'] and
                   any(x in (c.get('cause_of_death') or '') for x in
                       ['climate', 'nuclear', 'ai', 'biotech', 'resource',
                        'nanotech', 'stellar', 'singularity'])]
    dead_sn = [c for c in data['civilizations']
               if not c['alive'] and 'supernova' in (c.get('cause_of_death') or '')]
    dead_grb = [c for c in data['civilizations']
                if not c['alive'] and 'gamma' in (c.get('cause_of_death') or '')]

    # Kardashev color mapping
    kardashev_colors = {
        0.5: '#3498db',  # Type 0.5 - Blue (planetary)
        1.0: '#2ecc71',  # Type I - Green (planetary mastery)
        1.5: '#f39c12',  # Type 1.5 - Orange (interplanetary)
        2.0: '#e74c3c',  # Type II - Red (stellar)
        2.5: '#9b59b6',  # Type 2.5 - Purple (multi-stellar)
        3.0: '#e91e63'   # Type III - Pink (galactic)
    }

    # Add alive civilizations (color-coded by Kardashev level)
    for k_level in sorted(kardashev_colors.keys()):
        civs_at_level = [c for c in alive_civs if abs(c['kardashev_level'] - k_level) < 0.25]
        if civs_at_level:
            x = [c['position'][0] for c in civs_at_level]
            y = [c['position'][1] for c in civs_at_level]
            z = [c['position'][2] for c in civs_at_level]

            hover_text = [
                f"ID: {c['id']}<br>" +
                f"Kardashev: {c['kardashev_level']:.2f}<br>" +
                f"Maturity: {c['social_maturity']:.2f}<br>" +
                f"Age: {c['age']:.1f} Myr"
                for c in civs_at_level
            ]

            fig.add_trace(go.Scatter3d(
                x=x, y=y, z=z,
                mode='markers',
                marker=dict(
                    size=8,
                    color=kardashev_colors[k_level],
                    symbol='diamond',
                    line=dict(color='white', width=1)
                ),
                name=f'Type {k_level} (Alive)',
                hovertext=hover_text,
                hoverinfo='text'
            ))

    # Add dead civilizations (crisis)
    if dead_crisis:
        x = [c['position'][0] for c in dead_crisis]
        y = [c['position'][1] for c in dead_crisis]
        z = [c['position'][2] for c in dead_crisis]

        hover_text = [
            f"ID: {c['id']}<br>" +
            f"Cause: {c.get('cause_of_death', 'unknown')}<br>" +
            f"Final Kardashev: {c['kardashev_level']:.2f}<br>" +
            f"Lifespan: {c['age']:.1f} Myr"
            for c in dead_crisis
        ]

        fig.add_trace(go.Scatter3d(
            x=x, y=y, z=z,
            mode='markers',
            marker=dict(
                size=6,
                color='#95a5a6',
                symbol='x',
                line=dict(color='red', width=2)
            ),
            name='Dead (Self-destruction)',
            hovertext=hover_text,
            hoverinfo='text'
        ))

    # Add dead civilizations (supernova)
    if dead_sn:
        x = [c['position'][0] for c in dead_sn]
        y = [c['position'][1] for c in dead_sn]
        z = [c['position'][2] for c in dead_sn]

        hover_text = [
            f"ID: {c['id']}<br>" +
            f"Cause: Supernova<br>" +
            f"Final Kardashev: {c['kardashev_level']:.2f}<br>" +
            f"Lifespan: {c['age']:.1f} Myr"
            for c in dead_sn
        ]

        fig.add_trace(go.Scatter3d(
            x=x, y=y, z=z,
            mode='markers',
            marker=dict(
                size=6,
                color='#e67e22',
                symbol='x',
                line=dict(color='orange', width=2)
            ),
            name='Dead (Supernova)',
            hovertext=hover_text,
            hoverinfo='text'
        ))

    # Add dead civilizations (GRB)
    if dead_grb:
        x = [c['position'][0] for c in dead_grb]
        y = [c['position'][1] for c in dead_grb]
        z = [c['position'][2] for c in dead_grb]

        hover_text = [
            f"ID: {c['id']}<br>" +
            f"Cause: Gamma-ray Burst<br>" +
            f"Final Kardashev: {c['kardashev_level']:.2f}<br>" +
            f"Lifespan: {c['age']:.1f} Myr"
            for c in dead_grb
        ]

        fig.add_trace(go.Scatter3d(
            x=x, y=y, z=z,
            mode='markers',
            marker=dict(
                size=6,
                color='#8e44ad',
                symbol='x',
                line=dict(color='purple', width=2)
            ),
            name='Dead (GRB)',
            hovertext=hover_text,
            hoverinfo='text'
        ))

    # Add astrophysical events if present
    # Try both possible keys for backward compatibility
    sn_events = data.get('supernova_events', data.get('supernovae', []))
    if sn_events:
        # Handle both list of dicts and list of positions
        if isinstance(sn_events[0], dict):
            sn_pos = np.array([evt['position'] for evt in sn_events[:50]])
        else:
            sn_pos = np.array(sn_events[:50])

        fig.add_trace(go.Scatter3d(
            x=sn_pos[:, 0], y=sn_pos[:, 1], z=sn_pos[:, 2],
            mode='markers',
            marker=dict(
                size=4,
                color='orange',
                opacity=0.3,
                symbol='star'
            ),
            name=f'Supernovae ({len(sn_events)})',
            hoverinfo='name'
        ))

    grb_events = data.get('grb_events', data.get('grbs', []))
    if grb_events:
        # Handle both list of dicts and list of positions
        if isinstance(grb_events[0], dict):
            grb_pos = np.array([evt['position'] for evt in grb_events[:50]])
        else:
            grb_pos = np.array(grb_events[:50])

        fig.add_trace(go.Scatter3d(
            x=grb_pos[:, 0], y=grb_pos[:, 1], z=grb_pos[:, 2],
            mode='markers',
            marker=dict(
                size=4,
                color='purple',
                opacity=0.3,
                symbol='diamond-open'
            ),
            name=f'GRBs ({len(grb_events)})',
            hoverinfo='name'
        ))

    # Update layout for realistic space theme
    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20, 'color': 'white'}
        },
        scene=dict(
            xaxis=dict(
                title='X (kpc)',
                backgroundcolor='black',
                gridcolor='#2c3e50',
                showbackground=True,
                color='white'
            ),
            yaxis=dict(
                title='Y (kpc)',
                backgroundcolor='black',
                gridcolor='#2c3e50',
                showbackground=True,
                color='white'
            ),
            zaxis=dict(
                title='Z (kpc)',
                backgroundcolor='black',
                gridcolor='#2c3e50',
                showbackground=True,
                color='white'
            ),
            bgcolor='black',
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.2)
            )
        ),
        paper_bgcolor='black',
        plot_bgcolor='black',
        font=dict(color='white'),
        showlegend=True,
        legend=dict(
            bgcolor='rgba(0,0,0,0.7)',
            bordercolor='#2c3e50',
            borderwidth=1,
            font=dict(color='white', size=10)
        ),
        height=700
    )

    return fig


def create_development_timeline(
    data: Dict[str, Any],
    title: str = "Civilization Development Over Time"
) -> go.Figure:
    """
    Create timeline plots showing civilization development.

    Args:
        data: Simulation data dictionary with 'civilizations' key
        title: Plot title

    Returns:
        Plotly Figure object with timeline subplots
    """
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Kardashev Level Evolution', 'Social Maturity Evolution'),
        vertical_spacing=0.12
    )

    # Extract civilizations with history
    civs_with_history = [c for c in data['civilizations'] if 'history' in c and c['history']]

    if not civs_with_history:
        # No history data, show current state only
        for civ in data['civilizations']:
            color = '#2ecc71' if civ['alive'] else '#e74c3c'

            fig.add_trace(
                go.Scatter(
                    x=[0, civ['age']],
                    y=[0.5, civ['kardashev_level']],
                    mode='lines',
                    line=dict(color=color, width=2),
                    name=f"Civ {civ['id']}",
                    showlegend=False
                ),
                row=1, col=1
            )

            fig.add_trace(
                go.Scatter(
                    x=[0, civ['age']],
                    y=[0, civ['social_maturity']],
                    mode='lines',
                    line=dict(color=color, width=2),
                    showlegend=False
                ),
                row=2, col=1
            )
    else:
        # Plot full histories
        for civ in civs_with_history:
            times = [h['time'] for h in civ['history']]
            kardashev = [h['kardashev'] for h in civ['history']]
            maturity = [h['maturity'] for h in civ['history']]

            color = '#2ecc71' if civ['alive'] else '#e74c3c'

            fig.add_trace(
                go.Scatter(
                    x=times,
                    y=kardashev,
                    mode='lines',
                    line=dict(color=color, width=2),
                    name=f"Civ {civ['id']}",
                    showlegend=False,
                    hovertemplate='Time: %{x:.0f} Myr<br>Kardashev: %{y:.2f}<extra></extra>'
                ),
                row=1, col=1
            )

            fig.add_trace(
                go.Scatter(
                    x=times,
                    y=maturity,
                    mode='lines',
                    line=dict(color=color, width=2),
                    showlegend=False,
                    hovertemplate='Time: %{x:.0f} Myr<br>Maturity: %{y:.2f}<extra></extra>'
                ),
                row=2, col=1
            )

    # Update layout
    fig.update_xaxes(title_text="Time (Myr)", row=2, col=1, color='white', gridcolor='#2c3e50')
    fig.update_xaxes(row=1, col=1, color='white', gridcolor='#2c3e50')
    fig.update_yaxes(title_text="Kardashev Level", row=1, col=1, color='white', gridcolor='#2c3e50')
    fig.update_yaxes(title_text="Social Maturity", row=2, col=1, color='white', gridcolor='#2c3e50')

    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18, 'color': 'white'}
        },
        paper_bgcolor='black',
        plot_bgcolor='black',
        font=dict(color='white'),
        height=600
    )

    return fig


def create_statistics_dashboard(
    data: Dict[str, Any],
    title: str = "Simulation Statistics"
) -> go.Figure:
    """
    Create multi-panel statistics dashboard.

    Args:
        data: Simulation data dictionary with 'civilizations' key
        title: Plot title

    Returns:
        Plotly Figure object with statistics subplots
    """
    civs = data['civilizations']

    # Calculate statistics
    total_civs = len(civs)
    alive_count = sum(1 for c in civs if c['alive'])
    dead_count = total_civs - alive_count

    # Death causes
    death_causes = {}
    for civ in civs:
        if not civ['alive']:
            cause = civ.get('cause_of_death') or 'unknown'
            death_causes[cause] = death_causes.get(cause, 0) + 1

    # Kardashev distribution
    kardashev_levels = [c['kardashev_level'] for c in civs]

    # Astrophysical events (try both possible keys)
    sn_count = len(data.get('supernova_events', data.get('supernovae', [])))
    grb_count = len(data.get('grb_events', data.get('grbs', [])))

    # Create subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            'Survival Status',
            'Death Causes',
            'Kardashev Distribution',
            'Astrophysical Events'
        ),
        specs=[
            [{'type': 'pie'}, {'type': 'bar'}],
            [{'type': 'histogram'}, {'type': 'bar'}]
        ],
        vertical_spacing=0.15,
        horizontal_spacing=0.12
    )

    # 1. Survival pie chart
    fig.add_trace(
        go.Pie(
            labels=['Alive', 'Dead'],
            values=[alive_count, dead_count],
            marker=dict(colors=['#2ecc71', '#e74c3c']),
            hole=0.3,
            textinfo='label+percent',
            textfont=dict(color='white', size=12)
        ),
        row=1, col=1
    )

    # 2. Death causes bar chart
    if death_causes:
        causes = list(death_causes.keys())
        counts = list(death_causes.values())

        fig.add_trace(
            go.Bar(
                x=causes,
                y=counts,
                marker=dict(color='#e74c3c'),
                text=counts,
                textposition='auto',
                textfont=dict(color='white')
            ),
            row=1, col=2
        )

    # 3. Kardashev distribution histogram
    fig.add_trace(
        go.Histogram(
            x=kardashev_levels,
            nbinsx=20,
            marker=dict(color='#3498db'),
            name='Kardashev'
        ),
        row=2, col=1
    )

    # 4. Astrophysical events bar chart
    fig.add_trace(
        go.Bar(
            x=['Supernovae', 'GRBs'],
            y=[sn_count, grb_count],
            marker=dict(color=['#e67e22', '#9b59b6']),
            text=[sn_count, grb_count],
            textposition='auto',
            textfont=dict(color='white')
        ),
        row=2, col=2
    )

    # Update layout
    fig.update_xaxes(title_text="Cause", row=1, col=2, color='white', gridcolor='#2c3e50')
    fig.update_yaxes(title_text="Count", row=1, col=2, color='white', gridcolor='#2c3e50')

    fig.update_xaxes(title_text="Kardashev Level", row=2, col=1, color='white', gridcolor='#2c3e50')
    fig.update_yaxes(title_text="Count", row=2, col=1, color='white', gridcolor='#2c3e50')

    fig.update_xaxes(title_text="Event Type", row=2, col=2, color='white', gridcolor='#2c3e50')
    fig.update_yaxes(title_text="Count", row=2, col=2, color='white', gridcolor='#2c3e50')

    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18, 'color': 'white'}
        },
        paper_bgcolor='black',
        plot_bgcolor='black',
        font=dict(color='white'),
        showlegend=False,
        height=700
    )

    return fig
