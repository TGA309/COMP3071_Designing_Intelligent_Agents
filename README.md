# Designing Intelligent Agents (COMP3071)

Coursework Repository for the module COMP3071 - Designing Intelligent Agents.

Topic Chosen: Intelligent Web Crawling Agent

Title: Domain Agnostic Web Crawler (DAWC)


# Overview

The Domain Agnostic Web Crawler (DAWC) is an intelligent web crawling agent that can navigate and extract information from websites across various domains. The application consists of a FastAPI backend for handling the crawling logic and API requests, and a ReactJS + ViteJS frontend for user interaction and visualization of crawled data.


# Project Structure
    project-root/
    ├── api/                  # API routes and logic
    ├── crawler/              # Web crawler core implementation
    ├── frontend/             # ReactJS + ViteJS frontend application
    │   ├── public/           # Static assets served as-is (favicon, robots.txt, images)
    │   ├── src/              # Source code (React components, JS/TS files, CSS/SCSS)
    │   ├── .env.example      # Frontend environment variables example
    │   ├── ....
    ├── .env.example          # Backend environment variables example
    ├── .gitignore            # Git ignore rules
    ├── config.py             # Backend configuration settings
    ├── LICENSE               # License file
    ├── main_backend.py       # Backend entry point
    ├── README.md             # Readme File
    └── requirements.txt      # Python dependencies


# Prerequisites

Before setting up the project, make sure you have the following installed:

- **Python 3.12.9+** – For the backend
- **Node.js 21+** – For the frontend
- **npm** – Package manager for frontend dependencies
- **A Mistral AI API Key** – Required for the backend's AI capabilities


# Installation & Setup

## Backend Setup

1. **Create a virtual environment:**

    ```bash
    python -m venv venv
    ```

2. **Activate the virtual environment**

    - On **Windows**:

        ```bash
        venv\Scripts\activate
        ```

    - On **macOS/Linux**:

        ```bash
        source venv/bin/activate
        ```

3. **Install backend dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4. **Configure environment variables:**

    ```bash
    cp .env.example .env
    ```

    Open `.env` and add your Mistral AI API key:

    ```
    MISTRAL_API_KEY=your_api_key_here
    ```

## Frontend Setup

1. **Navigate to the frontend directory:**

    ```bash
    cd frontend
    ```

2. **Install frontend dependencies:**

    ```bash
    npm install
    ```

3. **Configure frontend environment variables:**

    ```bash
    cp .env.example .env
    ```


# Running the Application

## Starting the Backend

1. **Ensure your virtual environment is activated:**

    - On **Windows**:

        ```bash
        venv\Scripts\activate
        ```

    - On **macOS/Linux**:

        ```bash
        source venv/bin/activate
        ```

2. **Start the backend server:**

    ```bash
    python main_backend.py
    ```

The backend server will start on `http://localhost:3000`.

## Starting the Frontend

1. **Navigate to the frontend directory (if not already there):**

    ```bash
    cd frontend
    ```

2. **Start the development server:**

    ```bash
    npm run dev
    ```

The frontend server will start at `http://localhost:5173`.


# Usage

Once both the frontend and backend are running:

1.  Open your browser and navigate to the frontend URL provided in the terminal (usually `http://localhost:5173`)
2.  Use the web interface to configure and initiate web crawling operations
3.  The backend API will be accessible at `http://localhost:3000/api`


# Features

*   **Domain Agnostic Crawling**: Intelligently crawl websites regardless of their domain or structure
*   **AI-Powered Analysis**: Leverages Mistral AI for understanding website content
*   **Interactive Visualization**: View and analyze crawled data through the frontend interface


# Technology Stack

*   **Backend**: Python, FastAPI, Uvicorn
*   **Frontend**: JavaScript, React, ViteJS
*   **AI Integration**: Mistral AI
*   **API**: RESTful API with CORS support

# Troubleshooting

## Common Issues

1.  **Backend fails to start**:
    *   Ensure your virtual environment is activated
    *   Verify that all dependencies are installed (`pip install -r requirements.txt`)
    *   Check that your `.env` file has a valid Mistral AI API key
2.  **Frontend fails to start**:
    *   Ensure all dependencies are installed (`npm install`)
    *   Verify that your frontend `.env` file is properly configured
    *   Check that Node.js is properly installed and up to date
3.  **Connection errors between frontend and backend**:
    *   Ensure both services are running
    *   Check that the backend URL in the frontend configuration is correct
    *   Verify CORS settings in the backend if you're experiencing cross-origin issues

# License

This project is an academic work created for the COMP3071 module at the University of Nottingham.

# Acknowledgements

*   University of Nottingham, School of Computer Science
*   Mistral AI for providing the API used in this project

* * *
For any questions or issues, please open an issue in this repository.