# SoloLeveller - A Gamified Habit Tracker

## 📖 Overview

Leveling Life is a revolutionary habit tracking application inspired by the anime "Solo Leveling" and RPG progression systems. It transforms personal development into an engaging, game-like experience where users level up their life attributes while combating the seven deadly sins.

## 🎮 Concept

This self-development tool gamifies personal growth by treating life skills as video game attributes that can be leveled up through positive actions (Atoning) or decreased through negative behaviors (Sinning). The system creates an addictive progression loop that motivates users to continuously improve themselves.

## 🛠️ Tech Stack

- **Python** - Core application logic
- **Tkinter** - GUI framework for desktop interface  
- **SQLite** - Local database for personal data storage


## Screenshots (Work in Progress)
![Alt text](sc1.png)
![Alt text](sc2.png)
![Alt text](sc3.png)

## ⚔️ The Attribute System

### 7 Positive Attributes (0-99 Scale)

1. **Spiritual** 🧘‍♀️
   - Meditation, reading sacred texts, nature walks
   - Practicing gratitude, acts of service, journaling
   
2. **Physical** 💪
   - Working out, sports, cardio, walking
   - Any form of physical exercise or movement
   
3. **Mindful (Focus)** 🎯
   - Uninterrupted deep work sessions
   - Avoiding distractions like TikTok or social media
   
4. **Social** 👥
   - Quality time with family, friends, loved ones
   - Making new meaningful connections
   
5. **Integrity** 🤝
   - Following through on commitments
   - Doing what you said you would do
   
6. **Intellect** 🧠
   - Learning new skills, watching educational content
   - Expanding knowledge in specific fields
   - Seeking out new information deliberately
   
7. **Character** ❤️
   - Acts of kindness and service
   - Helping others without expecting anything in return

### 7 Deadly Sins (Negative Modifiers)

- **Pride** - Arrogance, refusing help, excessive ego
- **Envy** - Jealousy, comparison to others, resentment
- **Wrath** - Anger, rage, losing temper
- **Sloth** - Laziness, procrastination, avoiding responsibilities
- **Greed** - Excessive materialism, selfishness
- **Gluttony** - Overindulgence in food, substances, or activities
- **Lust** - Inappropriate desires, objectifying others

## 🚀 Getting Started

### Initial Setup
1. **Baseline Assessment Quiz** - New users complete a comprehensive quiz to establish starting attribute levels
2. **Attribute floors** - No attribute starts below 35 to reflect basic human capabilities
3. **Ranking System** - Overwatch/Rocket League inspired progression tiers

### Daily Workflow

#### Main Dashboard
- **Date Navigation** - Click left/right arrows to view previous/next days
- **Current Stats Display** - All 7 attributes with current levels and rankings
- **Daily Action Log** - List of completed Atones and Sins for the selected day

#### Taking Actions

**Atoning Process:**
1. Click "Atone" button
2. Select attribute category (e.g., Physical)
3. Choose specific action from predefined list (e.g., "Played a sport")
4. Receive confirmation: "Atoned!"
5. Experience points added to selected attribute

**Sinning Process:**
1. Click "Sin" button  
2. Select which deadly sin was committed
3. Choose specific behavior or select "Other" for custom input
4. Experience points deducted from relevant attributes

## 📊 Progression System

### Scaling
- **Attribute Range**: 0-99 (FIFA card style)
- **Starting Floor**: Minimum 35 for all attributes
- **Difficulty Curve**: Exponentially harder to reach higher levels


## ⚡ Key Features

### Edge Cases Handled
1. **Custom Actions** - "Other" option allows users to input unique activities not in predefined lists
2. **Date Restrictions** - Users can only add Sins/Atones to the current day
3. **One-Time Quiz** - Baseline assessment is only taken once during initial setup

### Data Persistence
- All user data stored locally using SQLite
- Attribute progression history maintained
- Daily action logs preserved

## 🎨 Visual Design

The application features a carefully selected color palette that promotes focus and motivation while maintaining visual appeal for extended daily use.

## 🔧 Installation & Setup

```bash
# Clone the repository
git clone [repository-url]
cd habit-tracker

# Install required dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

if you want to remove database to reset stats : rm habit_tracker.db

## 🎯 Goals & Philosophy

Leveling Life aims to make personal development as engaging as playing your favorite video game. By gamifying self-improvement, users develop a natural addiction to bettering themselves, creating sustainable habits that lead to long-term growth and fulfillment.

## 🤝 Contributing

This is a personal development tool designed for individual use. However, suggestions for improvements and feature requests are welcome.

## 📄 License

This project is intended for personal use and self-development.

