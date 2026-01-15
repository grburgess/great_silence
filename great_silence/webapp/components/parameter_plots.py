"""Interactive parameter visualization plots for the webapp sidebar."""

from nicegui import ui
import plotly.graph_objects as go
import numpy as np
from typing import Callable, Optional

from ..state import app_state


DARK_THEME = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='#1a1a2e',
    font=dict(color='#e0e0e0', size=11),
    margin=dict(l=50, r=20, t=40, b=40),
    xaxis=dict(
        gridcolor='#333355',
        zerolinecolor='#444466',
    ),
    yaxis=dict(
        gridcolor='#333355',
        zerolinecolor='#444466',
    ),
)

COLORS = {
    'cyan': '#00d4ff',
    'purple': '#a855f7',
    'orange': '#ff6b35',
    'green': '#22c55e',
    'red': '#ef4444',
    'yellow': '#eab308',
    'pink': '#ec4899',
}

PLOT_OPTIONS = [
    ('kardashev', 'Kardashev Crisis'),
    ('drake', 'Drake Funnel'),
    ('imf', 'IMF Distribution'),
    ('hazards', 'Hazard Ranges'),
    ('habitable', 'Habitable Mass'),
]


class ParameterPlots:
    """Component for displaying interactive parameter visualization plots."""

    def __init__(self, on_ready: Optional[Callable] = None):
        self._plot1_type = 'kardashev'
        self._plot2_type = 'drake'
        self._plot1_container = None
        self._plot2_container = None
        self._on_ready = on_ready
        self._build()

    def _build(self) -> None:
        with ui.card().classes('w-full h-full'):
            ui.label('📊 Parameter Visualization').classes(
                'text-lg font-semibold text-gray-300 mb-2'
            )

            with ui.row().classes('w-full gap-2 mb-2'):
                ui.label('Plot 1:').classes('text-gray-400 text-sm self-center')
                self._select1 = ui.select(
                    options={k: v for k, v in PLOT_OPTIONS},
                    value=self._plot1_type,
                    on_change=lambda e: self._on_plot_select(1, e.args[0]),
                ).classes('w-40').props('dense dark outlined')

                ui.label('Plot 2:').classes('text-gray-400 text-sm self-center ml-4')
                self._select2 = ui.select(
                    options={k: v for k, v in PLOT_OPTIONS},
                    value=self._plot2_type,
                    on_change=lambda e: self._on_plot_select(2, e.args[0]),
                ).classes('w-40').props('dense dark outlined')

            with ui.column().classes('w-full gap-4'):
                self._plot1_container = ui.column().classes('w-full')
                self._plot2_container = ui.column().classes('w-full')

            self.refresh()

    def _on_plot_select(self, plot_num: int, value: str) -> None:
        if plot_num == 1:
            self._plot1_type = value
        else:
            self._plot2_type = value
        self.refresh()

    def refresh(self) -> None:
        """Refresh both plots with current config values."""
        self._plot1_container.clear()
        with self._plot1_container:
            fig1 = self._create_plot(self._plot1_type)
            ui.plotly(fig1).classes('w-full h-72')

        self._plot2_container.clear()
        with self._plot2_container:
            fig2 = self._create_plot(self._plot2_type)
            ui.plotly(fig2).classes('w-full h-72')

    def _create_plot(self, plot_type: str) -> go.Figure:
        if plot_type == 'kardashev':
            return self._create_kardashev_plot()
        elif plot_type == 'drake':
            return self._create_drake_plot()
        elif plot_type == 'imf':
            return self._create_imf_plot()
        elif plot_type == 'hazards':
            return self._create_hazards_plot()
        elif plot_type == 'habitable':
            return self._create_habitable_plot()
        else:
            return go.Figure()

    def _create_kardashev_plot(self) -> go.Figure:
        """Create Kardashev crisis curve showing self-destruction hazard rate."""
        config = app_state.config.civilization

        k_values = np.linspace(0, 3, 300)

        baseline_rate = config.baseline_self_destruction_rate
        baseline_scaling = config.baseline_risk_scaling
        lambda_base = baseline_rate * (1 + baseline_scaling * k_values)

        crisis_peaks = [
            ('Nuclear Age', 0.72, 0.05, config.crisis_nuclear_age_amplitude, config.enable_nuclear_crisis, COLORS['orange']),
            ('Planetary Unification', 0.85, 0.05, config.crisis_planetary_unification_amplitude, config.enable_planetary_unification_crisis, COLORS['yellow']),
            ('AI Transition', 1.05, 0.08, config.crisis_ai_transition_amplitude, config.enable_ai_crisis, COLORS['red']),
            ('Interplanetary', 1.25, 0.10, config.crisis_interplanetary_amplitude, config.enable_interplanetary_crisis, COLORS['purple']),
            ('Stellar Engineering', 1.80, 0.15, config.crisis_stellar_engineering_amplitude, config.enable_stellar_crisis, COLORS['cyan']),
            ('Relativistic Weapons', 2.50, 0.20, config.crisis_relativistic_weapons_amplitude, config.enable_relativistic_weapons_crisis, COLORS['pink']),
        ]

        total_hazard = lambda_base.copy()

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=k_values,
            y=lambda_base,
            mode='lines',
            name='Baseline',
            line=dict(color='#666688', dash='dash', width=1),
            hovertemplate='K=%.2f<br>Baseline: %.4f/Myr<extra></extra>',
        ))

        for name, k_center, width, amplitude, enabled, color in crisis_peaks:
            if enabled:
                gaussian = amplitude * np.exp(-0.5 * ((k_values - k_center) / width) ** 2)
                total_hazard += gaussian

                fig.add_trace(go.Scatter(
                    x=k_values,
                    y=gaussian + lambda_base,
                    mode='lines',
                    name=name,
                    line=dict(color=color, width=1),
                    opacity=0.5,
                    hovertemplate=f'{name}<br>K=%.2f<br>Peak: {amplitude:.2f}/Myr<extra></extra>',
                ))

        fig.add_trace(go.Scatter(
            x=k_values,
            y=total_hazard,
            mode='lines',
            name='Total Hazard',
            line=dict(color=COLORS['cyan'], width=2),
            hovertemplate='K=%.2f<br>Total: %.4f/Myr<extra></extra>',
        ))

        fig.add_vline(x=0.7, line_dash='dot', line_color='#888888', annotation_text='Earth', annotation_position='top')

        fig.update_layout(
            title='Self-Destruction Hazard Rate',
            xaxis_title='Kardashev Level',
            yaxis_title='Hazard Rate (per Myr)',
            showlegend=True,
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1,
                font=dict(size=9),
            ),
            height=280,
            **DARK_THEME,
        )

        return fig

    def _create_drake_plot(self) -> go.Figure:
        """Create Drake equation funnel showing emergence probability."""
        config = app_state.config.civilization

        stages = [
            ('Stars with Planets', config.fraction_stars_with_planets),
            ('Habitable Planets', config.avg_habitable_planets_per_system),
            ('Develop Life', config.fraction_develop_life),
            ('Intelligence', config.fraction_develop_intelligence),
            ('Technology', config.fraction_develop_technology),
        ]

        labels = [s[0] for s in stages]
        values = []
        cumulative = 1.0
        for _, frac in stages:
            cumulative *= frac
            values.append(cumulative)

        fig = go.Figure()

        fig.add_trace(go.Funnel(
            y=labels,
            x=[v * 100 for v in values],
            textinfo='value+percent initial',
            texttemplate='%{x:.4f}%',
            marker=dict(
                color=[COLORS['cyan'], COLORS['purple'], COLORS['green'], COLORS['orange'], COLORS['red']],
            ),
            connector=dict(line=dict(color='#444466', width=1)),
            hovertemplate='%{y}<br>Cumulative: %{x:.6f}%<extra></extra>',
        ))

        final_prob = values[-1] if values else 0
        fig.add_annotation(
            text=f'Final: {final_prob:.2e} per star',
            xref='paper', yref='paper',
            x=0.95, y=0.05,
            showarrow=False,
            font=dict(color=COLORS['cyan'], size=12),
            bgcolor='rgba(0,0,0,0.5)',
        )

        fig.update_layout(
            title='Drake Equation Emergence Probability',
            height=280,
            **DARK_THEME,
        )

        return fig

    def _create_imf_plot(self) -> go.Figure:
        """Create IMF (Initial Mass Function) distribution plot."""
        config = app_state.config.astrophysics
        imf_type = config.imf_type

        masses = np.logspace(-1, 2, 200)

        if imf_type == 'kroupa':
            alpha1, alpha2 = -1.3, -2.3
            m_break = 0.5
            imf = np.where(
                masses < m_break,
                masses ** alpha1,
                (m_break ** (alpha1 - alpha2)) * masses ** alpha2
            )
            title_suffix = 'Kroupa (α=-1.3/-2.3)'
        elif imf_type == 'salpeter':
            imf = masses ** -2.35
            title_suffix = 'Salpeter (α=-2.35)'
        elif imf_type == 'chabrier':
            mc = 0.08
            sigma = 0.69
            imf = np.where(
                masses < 1.0,
                np.exp(-((np.log10(masses) - np.log10(mc)) ** 2) / (2 * sigma ** 2)),
                masses ** -2.3
            )
            title_suffix = 'Chabrier (lognormal+power)'
        else:
            imf = masses ** -2.35
            title_suffix = imf_type

        imf = imf / np.max(imf)

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=masses,
            y=imf,
            mode='lines',
            name='IMF',
            line=dict(color=COLORS['cyan'], width=2),
            fill='tozeroy',
            fillcolor='rgba(0, 212, 255, 0.2)',
            hovertemplate='Mass: %.2f M☉<br>Relative N: %.4f<extra></extra>',
        ))

        fig.add_vline(x=8.0, line_dash='dash', line_color=COLORS['orange'], 
                     annotation_text='SN progenitor', annotation_position='top right')
        fig.add_vline(x=1.0, line_dash='dot', line_color='#888888',
                     annotation_text='Sun', annotation_position='bottom right')

        fig.update_layout(
            title=f'Initial Mass Function ({title_suffix})',
            xaxis_title='Stellar Mass (M☉)',
            yaxis_title='Relative Number',
            xaxis_type='log',
            yaxis_type='log',
            xaxis=dict(range=[-1, 2], **DARK_THEME['xaxis']),
            yaxis=dict(range=[-4, 0.1], **DARK_THEME['yaxis']),
            height=280,
            showlegend=False,
            **{k: v for k, v in DARK_THEME.items() if k not in ['xaxis', 'yaxis']},
        )

        return fig

    def _create_hazards_plot(self) -> go.Figure:
        """Create hazard lethal ranges comparison plot."""
        config = app_state.config.astrophysics

        categories = ['Supernova', 'GRB', 'NS Merger (sGRB)', 'NS Merger (KN)']

        lethal = [
            config.sn_lethal_range_pc,
            config.grb_lethal_range_kpc * 1000,
            config.ns_sgrb_lethal_range_kpc * 1000,
            config.ns_kilonova_lethal_range_pc,
        ]

        sterilization = [
            config.sn_sterilization_range_pc,
            config.grb_lethal_range_kpc * 1000 * 1.5,
            config.ns_sgrb_lethal_range_kpc * 1000 * 1.5,
            config.ns_kilonova_sterilization_range_pc,
        ]

        fig = go.Figure()

        fig.add_trace(go.Bar(
            name='Lethal Range',
            x=categories,
            y=lethal,
            marker_color=COLORS['red'],
            hovertemplate='%{x}<br>Lethal: %{y:.0f} pc<extra></extra>',
        ))

        fig.add_trace(go.Bar(
            name='Sterilization',
            x=categories,
            y=sterilization,
            marker_color=COLORS['orange'],
            opacity=0.7,
            hovertemplate='%{x}<br>Sterilization: %{y:.0f} pc<extra></extra>',
        ))

        fig.update_layout(
            title='Astrophysical Hazard Ranges',
            yaxis_title='Range (parsecs)',
            yaxis_type='log',
            barmode='group',
            height=280,
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1,
            ),
            **DARK_THEME,
        )

        return fig

    def _create_habitable_plot(self) -> go.Figure:
        """Create IMF plot with habitable mass range overlay."""
        config_astro = app_state.config.astrophysics
        config_galaxy = app_state.config.galaxy

        masses = np.logspace(-1, 2, 200)

        imf_type = config_astro.imf_type
        if imf_type == 'kroupa':
            alpha1, alpha2 = -1.3, -2.3
            m_break = 0.5
            imf = np.where(
                masses < m_break,
                masses ** alpha1,
                (m_break ** (alpha1 - alpha2)) * masses ** alpha2
            )
        elif imf_type == 'salpeter':
            imf = masses ** -2.35
        else:
            mc = 0.08
            sigma = 0.69
            imf = np.where(
                masses < 1.0,
                np.exp(-((np.log10(masses) - np.log10(mc)) ** 2) / (2 * sigma ** 2)),
                masses ** -2.3
            )

        imf = imf / np.max(imf)

        hab_min = config_galaxy.habitable_mass_min_msun
        hab_max = config_galaxy.habitable_mass_max_msun

        fig = go.Figure()

        fig.add_vrect(
            x0=hab_min, x1=hab_max,
            fillcolor='rgba(34, 197, 94, 0.3)',
            layer='below',
            line_width=0,
            annotation_text='Habitable Zone',
            annotation_position='top',
        )

        fig.add_trace(go.Scatter(
            x=masses,
            y=imf,
            mode='lines',
            name='IMF',
            line=dict(color=COLORS['cyan'], width=2),
            hovertemplate='Mass: %.2f M☉<br>Relative N: %.4f<extra></extra>',
        ))

        hab_mask = (masses >= hab_min) & (masses <= hab_max)
        hab_masses = masses[hab_mask]
        hab_imf = imf[hab_mask]

        fig.add_trace(go.Scatter(
            x=hab_masses,
            y=hab_imf,
            mode='lines',
            name='Habitable Stars',
            fill='tozeroy',
            fillcolor='rgba(34, 197, 94, 0.4)',
            line=dict(color=COLORS['green'], width=2),
            hovertemplate='Mass: %.2f M☉<br>Habitable!<extra></extra>',
        ))

        total_area = np.trapz(imf, masses)
        hab_area = np.trapz(hab_imf, hab_masses) if len(hab_masses) > 0 else 0
        hab_fraction = hab_area / total_area if total_area > 0 else 0

        fig.add_annotation(
            text=f'Habitable: {hab_fraction*100:.1f}% of stars',
            xref='paper', yref='paper',
            x=0.95, y=0.95,
            showarrow=False,
            font=dict(color=COLORS['green'], size=12),
            bgcolor='rgba(0,0,0,0.5)',
        )

        fig.add_vline(x=hab_min, line_dash='dash', line_color=COLORS['green'])
        fig.add_vline(x=hab_max, line_dash='dash', line_color=COLORS['green'])

        fig.update_layout(
            title=f'Habitable Stellar Mass Range ({hab_min}-{hab_max} M☉)',
            xaxis_title='Stellar Mass (M☉)',
            yaxis_title='Relative Number',
            xaxis_type='log',
            yaxis_type='log',
            xaxis=dict(range=[-1, 2], **DARK_THEME['xaxis']),
            yaxis=dict(range=[-4, 0.1], **DARK_THEME['yaxis']),
            height=280,
            showlegend=False,
            **{k: v for k, v in DARK_THEME.items() if k not in ['xaxis', 'yaxis']},
        )

        return fig
