# Jupyter Setup for GalaticBot

## ✅ Setup Complete!

JupyterLab is now running from your **micromamba galaticbot environment** with all dependencies properly installed.

## 🎯 What Was Done

### 1. **Cleaned Up Old Setup**
- Stopped the old virtualenvwrapper-based Jupyter instance
- Now using micromamba environment exclusively

### 2. **Installed Dependencies in Mamba Environment**
```bash
~/.local/bin/micromamba run -n galaticbot pip install jupyterlab ipywidgets plotly ipykernel nbformat
```

### 3. **Registered Kernel**
The **Python (galaticbot)** kernel is now available in JupyterLab:
```bash
~/.local/bin/micromamba run -n galaticbot python -m ipykernel install --user --name galaticbot
```

### 4. **Launched from Mamba Environment**
```bash
~/.local/bin/micromamba run -n galaticbot jupyter lab
```

## 🚀 Current Status

**Jupyter Server Running**: ✅
**Port**: 8888
**Kernel Available**: Python (galaticbot)

## 🔧 Managing JupyterLab

### Start JupyterLab
```bash
cd /Users/jburgess/coding/projects/galaticbot/notebooks
~/.local/bin/micromamba run -n galaticbot jupyter lab
```

### Stop JupyterLab
In the terminal where Jupyter is running:
- Press `Ctrl+C` twice

Or from another terminal:
```bash
# Find the process
ps aux | grep jupyter

# Kill it (replace PID with actual process ID)
kill <PID>
```

### List Available Kernels
```bash
jupyter kernelspec list
```

You should see:
```
Available kernels:
  galaticbot    /Users/jburgess/Library/Jupyter/kernels/galaticbot
  python3       /Users/jburgess/Library/Jupyter/kernels/python3
```

## 📝 Using the Notebook

1. **Open JupyterLab** in your browser at the URL shown above
2. **Navigate** to `interactive_simulation.ipynb`
3. **Select Kernel**: Click on the kernel name in the top-right corner
4. **Choose**: "Python (galaticbot)" from the dropdown
5. **Run cells**: Execute the notebook cells

## 🧹 Removing Old Jupyter Installations (Optional)

If you want to completely remove the old virtualenvwrapper Jupyter:

```bash
# Uninstall from user Python
pip uninstall -y jupyter jupyterlab ipywidgets

# Or if you want to keep it but prevent conflicts, just use the mamba version
# No action needed - we're already using it!
```

## 💡 Tips

- Always launch Jupyter from the mamba environment using the command above
- The galaticbot kernel has access to all packages in the mamba environment
- If you install new packages, install them in the mamba environment:
  ```bash
  ~/.local/bin/micromamba run -n galaticbot pip install <package>
  ```

## 🔍 Troubleshooting

**Kernel not showing up?**
```bash
~/.local/bin/micromamba run -n galaticbot python -m ipykernel install --user --name galaticbot --display-name "Python (galaticbot)"
```

**Wrong packages?**
Make sure you're in the right environment:
```bash
~/.local/bin/micromamba run -n galaticbot pip list
```

**Port 8888 already in use?**
```bash
# Find what's using port 8888
lsof -i :8888

# Kill it
kill <PID>

# Or use a different port
~/.local/bin/micromamba run -n galaticbot jupyter lab --port=8889
```
