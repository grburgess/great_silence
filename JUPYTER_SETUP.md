# Jupyter Lab Setup for GalaticBot

## ⚠️ Important: Dual Environment Architecture

**This project uses a split setup:**
- **Jupyter Lab runs in:** `base` conda environment
- **Code executes in:** `galaticbot` kernel environment

**Extensions (ipywidgets, plotly) must be installed in base conda environment.**
See `JUPYTER_ARCHITECTURE.md` for full details.

## Kernel Installation (DONE ✓)

The GalaticBot kernel has been registered with Jupyter. You should now see **"Python (galaticbot)"** as an available kernel when you:
1. Open Jupyter Lab
2. Create a new notebook or open an existing one
3. Click on the kernel name in the top right
4. Select "Python (galaticbot)"

## Quick Start

### 1. Launch Jupyter Lab

From **any directory**:
```bash
jupyter lab
```

**OR** from the project directory:
```bash
cd /Users/jburgess/coding/projects/galaticbot
jupyter lab
```

### 2. Open a Notebook

Navigate to `notebooks/` and open:
- `01_quickstart_production_workflow.ipynb`
- `02_interactive_exploration.ipynb`
- `03_animation_generation.ipynb`

### 3. Select the GalaticBot Kernel

In the notebook:
1. Click the kernel name in the top right (might say "No Kernel" or "Python 3")
2. Select **"Python (galaticbot)"** from the dropdown
3. Wait for kernel to start (usually 2-3 seconds)

### 4. Run the Notebook

- **Run all cells:** Shift + Enter through each cell
- **Run all:** Menu → Run → Run All Cells
- **Restart kernel:** Menu → Kernel → Restart Kernel

## Force Reload Notebooks (If Changes Don't Appear)

If you've updated notebooks but don't see changes in Jupyter Lab:

**1. Close and reload the notebook file:**
   - File → Close Tab
   - Re-open the notebook from file browser

**2. If still not working, hard refresh the browser:**
   - **Chrome/Edge:** Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
   - **Firefox:** Cmd+Shift+R (Mac) or Ctrl+F5 (Windows)
   - **Safari:** Cmd+Option+R

**3. Clear Jupyter checkpoints:**
```bash
rm -rf notebooks/.ipynb_checkpoints/
```
Then refresh browser.

**4. Nuclear option - restart Jupyter Lab:**
   - Stop Jupyter Lab (Ctrl+C in terminal)
   - Restart: `jupyter lab`

## Troubleshooting

### Kernel doesn't appear in list

Re-register the kernel:
```bash
~/.local/bin/micromamba run -n galaticbot python -m ipykernel install --user --name galaticbot --display-name "Python (galaticbot)"
```

### "ModuleNotFoundError: No module named 'great_silence'"

The library isn't installed in the kernel's environment. Install it:
```bash
~/.local/bin/micromamba run -n galaticbot pip install -e .
```

### Kernel keeps dying/restarting

Check memory usage (simulations can be memory-intensive):
- Reduce `num_stars` slider to 50,000 or less
- Use shorter simulation duration (1-5 Gyr)
- Close other applications

### Widget showing as "VBox(children=..." instead of rendering

This means ipywidgets is not properly rendering. The widget object is being displayed as text instead of an interactive UI.

**CRITICAL: Extensions must be in BASE conda environment (where Jupyter Lab runs)**

**1. Check if extension is installed in base:**
```bash
# Run from base conda environment (where jupyter lab runs)
jupyter labextension list
```

Look for `@jupyter-widgets/jupyterlab-manager` - it should show as "enabled" and "OK".

**2. If missing, install in BASE:**
```bash
# Activate base conda environment first
conda activate base

# Install ipywidgets (includes extension)
conda install -c conda-forge ipywidgets

# Rebuild JupyterLab
jupyter lab build
```

**3. Ensure package is also in KERNEL:**
```bash
# The Python package must be in galaticbot kernel
~/.local/bin/micromamba run -n galaticbot pip install ipywidgets
```

