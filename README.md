# Hevy API Dashboard

A workout tracker that uses the Hevy public API to pull and visualize your workout data.

This is a personal project that creates a web-based dashboard for tracking and analyzing workouts from the public Hevy API.

**Note:** This project has only been tested with my own workout data. Feel free to use and build upon. Read section on API usage below.

## Features

- **Weeklday heatmap**: Visual representation of workouts per week
- **Weekly volume graph**: Monitor weekly training volume and progression
- **Weekly sets per muscle groups**: Track sets per muscle group over time
- **Workout Details**: View of specific workouts and the exercises done
- **Weekly Comments**: Add personal notes for each week
- **Progression line graph**: View 1RM, Volume or Best PR (set per min reps) for specific exercises
- **Muscle group categorization**: Possibility to add your own muscle groups and map exercises to these custom muscle groups. Setting to override the standard Hevy muscle group categorization.

## Stack

- Python 3.12
- FastAPI
- SQLAlchemy
- PostgreSQL
- Pydantic
- Requests
- HTML5
- CSS3
- Chart.js


## Quick Start with Docker


1. **Clone the repository**
   ```bash
   git clone https://github.com/fhanel/hevy-api-dashboard.git
   cd hevy-api-dashboard
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and add your configuration:
   - PostgreSQL database credentials
   - Hevy API key
   - API port settings

3. **Run with Docker Compose**
   ```bash
   docker-compose up -d
   ```

4. **Access the dashboard**
   Open your browser and go to `http://localhost:8000`

## Repository Structure

```
hevy-api-dashboard/
├── app/                    # Backend API (FastAPI)
│   ├── main.py            # API endpoints and routes
│   ├── models.py          # Database models (SQLAlchemy)
│   ├── hevy_client.py     # Hevy API integration
│   ├── sync.py            # Data sync
│   └── requirements.txt   # Dependencies
├── frontend/              # Frontend (HTML/CSS/JavaScript)
│   ├── index.html         # Main dashboard
│   ├── data.html          # Workout data table
│   ├── progression.html   # Progression charts
│   ├── settings.html      # Configuration
│   ├── styles.css         # Styling
│   └── shared.js          # Common utilities
├── docker/                # Docker configuration
│   └── api.Dockerfile     # API container setup
├── docker-compose.yml     # Multi-container setup
└── .env.example          # Environment variables template
```

## API Usage

This project integrates with the Hevy API.  
To use it, you must be a **Hevy Pro subscriber** and provide your own API key.  

- This project is not affiliated with Hevy.  
- You are responsible for complying with Hevy's Terms of Service.  
- Do not share your API key publicly.

## License

MIT License
