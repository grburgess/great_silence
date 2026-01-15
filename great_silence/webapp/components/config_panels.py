"""Advanced hierarchical configuration panels for all simulation parameters."""

from nicegui import ui
from typing import Any, Callable, Optional
from dataclasses import fields

from ..state import app_state


_global_on_change: Optional[Callable[[], None]] = None


def create_slider(
    label: str,
    param_name: str,
    config_obj: Any,
    min_val: float,
    max_val: float,
    step: float = None,
    unit: str = "",
    tooltip: str = "",
    format_fn: Callable[[float], str] = None,
) -> None:
    """Create a labeled slider for a config parameter."""
    current_val = getattr(config_obj, param_name)
    if step is None:
        step = (max_val - min_val) / 100

    with ui.row().classes("w-full items-center gap-2"):
        lbl = ui.label(label).classes("w-48 text-gray-300 text-sm")
        if tooltip:
            lbl.tooltip(tooltip)

        slider = ui.slider(min=min_val, max=max_val, step=step, value=current_val).classes(
            "flex-grow"
        )

        if format_fn:
            display_text = format_fn(current_val)
        else:
            display_text = f"{current_val:.3g} {unit}".strip()
        value_label = ui.label(display_text).classes("w-28 text-right text-cyan-400 font-mono text-sm")

        def on_change(e, pname=param_name, cfg=config_obj, vlbl=value_label, fmt=format_fn, u=unit, sl=slider):
            val = e.args if isinstance(e.args, (int, float)) else sl.value
            setattr(cfg, pname, val)
            if fmt:
                vlbl.text = fmt(val)
            else:
                vlbl.text = f"{val:.3g} {u}".strip()
            if _global_on_change:
                _global_on_change()

        slider.on("update:model-value", on_change)


def create_number_input(
    label: str,
    param_name: str,
    config_obj: Any,
    min_val: float = None,
    max_val: float = None,
    step: float = 1,
    unit: str = "",
    tooltip: str = "",
) -> None:
    """Create a labeled number input for a config parameter."""
    current_val = getattr(config_obj, param_name)

    with ui.row().classes("w-full items-center gap-2"):
        lbl = ui.label(label).classes("w-48 text-gray-300 text-sm")
        if tooltip:
            lbl.tooltip(tooltip)

        num_input = (
            ui.number(value=current_val, min=min_val, max=max_val, step=step)
            .classes("w-32")
            .props("dense outlined dark")
        )

        if unit:
            ui.label(unit).classes("text-gray-500 text-sm")

        def on_change(e, pname=param_name, cfg=config_obj, ni=num_input):
            val = e.args if isinstance(e.args, (int, float)) else ni.value
            if val is not None:
                setattr(cfg, pname, type(getattr(cfg, pname))(val))
                if _global_on_change:
                    _global_on_change()

        num_input.on("update:model-value", on_change)


def create_toggle(
    label: str,
    param_name: str,
    config_obj: Any,
    tooltip: str = "",
) -> None:
    """Create a labeled toggle for a boolean config parameter."""
    current_val = getattr(config_obj, param_name)

    with ui.row().classes("w-full items-center gap-2"):
        lbl = ui.label(label).classes("w-48 text-gray-300 text-sm")
        if tooltip:
            lbl.tooltip(tooltip)

        toggle = ui.switch(value=current_val).classes("text-cyan-400")

        def on_change(e, pname=param_name, cfg=config_obj, tg=toggle):
            val = e.args if isinstance(e.args, bool) else tg.value
            setattr(cfg, pname, val)
            if _global_on_change:
                _global_on_change()

        toggle.on("update:model-value", on_change)


def create_dropdown(
    label: str,
    param_name: str,
    config_obj: Any,
    options: list,
    tooltip: str = "",
) -> None:
    """Create a labeled dropdown for a config parameter."""
    current_val = getattr(config_obj, param_name)

    with ui.row().classes("w-full items-center gap-2"):
        lbl = ui.label(label).classes("w-48 text-gray-300 text-sm")
        if tooltip:
            lbl.tooltip(tooltip)

        select = ui.select(options, value=current_val).classes("w-40").props("dense outlined dark")

        def on_change(e, pname=param_name, cfg=config_obj, sel=select):
            val = e.args if e.args is not None else sel.value
            setattr(cfg, pname, val)
            if _global_on_change:
                _global_on_change()

        select.on("update:model-value", on_change)