**3. Restart Jupyter Lab completely:**
- Stop server (Ctrl+C in terminal)
- Start fresh: `jupyter lab`
- Hard refresh browser: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)

**4. Update ipywidgets:**
```bash
~/.local/bin/micromamba run -n galaticbot pip install --upgrade ipywidgets
```

**5. Check kernel is correct:**
Make sure the notebook is using the "Python (galaticbot)" kernel (see top right of notebook).

### Plotly plots not showing

Plotly interactive plots require the JupyterLab plotly extension in BASE.

**CRITICAL: Plotly extension must be in BASE conda environment**

**1. Check if installed in base:**
```bash
# Run from base conda environment
jupyter labextension list | grep plotly
```

Should show: `jupyterlab-plotly v6.0.1 enabled OK`

**2. If missing, install in BASE:**
```bash
# Activate base conda environment
conda activate base

# Install plotly (extension comes with it)
conda install -c plotly plotly

# Rebuild JupyterLab
jupyter lab build
```

**3. Ensure package is also in KERNEL:**
```bash
# The Python package must be in galaticbot kernel
~/.local/bin/micromamba run -n galaticbot pip install plotly
```

**4. Configure renderer in notebook:**
The `configure_notebook_display()` function automatically sets plotly to use 'jupyterlab' renderer. If plots still don't show, manually set it:

```python
import plotly.io as pio
pio.renderers.default = 'jupyterlab'
```

**5. After installation:**
1. Restart Jupyter Lab (Ctrl+C, then `jupyter lab`)
2. Hard refresh browser (Cmd+Shift+R)
3. Rerun the notebook cells

### Widget extension not enabled

Enable widget extension (if not already done):
```bash
~/.local/bin/micromamba run -n galaticbot jupyter labextension list
```

If `@jupyter-widgets/jupyterlab-manager` is not listed:
```bash
~/.local/bin/micromamba run -n galaticbot pip install ipywidgets
~/.local/bin/micromamba run -n galaticbot jupyter labextension install @jupyter-widgets/jupyterlab-manager
```

### Running Jupyter from different environment

If you accidentally launch Jupyter from a different environment:
1. Close Jupyter Lab
2. Activate the correct environment:
   ```bash
   micromamba activate galaticbot
   ```
3. Launch again:
   ```bash
   jupyter lab
   ```

## Verifying Kernel

Test that the kernel works:

```python
# Run this in a notebook cell
import sys
print(f"Python executable: {sys.executable}")
print(f"Expected: /Users/jburgess/micromamba/envs/galaticbot/bin/python")

# Test imports
from great_silence.notebook import SimulationWidget
print("✓ GalaticBot imports work!")
```

Expected output:
```
Python executable: /Users/jburgess/micromamba/envs/galaticbot/bin/python
✓ GalaticBot imports work!
```

## Kernel Management

### List all kernels
```bash
jupyter kernelspec list
```

### Remove a kernel (if needed)
```bash
jupyter kernelspec remove galaticbot
```

### Reinstall kernel (if corrupted)
```bash
# Remove old kernel
jupyter kernelspec remove galaticbot

# Reinstall
~/.local/bin/micromamba run -n galaticbot python -m ipykernel install --user --name galaticbot --display-name "Python (galaticbot)"
```

## Environment Info

- **Kernel name:** galaticbot
- **Display name:** Python (galaticbot)
- **Python path:** /Users/jburgess/micromamba/envs/galaticbot/bin/python
- **Kernel location:** /Users/jburgess/Library/Jupyter/kernels/galaticbot

## Notes

- The kernel is registered **globally** for your user account
- You can use it from Jupyter Lab launched in **any directory**
- The kernel automatically uses the galaticbot micromamba environment
- All dependencies (ipywidgets, h5py, pythreejs) are available in this kernel

---

**Ready to go!** Open `notebooks/01_quickstart_production_workflow.ipynb` and select the "Python (galaticbot)" kernel to get started. 🚀
