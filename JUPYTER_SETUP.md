# Jupyter Lab Setup for GalaticBot

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

This means the widget object is being displayed instead of rendered. **Fix:** Add a semicolon:

```python
# Wrong (shows VBox object):
widget.display()

# Correct (renders widget):
widget.display();  # <-- semicolon suppresses output
```

**Or** just return the widget directly:
```python
widget.main_layout  # Returns widget, Jupyter renders it
```

All notebooks have been updated with the correct syntax.

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
