# VERIQ Hospital Management System - Setup Guide

## Prerequisites

Before running this project, you need to install the following:

### 1. Node.js (Required)
Download and install Node.js (v18 or higher recommended):
- **Windows/Mac/Linux**: https://nodejs.org/en/download/
- Choose the LTS (Long Term Support) version
- This will also install `npm` (Node Package Manager)

To verify installation, open terminal/command prompt and run:
```bash
node --version
npm --version
```

### 2. Git (Required for cloning)
Download and install Git:
- **Windows**: https://git-scm.com/download/win
- **Mac**: https://git-scm.com/download/mac
- **Linux**: `sudo apt install git` (Ubuntu/Debian)

---

## Installation Steps

### Step 1: Clone the Repository
```bash
git clone https://github.com/GouravN97/four_of_us_HackAxios.git
cd four_of_us_HackAxios
git checkout harsh-setup
```

### Step 2: Install Dependencies
```bash
npm install
```

This will install all required packages:
- react (v19.2.0)
- react-dom (v19.2.0)
- react-router-dom (v7.11.0)
- react-transition-group (v4.4.5)
- recharts (v3.6.0)
- vite (v7.2.4)
- eslint and other dev dependencies

### Step 3: Run the Development Server
```bash
npm run dev
```

The app will start at `http://localhost:5173` (or another port if 5173 is busy).

---

## Login Credentials

Use these credentials to log in:
- **Hospital ID**: H123
- **First Name**: Harsh
- **Last Name**: Mishra
- **Admin Email**: h123@gmail.com
- **Password**: orange@123

---

## Available Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server |
| `npm run build` | Build for production |
| `npm run preview` | Preview production build |
| `npm run lint` | Run ESLint |

---

## Project Structure

```
├── public/
│   └── assets/images/     # Icons and images
├── src/
│   ├── components/
│   │   ├── Frame0.jsx     # Login Page
│   │   ├── Frame1.jsx     # Dashboard/Overview
│   │   ├── Frame2.jsx     # ER Page
│   │   ├── Frame2_1.jsx   # Patient Prioritization Popup
│   │   ├── Frame3.jsx     # ICU Page
│   │   ├── Frame4.jsx     # Patient Log Page
│   │   └── Frame4_1.jsx   # Add Patient Form Popup
│   ├── App.jsx            # Main App with routing
│   └── main.jsx           # Entry point
├── package.json           # Dependencies
└── vite.config.js         # Vite configuration
```

---

## Troubleshooting

### "npm is not recognized"
- Make sure Node.js is installed and added to PATH
- Restart your terminal after installation

### "Port 5173 is already in use"
- The app will automatically try another port
- Or kill the process using port 5173

### "Module not found" errors
- Run `npm install` again
- Delete `node_modules` folder and run `npm install`

---

## Tech Stack

- **Frontend**: React 19
- **Routing**: React Router DOM 7
- **Charts**: Recharts
- **Build Tool**: Vite 7
- **Styling**: CSS
