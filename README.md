# Icon Changer (VSCode Material Icons)

A modern, dark-themed GUI application to easily change folder and file icons on Linux (and Windows), utilizing the beautiful [VSCode Material Icon Theme](https://github.com/PKief/vscode-material-icon-theme) collection.

## ✨ Features

- **Modern UI**: Built with CustomTkinter for a sleek, dark-themed look.
- **Huge Collection**: Access to hundreds of high-quality icons.
- **Search**: Instantly filter icons by name.
- **Auto-Detection**: Automatically suggests the correct icon based on file extensions (e.g., `.py` -> Python icon).
- **Auto-Update**: Functionality to check for updates from GitHub Releases.
- **Cross-Platform**: Designed for Linux (using `gio` metadata) but built on cross-platform Python libraries.

## 🚀 Installation & Usage

### Method 1: Running from Source

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/your-username/icon-changer.git
    cd icon-changer
    ```

2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    *Note: You may need system libraries for `cairosvg` (e.g., `libcairo2` on Linux).*

3.  **Run the app**:
    ```bash
    python folder_icon_changer.py
    ```

### Method 2: Running the Executable (if available)

Just download the latest release, extract it, and ensure the `icons` folder is in the same directory as the executable. Run `IconChanger`.

## 🛠️ Building the Executable

To create a standalone executable for your system:

1.  Install the requirements (as above).
2.  Run the build script:
    ```bash
    python build.py
    ```
3.  The executable will be generated in the `dist/` directory.

## ⚙️ Configuration

To enable Auto-Updates, update the repository configuration in `folder_icon_changer.py`:

```python
APP_VERSION = "0.0.1"
GITHUB_REPO = "your_username/your_repo"
```

## 📝 License

This project uses icons from the VSCode Material Icon Theme. Please refer to their license for icon usage.
The code for this tool is open source.