class ConfigPanels:
    """Hierarchical configuration panels for all simulation parameters."""

    def __init__(self, on_change: Optional[Callable[[], None]] = None):
        global _global_on_change
        _global_on_change = on_change
        self._build()

    def _build(self) -> None:
        with ui.column().classes("w-full gap-2"):
            self._create_galaxy_panel()
            self._create_astrophysics_panel()
            self._create_emergence_panel()
            self._create_expansion_panel()
            self._create_self_destruction_panel()
            self._create_kardashev_panel()
            self._create_interciv_panel()
            self._create_simulation_panel()

    def _create_galaxy_panel(self) -> None:
        cfg = app_state.config.galaxy
        with ui.expansion("🌌 Galaxy Structure", icon="blur_circular").classes("w-full"):
            ui.label("Configure the galactic structure and stellar population").classes(
                "text-xs text-gray-500 mb-2"
            )

            with ui.expansion("Disk Dimensions", value=False).classes("w-full bg-gray-800/50"):
                create_slider("Disk Radius", "disk_radius_kpc", cfg, 5, 30, 1, "kpc",
                             "Outer radius of the galactic disk")
                create_slider("Disk Height", "disk_height_kpc", cfg, 0.1, 1.0, 0.05, "kpc",
                             "Scale height of the thin disk")
                create_slider("Scale Length", "scale_length_kpc", cfg, 1, 10, 0.5, "kpc",
                             "Exponential scale length for stellar density")

            with ui.expansion("Bulge Settings", value=False).classes("w-full bg-gray-800/50"):
                create_toggle("Include Bulge", "include_bulge", cfg,
                             "Include central bulge component")
                create_slider("Bulge Radius", "bulge_radius_kpc", cfg, 0.5, 3, 0.1, "kpc",
                             "Effective radius of the bulge")
                create_slider("Bulge Fraction", "bulge_fraction", cfg, 0.05, 0.4, 0.01, "",
                             "Fraction of stars in bulge (~20% for MW)")

            with ui.expansion("Gradients", value=False).classes("w-full bg-gray-800/50"):
                create_toggle("Use Age Gradient", "use_age_gradient", cfg,
                             "Radial age gradient (inner stars older)")
                create_slider("Central Age", "central_mean_age_gyr", cfg, 8, 13, 0.5, "Gyr",
                             "Mean stellar age in bulge/center")
                create_slider("Outer Age", "outer_mean_age_gyr", cfg, 1, 8, 0.5, "Gyr",
                             "Mean stellar age in outer disk")
                create_toggle("Use Metallicity Gradient", "use_metallicity_gradient", cfg,
                             "Radial metallicity gradient")
                create_slider("Central [Fe/H]", "central_metallicity_feh", cfg, -0.5, 0.5, 0.05, "dex",
                             "Metallicity in bulge (metal-rich)")
                create_slider("Gradient", "metallicity_gradient_dex_per_kpc", cfg, -0.15, 0, 0.01, "dex/kpc",
                             "Metallicity gradient slope")

            with ui.expansion("Dynamics", value=False).classes("w-full bg-gray-800/50"):
                create_slider("Rotation Velocity", "rotation_velocity_km_s", cfg, 150, 300, 10, "km/s",
                             "Circular velocity at solar radius")
                create_number_input("Spiral Arms", "spiral_arm_count", cfg, 0, 8, 1, "",
                                   "Number of spiral arms")
                create_slider("Spiral Strength", "spiral_arm_strength", cfg, 0, 0.5, 0.05, "",
                             "Amplitude of spiral perturbation")
                create_toggle("Enable Bar", "enable_bar", cfg,
                             "Include central bar structure")

            with ui.expansion("Habitable Zone", value=False).classes("w-full bg-gray-800/50"):
                create_slider("Min Habitable Mass", "habitable_mass_min_msun", cfg, 0.3, 0.8, 0.05, "M☉",
                             "Minimum stellar mass for habitable zone stability")
                create_slider("Max Habitable Mass", "habitable_mass_max_msun", cfg, 1.0, 2.0, 0.1, "M☉",
                             "Maximum stellar mass (main sequence lifetime)")
                create_slider("Max Stellar Age", "max_stellar_age_gyr", cfg, 10, 14, 0.5, "Gyr",
                             "Maximum stellar age / age of universe")

    def _create_astrophysics_panel(self) -> None:
        cfg = app_state.config.astrophysics
        with ui.expansion("💥 Astrophysics & Hazards", icon="flash_on").classes("w-full"):
            ui.label("Configure astrophysical processes and extinction hazards").classes(
                "text-xs text-gray-500 mb-2"
            )

            with ui.expansion("Star Formation", value=False).classes("w-full bg-gray-800/50"):
                create_slider("Current SFR", "current_sfr_msun_yr", cfg, 0.5, 5, 0.1, "M☉/yr",
                             "Current star formation rate")
                create_slider("SFR Peak Age", "sfr_peak_age_gyr", cfg, 5, 12, 0.5, "Gyr",
                             "Epoch of peak star formation")
                create_dropdown("IMF Type", "imf_type", cfg, ["kroupa", "salpeter", "chabrier"],
                               "Initial Mass Function")

            with ui.expansion("Supernovae", value=False).classes("w-full bg-gray-800/50"):
                create_slider("SN Rate", "sn_rate_per_century", cfg, 0.5, 5, 0.1, "/century",
                             "Supernova rate per century")
                create_slider("Lethal Range", "sn_lethal_range_pc", cfg, 5, 30, 1, "pc",
                             "Distance at which SNe are lethal")
                create_slider("Sterilization Range", "sn_sterilization_range_pc", cfg, 10, 100, 5, "pc",
                             "Distance causing partial sterilization")

            with ui.expansion("Gamma-Ray Bursts", value=False).classes("w-full bg-gray-800/50"):
                create_slider("GRB Rate", "grb_rate_per_century", cfg, 0.001, 0.1, 0.001, "/century",
                             "GRB rate per century")
                create_slider("Lethal Range", "grb_lethal_range_kpc", cfg, 1, 15, 0.5, "kpc",
                             "GRB lethal distance")
                create_slider("Beaming Angle", "grb_beaming_angle_deg", cfg, 2, 30, 1, "°",
                             "GRB jet opening angle")
                create_slider("GRB Fraction", "grb_fraction_of_sne", cfg, 0.001, 0.1, 0.001, "",
                             "Fraction of massive SNe producing GRBs")

            with ui.expansion("Neutron Star Mergers", value=False).classes("w-full bg-gray-800/50"):
                create_slider("Merger Rate", "ns_merger_rate_per_myr", cfg, 10, 200, 10, "/Myr",
                             "Galactic NS merger rate")
                create_slider("sGRB Lethal Range", "ns_sgrb_lethal_range_kpc", cfg, 0.5, 10, 0.5, "kpc",
                             "Short GRB lethal distance")
                create_slider("sGRB Beaming", "ns_sgrb_beaming_angle_deg", cfg, 1, 15, 1, "°",
                             "Short GRB beaming angle")
                create_slider("Kilonova Lethal", "ns_kilonova_lethal_range_pc", cfg, 10, 100, 5, "pc",
                             "Kilonova lethal distance")

    def _create_emergence_panel(self) -> None:
        cfg = app_state.config.civilization
        with ui.expansion("🧬 Civilization Emergence (Drake Equation)", icon="psychology").classes("w-full"):
            ui.label("Configure Drake equation factors for civilization emergence").classes(
                "text-xs text-gray-500 mb-2"
            )

            with ui.expansion("Drake Factors", value=True).classes("w-full bg-gray-800/50"):
                create_slider("Stars with Planets", "fraction_stars_with_planets", cfg, 0.1, 1.0, 0.05, "",
                             "Fraction of stars with planetary systems")
                create_slider("Habitable Planets", "avg_habitable_planets_per_system", cfg, 0.01, 1.0, 0.01, "",
                             "Average habitable planets per system")
                create_slider("Life Develops", "fraction_develop_life", cfg, 0.001, 1.0, 0.01, "",
                             "Fraction of habitable planets developing life",
                             format_fn=lambda x: f"{x:.1%}")
                create_slider("Intelligence Develops", "fraction_develop_intelligence", cfg, 0.001, 0.5, 0.001, "",
                             "Fraction of life-bearing planets developing intelligence",
                             format_fn=lambda x: f"{x:.2%}")
                create_slider("Technology Develops", "fraction_develop_technology", cfg, 0.01, 1.0, 0.01, "",
                             "Fraction of intelligent species developing technology",
                             format_fn=lambda x: f"{x:.1%}")

            with ui.expansion("Lifetime", value=False).classes("w-full bg-gray-800/50"):
                create_slider("Mean Lifetime", "mean_civilization_lifetime_myr", cfg, 0.01, 100, 0.1, "Myr",
                             "Mean civilization lifetime")
                create_slider("Lifetime Stddev", "lifetime_stddev_myr", cfg, 0.01, 50, 0.1, "Myr",
                             "Standard deviation of lifetime")
                create_slider("Min Stellar Age", "min_stellar_age_for_life_gyr", cfg, 0.1, 5, 0.1, "Gyr",
                             "Minimum stellar age for complex life")

    def _create_expansion_panel(self) -> None:
        cfg = app_state.config.civilization
        with ui.expansion("🚀 Expansion & Probes", icon="rocket_launch").classes("w-full"):
            ui.label("Configure self-replicating probe expansion parameters").classes(
                "text-xs text-gray-500 mb-2"
            )

            with ui.expansion("Expansion Settings", value=True).classes("w-full bg-gray-800/50"):
                create_toggle("Expansion Enabled", "expansion_enabled", cfg,
                             "Enable probe-based expansion")
                create_slider("Min K for Expansion", "min_kardashev_for_expansion", cfg, 0.5, 1.5, 0.05, "",
                             "Minimum Kardashev level for interstellar probes")
                create_number_input("Max Colonies", "max_colonies_per_civilization", cfg, 10, 10000, 100, "",
                                   "Maximum colonies per civilization")

            with ui.expansion("Metallicity Thresholds", value=False).classes("w-full bg-gray-800/50"):
                ui.label("Probes need metal-rich systems for replication").classes("text-xs text-gray-500 mb-2")
                create_slider("K=0.85-0.95 Threshold", "metallicity_threshold_k085", cfg, -1.0, 0.5, 0.05, "[Fe/H]",
                             "Metallicity threshold for early-tech probes")
                create_slider("K=0.95-1.20 Threshold", "metallicity_threshold_k095", cfg, -1.0, 0.5, 0.05, "[Fe/H]",
                             "Metallicity threshold for mid-tech probes")
                create_slider("K>1.20 Threshold", "metallicity_threshold_k120", cfg, -2.0, 0.0, 0.05, "[Fe/H]",
                             "Metallicity threshold for advanced probes")

            with ui.expansion("Probe Sensors", value=False).classes("w-full bg-gray-800/50"):
                create_slider("Sensor Range", "probe_sensor_range_pc", cfg, 1, 50, 1, "pc",
                             "Probe sensor range for course corrections")
                create_toggle("Mid-Flight Retargeting", "enable_mid_flight_retargeting", cfg,
                             "Allow probes to change targets (EXPERIMENTAL)")

    def _create_self_destruction_panel(self) -> None:
        cfg = app_state.config.civilization
        with ui.expansion("☠️ Self-Destruction Model", icon="warning").classes("w-full"):
            ui.label("Configure civilization self-destruction risks").classes(
                "text-xs text-gray-500 mb-2"
            )

            with ui.expansion("Model Type", value=True).classes("w-full bg-gray-800/50"):
                create_dropdown("Model", "self_destruction_model_type", cfg,
                               ["kardashev_dependent", "flat"],
                               "Self-destruction probability model")
                create_slider("Flat Rate", "self_destruction_probability_per_myr", cfg, 0.001, 1.0, 0.01, "/Myr",
                             "Flat self-destruction rate (if flat model)")
                create_slider("Baseline Rate", "baseline_self_destruction_rate", cfg, 0.001, 0.1, 0.001, "/Myr",
                             "Baseline hazard at K=0")
                create_slider("Risk Scaling", "baseline_risk_scaling", cfg, 0.01, 0.2, 0.01, "",
                             "Linear risk increase with K")

            with ui.expansion("Crisis Amplitudes", value=False).classes("w-full bg-gray-800/50"):
                ui.label("Peak hazard rates at technological crises").classes("text-xs text-gray-500 mb-2")
                create_slider("Nuclear Age (K~0.72)", "crisis_nuclear_age_amplitude", cfg, 0, 0.5, 0.01, "",
                             "Crisis at nuclear technology")
                create_slider("Planetary Unification (K~0.85)", "crisis_planetary_unification_amplitude", cfg, 0, 0.5, 0.01, "",
                             "Crisis at global unification")
                create_slider("AI Transition (K~1.05)", "crisis_ai_transition_amplitude", cfg, 0, 0.5, 0.01, "",
                             "Crisis at AI singularity")
                create_slider("Interplanetary (K~1.25)", "crisis_interplanetary_amplitude", cfg, 0, 0.5, 0.01, "",
                             "Crisis at interplanetary expansion")
                create_slider("Stellar Engineering (K~1.80)", "crisis_stellar_engineering_amplitude", cfg, 0, 0.3, 0.01, "",
                             "Crisis at stellar engineering")
                create_slider("Relativistic Weapons (K~2.50)", "crisis_relativistic_weapons_amplitude", cfg, 0, 0.2, 0.01, "",
                             "Crisis at relativistic weapons")

            with ui.expansion("Enable/Disable Crises", value=False).classes("w-full bg-gray-800/50"):
                create_toggle("Nuclear Crisis", "enable_nuclear_crisis", cfg, "Enable nuclear age crisis")
                create_toggle("Unification Crisis", "enable_planetary_unification_crisis", cfg, "Enable unification crisis")
                create_toggle("AI Crisis", "enable_ai_crisis", cfg, "Enable AI transition crisis")
                create_toggle("Interplanetary Crisis", "enable_interplanetary_crisis", cfg, "Enable interplanetary crisis")
                create_toggle("Stellar Crisis", "enable_stellar_crisis", cfg, "Enable stellar engineering crisis")
                create_toggle("Relativistic Crisis", "enable_relativistic_weapons_crisis", cfg, "Enable relativistic weapons crisis")

    def _create_kardashev_panel(self) -> None:
        cfg = app_state.config.civilization
        with ui.expansion("⚡ Kardashev Progression", icon="trending_up").classes("w-full"):
            ui.label("Configure technological advancement rates").classes(
                "text-xs text-gray-500 mb-2"
            )

            with ui.expansion("Initial State", value=True).classes("w-full bg-gray-800/50"):
                create_slider("Initial K Mean", "initial_kardashev_scale_mean", cfg, 0.5, 1.0, 0.05, "",
                             "Mean starting Kardashev level (~0.7 for Earth)")
                create_slider("Initial K Stddev", "initial_kardashev_scale_stddev", cfg, 0.01, 0.3, 0.01, "",
                             "Variation in starting technology")
                create_slider("Max K Scale", "kardashev_max_scale", cfg, 2.0, 4.0, 0.1, "",
                             "Maximum technological level (Type III = 3.0)")

            with ui.expansion("Advancement Rates", value=False).classes("w-full bg-gray-800/50"):
                create_slider("Advancement Rate", "kardashev_advancement_rate_mean", cfg, 0.001, 0.1, 0.001, "/Myr",
                             "Mean K advancement rate per Myr")
                create_slider("Rate Stddev", "kardashev_advancement_rate_stddev", cfg, 0.001, 0.05, 0.001, "/Myr",
                             "Variation in advancement rate")
                create_slider("Stagnation Prob", "kardashev_stagnation_probability_per_myr", cfg, 0, 0.2, 0.01, "/Myr",
                             "Chance of tech stagnation")
                create_slider("Breakthrough Prob", "kardashev_breakthrough_probability_per_myr", cfg, 0, 0.1, 0.005, "/Myr",
                             "Chance of rapid advancement")
                create_slider("Breakthrough Mult", "kardashev_breakthrough_multiplier", cfg, 1.5, 10, 0.5, "×",
                             "Speed multiplier during breakthrough")

    def _create_interciv_panel(self) -> None:
        cfg = app_state.config.civilization
        with ui.expansion("🤝 Inter-Civilization Dynamics", icon="groups").classes("w-full"):
            ui.label("Configure encounter, war, and diplomacy mechanics").classes(
                "text-xs text-gray-500 mb-2"
            )

            with ui.expansion("Colony Resilience", value=False).classes("w-full bg-gray-800/50"):
                create_slider("Maturation Time", "colony_maturation_time_myr", cfg, 0.01, 1.0, 0.01, "Myr",
                             "Time before colonies contribute to resilience")
                create_slider("Lifetime Bonus", "colonization_lifetime_bonus_myr", cfg, 0.1, 5, 0.1, "Myr",
                             "Logarithmic lifetime bonus from colonies")
                create_slider("Home Fragility Period", "home_world_fragility_period_myr", cfg, 0.1, 2, 0.1, "Myr",
                             "Duration of fragility after home world loss")
                create_slider("Fragility Factor", "home_world_fragility_factor", cfg, 0.1, 1.0, 0.1, "",
                             "Lifetime multiplier during fragility")

            with ui.expansion("Colonial Wars", value=False).classes("w-full bg-gray-800/50"):
                create_number_input("Colony Threshold", "colonial_war_colony_threshold", cfg, 2, 100, 1, "",
                                   "Minimum colonies for colonial war risk")
                create_slider("K Threshold", "colonial_war_kardashev_threshold", cfg, 1.0, 2.5, 0.1, "",
                             "Minimum K-scale for colonial war")
                create_slider("War Amplitude", "colonial_war_amplitude", cfg, 0, 0.2, 0.01, "/Myr",
                             "Colonial war hazard rate")

            with ui.expansion("Encounters", value=False).classes("w-full bg-gray-800/50"):
                create_slider("Detection Range", "first_contact_detection_range_pc", cfg, 10, 500, 10, "pc",
                             "First contact detection range")
                create_slider("Scan Interval", "encounter_scan_interval_myr", cfg, 1, 500, 10, "Myr",
                             "Interval between encounter scans")
                create_slider("Sensor Range", "sensor_range_pc", cfg, 10, 200, 10, "pc",
                             "Civilization sensor range")

            with ui.expansion("War Mechanics", value=False).classes("w-full bg-gray-800/50"):
                create_dropdown("Outcome Model", "war_outcome_model", cfg, ["winner_takes_territory"],
                               "War resolution model")
                create_slider("Max War Duration", "war_duration_max_myr", cfg, 1, 50, 1, "Myr",
                             "Maximum war duration")
                create_slider("Stalemate Prob", "war_stalemate_probability", cfg, 0, 0.5, 0.05, "",
                             "Probability of stalemate")
                create_slider("Tech Advantage", "tech_advantage_sensitivity", cfg, 0.1, 1.0, 0.1, "",
                             "Sensitivity to tech advantage")
                create_slider("Fleet Velocity", "fleet_velocity_multiplier", cfg, 0.001, 0.1, 0.005, "c",
                             "Fleet velocity as fraction of c")

            with ui.expansion("Reputation & Alliances", value=False).classes("w-full bg-gray-800/50"):
                create_toggle("Reputation Enabled", "reputation_enabled", cfg, "Enable reputation system")
                create_slider("Reputation Weight", "reputation_weight_in_war_decision", cfg, 0, 1, 0.1, "",
                             "Weight of reputation in war decisions")
                create_slider("Reputation Decay", "reputation_decay_rate", cfg, 0, 0.1, 0.01, "/Myr",
                             "Reputation decay rate")
                create_toggle("Alliances Enabled", "alliance_formation_enabled", cfg, "Enable alliance formation")
                create_toggle("Light Cone Constraint", "alliance_light_cone_constraint", cfg,
                             "Enforce light cone for alliances")

    def _create_simulation_panel(self) -> None:
        cfg = app_state.config.simulation
        with ui.expansion("⚙️ Simulation Performance", icon="speed").classes("w-full"):
            ui.label("Configure simulation execution parameters").classes(
                "text-xs text-gray-500 mb-2"
            )

            with ui.expansion("Time Stepping", value=False).classes("w-full bg-gray-800/50"):
                create_toggle("Adaptive Timestep", "adaptive_timestepping", cfg,
                             "Enable adaptive time stepping based on events")
                create_slider("Base Timestep", "time_step_myr", cfg, 0.1, 10, 0.1, "Myr",
                             "Base timestep for fixed mode")
                create_slider("Min Timestep", "min_timestep_myr", cfg, 0.001, 0.1, 0.001, "Myr",
                             "Minimum adaptive timestep")
                create_slider("Max Timestep", "max_timestep_myr", cfg, 1, 50, 1, "Myr",
                             "Maximum adaptive timestep")

            with ui.expansion("Performance", value=False).classes("w-full bg-gray-800/50"):
                create_toggle("Use Numba", "use_numba", cfg, "Enable Numba JIT compilation")
                create_toggle("Parallel Processing", "parallel_processing", cfg, "Enable parallelization")
                create_number_input("Chunk Size", "chunk_size", cfg, 1000, 100000, 1000, "",
                                   "Processing chunk size")

            with ui.expansion("Physics Options", value=False).classes("w-full bg-gray-800/50"):
                create_toggle("Stellar Motion", "enable_stellar_motion", cfg,
                             "Enable gravitational evolution (EXPERIMENTAL)")
                create_toggle("Star Formation", "enable_star_formation", cfg,
                             "Enable continuous star formation")

            with ui.expansion("Output", value=False).classes("w-full bg-gray-800/50"):
                create_toggle("Save Snapshots", "save_snapshots", cfg, "Save periodic snapshots")
                create_slider("Snapshot Interval", "snapshot_interval_myr", cfg, 10, 1000, 10, "Myr",
                             "Interval between snapshots")
