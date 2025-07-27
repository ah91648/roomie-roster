# 🏠 RoomieRoster

**Household Chore Management Made Easy**

RoomieRoster is a full-stack web application that helps roommates fairly distribute household chores using intelligent assignment algorithms. The application features both predefined rotation assignments and randomized weighted distribution to ensure everyone gets a fair share of the work.

## 🌟 Features

### Core Functionality
- **Roommate Management**: Add, edit, and remove roommates from your household
- **Chore Management**: Create and manage chores with different frequencies and difficulty levels
- **Smart Assignment System**: 
  - **Predefined Chores**: Round-robin rotation ensures everyone takes turns
  - **Random Chores**: Weighted selection based on current cycle points for fairness
- **Real-time Results**: View current assignments organized by roommate
- **Cycle Management**: Automatic point reset and manual cycle control

### Technical Features
- **Full-stack Architecture**: Python Flask backend with React frontend
- **JSON File Storage**: Simple, portable data persistence
- **RESTful API**: Clean API design with proper error handling
- **Responsive Design**: Works on desktop and mobile devices
- **End-to-End Testing**: Comprehensive Playwright test suite

## 🏗️ Architecture

```
roomie-roster/
├── backend/               # Python Flask API
│   ├── app.py            # Main Flask application
│   ├── requirements.txt  # Python dependencies
│   ├── data/            # JSON data files
│   │   ├── chores.json
│   │   ├── roommates.json
│   │   └── state.json
│   └── utils/           # Core logic modules
│       ├── data_handler.py
│       └── assignment_logic.py
├── frontend/            # React SPA
│   ├── package.json
│   ├── src/
│   │   ├── App.js       # Main React component
│   │   ├── components/  # React components
│   │   └── services/    # API integration
│   └── public/
└── tests/               # End-to-end tests
    └── playwright/
        ├── playwright.config.js
        └── e2e/         # Test suites
```

## 🚀 Quick Start

### 🎯 **One-Click Launch (Recommended)**

The easiest way to run RoomieRoster is using the automatic launcher:

```bash
# Simply run the launcher script
python3 launch_app.py
```

**Or use the platform-specific scripts:**

**macOS/Linux:**
```bash
./launch_app.sh
```

**Windows:**
```cmd
launch_app.bat
```

The launcher will:
- ✅ Check all requirements (Python, Node.js, npm)
- 📦 Install missing dependencies automatically  
- 🚀 Start both backend and frontend servers
- 🌐 Open your browser to http://localhost:3000
- 🔄 Handle graceful shutdown with Ctrl+C

### 📋 Prerequisites
- **Python 3.8+** with pip
- **Node.js 16+** with npm

### 🛠️ Manual Setup (Alternative)

If you prefer to start servers manually:

#### 1. Backend Setup

```bash
# Navigate to backend directory
cd roomie-roster/backend

# Create and activate virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Start the Flask server
python app.py
```

The backend will be available at **http://localhost:5000**

#### 2. Frontend Setup

Open a new terminal window:

```bash
# Navigate to frontend directory
cd roomie-roster/frontend

# Install Node.js dependencies
npm install

# Start the React development server
npm start
```

The frontend will be available at **http://localhost:3000**

#### 3. Access the Application

Open your web browser and navigate to **http://localhost:3000**

## 📱 Usage Guide

### Getting Started

1. **Add Roommates**: Start by adding all household members in the "Roommates" tab
2. **Create Chores**: Add your household chores in the "Chores" tab with appropriate frequencies and point values
3. **Assign Chores**: Go to the "Assignments" tab and click "Assign Chores" to generate fair assignments

### Chore Types

**Predefined Chores** 🔄
- Use round-robin rotation
- Each roommate takes turns in order
- Perfect for chores that need consistent assignment (e.g., cleaning bathroom)

**Random Chores** 🎲
- Use weighted random selection
- Roommates with fewer points have higher probability of assignment
- Points accumulate during the cycle for fairness
- Great for variable chores (e.g., taking out trash)

### Assignment Cycle

- A new cycle starts automatically based on chore frequencies
- All roommate points reset to 0 at the beginning of each cycle
- You can manually reset the cycle using the "Reset Cycle" button

## 🧪 Testing

### End-to-End Tests with Playwright

The application includes comprehensive E2E tests to ensure reliability:

```bash
# Navigate to test directory
cd roomie-roster/tests/playwright

# Install test dependencies
npm install
npx playwright install

# Run tests (requires both backend and frontend to be running)
npm test

# Run tests with browser visible
npm run test:headed

# Debug tests interactively
npm run test:debug

# View test report
npm run test:report
```

