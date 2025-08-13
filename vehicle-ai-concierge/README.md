# Vehicle AI Concierge

The Vehicle AI Concierge is a web-based, conversational AI application that simulates a virtual assistant for a car dealership. This AI-powered concierge can help users with a variety of tasks, including exploring vehicle models, finding parts and accessories, locating dealerships, and even editing car images.

## Features

  * **Conversational Interface:** A user-friendly chat interface allows users to interact with the AI assistant in a natural way.
  * **Multi-Agent System:** The backend is powered by a multi-agent system, where a primary "orchestrator" agent delegates tasks to specialized agents for handling specific queries like website searches, parts lookups, and more.
  * **Tool Integration:** The agents are equipped with a variety of tools that allow them to access and process information from different sources, including:
      * A local parts database
      * A dealership locator that uses a local database of dealership information
      * A website search tool that can search for information on the dealership's website
      * An image editor that can modify images of vehicles based on user requests
  * **Rich Content Display:** The application can display rich content in the chat interface, such as interactive cards for dealerships and accessories, image galleries, and lead generation forms.

## Technical Overview

  * **Backend:**
      * The backend is built with **Python** and the **Flask** web framework.
      * The conversational AI is powered by the **Google Agent Development Kit (ADK)**, which allows for the creation and orchestration of multiple AI agents.
      * The agents use **Google's Gemini models** for natural language understanding and generation.
  * **Frontend:**
      * The frontend is built with **HTML**, **CSS**, and **JavaScript**.
      * **Tailwind CSS** is used for styling the user interface.
  * **Data:**
      * The application uses **JSON** files to store data for parts, dealerships, and user history.
  * **Deployment:**
      * The application is designed to be deployed using **Docker** and **Gunicorn**.

## Getting Started

### Prerequisites

  * Python 3.11+
  * `pip`
  * `virtualenv`

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/vehicle-ai-concierge.git
    cd vehicle-ai-concierge
    ```
2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```
3.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Configuration

1.  **Create a `.env` file:**
    ```bash
    cp .env.example .env
    ```
2.  **Edit the `.env` file** to include your Google Cloud project ID, location, and other configuration details.

### Running the Application

1.  **Run the Flask development server:**
    ```bash
    flask run
    ```
2.  Open your web browser and navigate to `http://127.0.0.1:5000` to access the application.