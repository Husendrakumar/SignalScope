# SignalScope - Automatic Radio Signal Analysis

**SIH Project - Problem Statement 147**

SignalScope is a technical radio signal analysis dashboard designed to automatically detect, analyze, demodulate, and decode unknown `.WAV` and `.IQ` radio signal recordings.

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── Header.jsx          # Top title & status bar
│   │   ├── Sidebar.jsx         # Left navigation sidebar & PS 147 badge
│   │   ├── UploadPanel.jsx     # Radio recording upload area (.WAV, .IQ)
│   │   ├── Pipeline.jsx        # 8-stage visual analysis pipeline
│   │   ├── SignalInfoCards.jsx # Technical signal metric cards
│   │   ├── VisualizationPanel.jsx # Signal visualization container
│   │   ├── AnalysisStatus.jsx # Real-time analysis status indicator
│   │   └── RecentActivity.jsx # Activity history log
│   ├── pages/
│   │   └── Dashboard.jsx       # Main dashboard composite page
│   ├── styles/
│   │   └── global.css          # Dark technical theme CSS styles
│   ├── App.jsx                 # Application layout container
│   └── main.jsx                # React DOM entry point
├── index.html
├── package.json
├── vite.config.js
└── README.md
```

## Getting Started

### Prerequisites

Ensure [Node.js](https://nodejs.org/) (v18 or higher) is installed on your system.

### Installation

Navigate to the `frontend/` directory and install the project dependencies:

```bash
cd frontend
npm install
```

### Running the Application

Start the local Vite development server:

```bash
npm run dev
```

The application will be accessible at: `http://localhost:3000`

### Build for Production

To create an optimized production build:

```bash
npm run build
```

## Note on Part 1

This repository currently contains **Part 1 (Frontend Foundation & Dashboard UI)**.
- No backend server connection is implemented in Part 1.
- All signal processing pipeline stages are visual placeholders.
- No mock data or fake signal visualizations are generated.