### Test Coverage

- **Roommate Management**: Adding, editing, deleting roommates
- **Chore Management**: Creating, updating, removing chores
- **Assignment Workflow**: Full assignment process and error handling
- **Cross-browser Testing**: Chrome, Firefox, Safari, and mobile browsers

## 🔧 API Documentation

### Base URL
```
http://localhost:5000/api
```

### Endpoints

#### Roommates
- `GET /roommates` - Get all roommates
- `POST /roommates` - Add new roommate
- `PUT /roommates/{id}` - Update roommate
- `DELETE /roommates/{id}` - Delete roommate

#### Chores
- `GET /chores` - Get all chores
- `POST /chores` - Add new chore
- `PUT /chores/{id}` - Update chore
- `DELETE /chores/{id}` - Delete chore

#### Assignments
- `POST /assign-chores` - Trigger chore assignment
- `GET /current-assignments` - Get current assignments
- `POST /reset-cycle` - Reset assignment cycle

#### System
- `GET /health` - Health check
- `GET /state` - Get application state

### Example API Usage

```javascript
// Assign chores
const response = await fetch('/api/assign-chores', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' }
});
const result = await response.json();
console.log(result.assignments);
```

## 🔄 Assignment Algorithm

### Predefined Chore Rotation
```python
def assign_predefined_chore(chore):
    # Get last assigned roommate for this chore
    last_assigned = get_last_assigned(chore.id)
    
    # Find next roommate in rotation
    next_roommate = get_next_in_rotation(last_assigned)
    
    # Update assignment state
    update_chore_state(chore.id, next_roommate.id)
    
    return next_roommate
```

### Random Chore Assignment
```python
def assign_random_chore(chore):
    # Calculate weights (lower points = higher probability)
    weights = []
    for roommate in roommates:
        weight = max_points - roommate.current_cycle_points
        weights.append(weight)
    
    # Weighted random selection
    selected = random.choices(roommates, weights=weights)[0]
    
    # Update points
    selected.current_cycle_points += chore.points
    
    return selected
```

## 🔧 Configuration

### Environment Variables

The application uses the following configuration options:

**Backend (Flask)**
- `DEBUG`: Set to `True` for development mode
- `HOST`: Server host (default: `0.0.0.0`)
- `PORT`: Server port (default: `5000`)

**Frontend (React)**
- Development server automatically proxies API requests to `http://localhost:5000`
- For production, update the API base URL in `src/services/api.js`

### Data Files

All application data is stored in JSON files in the `backend/data/` directory:

- `chores.json`: Chore definitions
- `roommates.json`: Roommate information and current points
- `state.json`: Application state and assignment history

These files are automatically created with sample data when the application first runs.

## 🐛 Troubleshooting

### Common Issues

**Backend won't start**
- Ensure Python 3.8+ is installed
- Activate virtual environment: `source venv/bin/activate`
- Install dependencies: `pip install -r requirements.txt`
- Check port 5000 isn't already in use

**Frontend can't connect to backend**
- Verify backend is running on port 5000
- Check browser console for CORS errors
- Ensure both servers are running simultaneously

**Tests failing**
- Ensure both backend and frontend are running
- Check that ports 3000 and 5000 are available
- Run tests with `npm run test:headed` to see browser interactions

**Data not persisting**
- Check write permissions in `backend/data/` directory
- Verify JSON files aren't corrupted
- Restart the backend server

### Getting Help

If you encounter issues:

1. Check the browser console for error messages
2. Review the backend server logs
3. Ensure all dependencies are properly installed
4. Try restarting both servers

## 🚀 Production Deployment

### Backend Deployment
```bash
# Install production WSGI server
pip install gunicorn

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Frontend Deployment
```bash
# Build for production
npm run build

# Serve static files with nginx, Apache, or any static file server
```

### Docker Deployment (Optional)
```dockerfile
# Example Dockerfile for backend
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run the test suite
5. Submit a pull request

### Code Style
- **Python**: Follow PEP 8 guidelines
- **JavaScript**: Use ES6+ features and React best practices
- **Testing**: Add tests for new features

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🎯 Future Enhancements

- [ ] User authentication and multi-household support
- [ ] Email/SMS notifications for assignments
- [ ] Mobile app using React Native
- [ ] Advanced analytics and reporting
- [ ] Integration with calendar applications
- [ ] Chore completion tracking and history
- [ ] Reward system and gamification
- [ ] Database backend (PostgreSQL/MongoDB)

---

**Made with ❤️ for harmonious households everywhere**