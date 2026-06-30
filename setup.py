from setuptools import find_packages, setup

setup(
    name="libriscribe",
    version="0.8.0",
    python_requires=">=3.10",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "fastapi",
        "uvicorn[standard]",
        "websockets",
        "python-multipart",
        "openai",
        "python-dotenv",
        "pydantic",
        "pydantic-settings",
        "pyyaml",
        "beautifulsoup4",
        "requests",
        "markdown",
        "fpdf",
        "tenacity",
        "anthropic",
        "google-genai>=2.7.0",
        "pystray",
        "Pillow",
    ],
    entry_points={
        "console_scripts": [
            "libriscribe=libriscribe.server:main",
        ],
    },
)
