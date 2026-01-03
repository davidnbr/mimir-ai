# Mimir AI

Mimir AI is a comprehensive assistant designed with both a Command Line Interface (CLI) and a User Interface (UI). It features voice activation and is built to be highly memory and context aware, providing intelligent and natural interactions. This README provides an overview of the project, setup instructions, and guidance on how to use it.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## Features

-   **CLI & UI**: Interact with the assistant via command line or a graphical user interface.
-   **Voice Activation**: Seamless interaction through spoken commands.
-   **Memory & Context Aware**: The assistant retains information from previous interactions and understands context for more natural and helpful responses.

## Installation

To set up the project environment, follow these steps:

### Prerequisites

- Python 3.8+
- [direnv](https://direnv.net/) (recommended for managing environment variables)
- [Nix](https://nixos.org/download.html) (optional, for `devenv.nix` based development environment)

### Steps

1. **Clone the repository:**

    ```bash
    git clone https://github.com/davidnbr/mimir-ai.git
    cd mimir-ai
    ```

2. **Set up the development environment:**

    If you have Nix and direnv installed, the `devenv.nix` and `.envrc` files will automatically set up the environment for you. Just run:

    ```bash
    direnv allow
    ```

    This will create a virtual environment and install dependencies.

    Alternatively, if you prefer not to use Nix/direnv:
    a. **Create a Python virtual environment:**
    `bash
    python3 -m venv .venv
    `
    b. **Activate the virtual environment:**
    `bash
    source .venv/bin/activate
    `
    c. **Install dependencies:**
    `bash
    pip install -r requirements.txt
    `

3. **Configure environment variables:**
    Copy the example environment file and fill in your details:

    ```bash
    cp .env.example .env
    ```

    Edit the `.env` file to set necessary API keys or configurations.

## Usage

_(Instructions on how to run the project, e.g., `python cli.py --help` or `python simple_workflow.py`)_

## Development

_(Information for developers, e.g., running tests, code style guidelines, project structure explanation)_

## Contributing

We welcome contributions! Please see our [CONTRIBUTING.md](CONTRIBUTING.md) (if it exists) for details on how to get started.

## License

This project is licensed under the [MIT License](LICENSE) - see the [LICENSE](LICENSE) file for details.
