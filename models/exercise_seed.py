"""
Predefined wellness exercises for the Envira app
"""

PREDEFINED_EXERCISES = [
    {
        "exercise_id": "breathing-4-7-8",
        "name": "Box Breathing (4-7-8)",
        "category": "breathing",
        "description": "Calming breathing technique to reduce stress and anxiety. Inhale for 4, hold for 7, exhale for 8.",
        "total_duration_seconds": 300,  # 5 minutes
        "difficulty": "beginner",
        "steps": [
            {
                "step_number": 1,
                "title": "Get Ready",
                "description": "Find a comfortable seated position. You can be on a chair, floor, or your bed.",
                "duration_seconds": 15,
                "guidance": "Sit with your spine upright but not rigid. Relax your shoulders.",
                "cues": ["Comfortable position", "Back straight", "Relaxed shoulders"]
            },
            {
                "step_number": 2,
                "title": "First Round - Inhale",
                "description": "Breathe in slowly through your nose for a count of 4.",
                "duration_seconds": 5,
                "guidance": "Count slowly: 1... 2... 3... 4. Focus on filling your belly with air.",
                "cues": ["Through the nose", "Slow count", "Feel your belly expand"]
            },
            {
                "step_number": 3,
                "title": "First Round - Hold",
                "description": "Hold your breath for a count of 7.",
                "duration_seconds": 7,
                "guidance": "Count: 1... 2... 3... 4... 5... 6... 7. Stay calm and relaxed.",
                "cues": ["Hold steady", "Don't tense up", "Stay calm"]
            },
            {
                "step_number": 4,
                "title": "First Round - Exhale",
                "description": "Exhale slowly through your mouth for a count of 8.",
                "duration_seconds": 8,
                "guidance": "Breathe out completely. You can make a gentle whooshing sound if it helps.",
                "cues": ["Through the mouth", "Slow and complete", "Release tension"]
            },
            {
                "step_number": 5,
                "title": "Continue (Rounds 2-5)",
                "description": "Repeat the cycle (inhale 4, hold 7, exhale 8) 4 more times.",
                "duration_seconds": 240,
                "guidance": "You're doing great. Continue with the same rhythm. Each cycle takes about 20 seconds.",
                "cues": ["Keep the rhythm", "Stay focused", "You've got this"]
            },
            {
                "step_number": 6,
                "title": "Finish",
                "description": "Return to normal breathing. Take a moment to notice how you feel.",
                "duration_seconds": 15,
                "guidance": "Slowly resume your normal breathing pattern. You may feel calmer and more focused.",
                "cues": ["Return to normal", "Notice the calm", "Breathe naturally"]
            }
        ],
        "benefits": ["Stress relief", "Anxiety reduction", "Improved focus", "Better sleep"],
        "prerequisites": ["Quiet space", "Comfortable seating"],
        "ideal_environment": {"light": "dimmed", "sound": "quiet", "temperature": "comfortable"},
        "frequency_recommendation": "1-3 times per day",
        "best_time": "Any time, especially when stressed or before bed"
    },
    {
        "exercise_id": "meditation-5min-mindfulness",
        "name": "5-Minute Mindfulness Meditation",
        "category": "meditation",
        "description": "A simple mindfulness meditation to calm the mind and increase awareness. Perfect for beginners.",
        "total_duration_seconds": 300,  # 5 minutes
        "difficulty": "beginner",
        "steps": [
            {
                "step_number": 1,
                "title": "Setup",
                "description": "Find a quiet space and sit comfortably. You can use a cushion or chair.",
                "duration_seconds": 20,
                "guidance": "Settle into a position you can hold for 5 minutes. Sit with your back straight.",
                "cues": ["Quiet space", "Comfortable position", "Straight spine"]
            },
            {
                "step_number": 2,
                "title": "Body Awareness",
                "description": "Close your eyes and take three deep breaths. Notice the weight of your body.",
                "duration_seconds": 30,
                "guidance": "Breathe in through your nose, out through your mouth. Feel your body supported by the chair or cushion.",
                "cues": ["Eyes closed", "Deep breaths", "Feel supported"]
            },
            {
                "step_number": 3,
                "title": "Focus on Breath",
                "description": "Begin to notice your natural breath without trying to change it.",
                "duration_seconds": 180,
                "guidance": "Don't control your breathing—just observe it. Notice the cool air as you inhale, warm air as you exhale.",
                "cues": ["Let it happen", "Observe without changing", "Natural rhythm"]
            },
            {
                "step_number": 4,
                "title": "Acknowledge Thoughts",
                "description": "When your mind wanders (and it will), gently acknowledge the thought and return focus to your breath.",
                "duration_seconds": 60,
                "guidance": "Thoughts are normal. Don't judge them. Simply notice them passing and bring your attention back to your breathing.",
                "cues": ["Thoughts are okay", "Be gentle with yourself", "Return to breath"]
            },
            {
                "step_number": 5,
                "title": "Closing",
                "description": "Slowly deepen your breath and prepare to open your eyes.",
                "duration_seconds": 10,
                "guidance": "Take a few deeper breaths. When ready, slowly open your eyes.",
                "cues": ["Wake up gently", "Take deeper breaths", "Open eyes slowly"]
            }
        ],
        "benefits": ["Mental clarity", "Stress reduction", "Improved focus", "Emotional balance"],
        "prerequisites": ["Quiet space", "10 minutes of uninterrupted time"],
        "ideal_environment": {"light": "dimmed", "sound": "very quiet", "temperature": "warm"},
        "frequency_recommendation": "Daily, preferably in the morning",
        "best_time": "Morning or before important tasks"
    },
    {
        "exercise_id": "stretching-desk-break",
        "name": "Desk Break Stretching (3 minutes)",
        "category": "stretching",
        "description": "Quick stretching routine for people who sit at desks. Relieves tension in neck, shoulders, and back.",
        "total_duration_seconds": 180,  # 3 minutes
        "difficulty": "beginner",
        "steps": [
            {
                "step_number": 1,
                "title": "Neck Rolls",
                "description": "Gently roll your head in circles to release neck tension.",
                "duration_seconds": 30,
                "guidance": "Drop your right ear toward your right shoulder, roll chin down toward chest, then lift left ear toward left shoulder. Repeat 3 times each direction.",
                "cues": ["Gentle circles", "No forcing", "Breathe steadily"]
            },
            {
                "step_number": 2,
                "title": "Shoulder Shrugs",
                "description": "Shrug your shoulders up to your ears, hold, then release.",
                "duration_seconds": 30,
                "guidance": "Inhale as you shrug shoulders up. Hold for 2 seconds. Exhale and let them drop. Repeat 5 times.",
                "cues": ["Up to ears", "Hold it", "Release with exhale"]
            },
            {
                "step_number": 3,
                "title": "Chest and Shoulder Stretch",
                "description": "Clasp your hands behind your back and straighten your arms.",
                "duration_seconds": 45,
                "guidance": "Interlace fingers behind your back. Straighten arms and lift your chest. Hold for 30 seconds. Release and shake out.",
                "cues": ["Hands clasped", "Chest up", "Feel the stretch"]
            },
            {
                "step_number": 4,
                "title": "Spinal Twist",
                "description": "Twist your torso gently from side to side while seated.",
                "duration_seconds": 30,
                "guidance": "Cross your right arm over your chest and gently pull your right shoulder back. Hold for 15 seconds each side.",
                "cues": ["Gentle twist", "Hold each side", "Keep hips still"]
            },
            {
                "step_number": 5,
                "title": "Standing Back Extension",
                "description": "Stand and gently arch your back to counter slouching.",
                "duration_seconds": 30,
                "guidance": "Stand up. Place hands on lower back and gently lean backward. Hold for 20 seconds.",
                "cues": ["Hands on back", "Gentle arch", "Don't overdo it"]
            },
            {
                "step_number": 6,
                "title": "Forward Fold",
                "description": "Gently bend forward to stretch your hamstrings and back.",
                "duration_seconds": 30,
                "guidance": "Keep knees slightly bent. Slowly fold forward and let your arms hang. You should feel a gentle stretch. Hold for 20 seconds.",
                "cues": ["Knees bent", "Fold gently", "No bouncing"]
            },
            {
                "step_number": 7,
                "title": "Finish",
                "description": "Return to standing and take a few deep breaths.",
                "duration_seconds": 15,
                "guidance": "Roll up slowly from your fold. Stand and take 3 deep breaths. Notice how your body feels.",
                "cues": ["Roll up slowly", "Deep breaths", "Notice the difference"]
            }
        ],
        "benefits": ["Reduced muscle tension", "Better posture", "Increased flexibility", "Mental break"],
        "prerequisites": ["Open space to stand", "A few minutes away from desk"],
        "ideal_environment": {"light": "normal", "sound": "any", "temperature": "normal"},
        "frequency_recommendation": "Every 1-2 hours during work",
        "best_time": "During work breaks, between tasks"
    },
    {
        "exercise_id": "focus-technique-pomodoro",
        "name": "Pomodoro Focus Session (25 minutes)",
        "category": "focus",
        "description": "The Pomodoro Technique: focused 25-minute work session with 5-minute break. Ideal for studying or deep work.",
        "total_duration_seconds": 1500,  # 25 minutes
        "difficulty": "intermediate",
        "steps": [
            {
                "step_number": 1,
                "title": "Prepare Your Space",
                "description": "Set up your workspace. Remove distractions and gather materials you need.",
                "duration_seconds": 60,
                "guidance": "Put your phone away. Close unnecessary browser tabs. Have water nearby.",
                "cues": ["Clear desk", "Phone away", "Have water"]
            },
            {
                "step_number": 2,
                "title": "Set Your Task",
                "description": "Choose a specific task you'll work on for the next 25 minutes.",
                "duration_seconds": 30,
                "guidance": "Make it specific: not 'study' but 'complete section 3 of chapter 5'.",
                "cues": ["Specific task", "Realistic for 25 min", "Clear goal"]
            },
            {
                "step_number": 3,
                "title": "Work Focus Session",
                "description": "Work on your task for 25 minutes. Stay focused. No distractions.",
                "duration_seconds": 1350,
                "guidance": "Use a timer. When your mind wanders, gently bring it back to your task. You've got this!",
                "cues": ["Timer started", "Stay focused", "One task"]
            },
            {
                "step_number": 4,
                "title": "Take a Break",
                "description": "Stop and take a 5-minute break. Stand up, move, hydrate.",
                "duration_seconds": 60,
                "guidance": "You completed one Pomodoro! Stand up, walk around, drink water, or step outside briefly.",
                "cues": ["Great job", "Stand up", "Move around", "Hydrate"]
            }
        ],
        "benefits": ["Improved focus", "Better productivity", "Reduced procrastination", "Better time management"],
        "prerequisites": ["Quiet workspace", "Timer"],
        "ideal_environment": {"light": "bright", "sound": "quiet", "temperature": "cool"},
        "frequency_recommendation": "3-5 sessions per day",
        "best_time": "Morning, or when you need focused work"
    },
    {
        "exercise_id": "relaxation-progressive-muscle",
        "name": "Progressive Muscle Relaxation (10 minutes)",
        "category": "relaxation",
        "description": "A deeply calming technique that systematically tenses and relaxes muscle groups to reduce physical and mental tension.",
        "total_duration_seconds": 600,  # 10 minutes
        "difficulty": "beginner",
        "steps": [
            {
                "step_number": 1,
                "title": "Get Comfortable",
                "description": "Lie down on your back or recline in a comfortable chair.",
                "duration_seconds": 30,
                "guidance": "You can use a pillow under your head and knees if needed. This exercise is best done lying down.",
                "cues": ["Lie flat", "Comfortable position", "Legs uncrossed"]
            },
            {
                "step_number": 2,
                "title": "Deep Breathing Setup",
                "description": "Take 3 slow, deep breaths to begin the relaxation process.",
                "duration_seconds": 30,
                "guidance": "Inhale through your nose for 4 counts, hold for 4, exhale for 4. Feel your body sinking into the surface.",
                "cues": ["Slow breaths", "In through nose", "Out through mouth"]
            },
            {
                "step_number": 3,
                "title": "Feet & Legs",
                "description": "Tense your feet and legs for 5 seconds, then release.",
                "duration_seconds": 60,
                "guidance": "Curl your toes and tighten your leg muscles. Hold for 5 seconds. Then completely relax. Feel the warmth and relaxation flow into your legs.",
                "cues": ["Tense for 5", "Then release", "Feel the difference"]
            },
            {
                "step_number": 4,
                "title": "Abdomen & Chest",
                "description": "Tighten your belly and chest muscles, hold, then release.",
                "duration_seconds": 60,
                "guidance": "Take a breath and tighten your abdominal and chest muscles. Hold for 5 seconds. Exhale and relax completely.",
                "cues": ["Tighten core", "Hold it", "Release with exhale"]
            },
            {
                "step_number": 5,
                "title": "Hands & Arms",
                "description": "Make tight fists and tense your arms, hold, then release.",
                "duration_seconds": 60,
                "guidance": "Squeeze your fists tight and tense your arm muscles from shoulders to fingertips. Hold for 5 seconds. Then let go completely.",
                "cues": ["Tight fists", "Tense arms", "Let everything go"]
            },
            {
                "step_number": 6,
                "title": "Neck, Shoulders & Face",
                "description": "Tense your neck, shoulders, and facial muscles, hold, then release.",
                "duration_seconds": 60,
                "guidance": "Shrug shoulders, clench jaw, and squint eyes. Hold for 5 seconds. Release and let your whole face relax.",
                "cues": ["Shrug up", "Clench jaw", "Squint eyes", "Release all"]
            },
            {
                "step_number": 7,
                "title": "Full Body Relaxation",
                "description": "Scan your entire body and consciously relax any remaining tension.",
                "duration_seconds": 120,
                "guidance": "From your toes to your head, notice if any area is still tense. Breathe into it and let it relax. Enjoy this peaceful state.",
                "cues": ["Scan your body", "Let it go", "Peaceful", "Calm"]
            },
            {
                "step_number": 8,
                "title": "Closing",
                "description": "Slowly return to normal awareness. Wiggle fingers and toes, then gradually stand up.",
                "duration_seconds": 30,
                "guidance": "Take a few deep breaths. Wiggle your fingers and toes. When ready, slowly open your eyes and gently sit or stand up.",
                "cues": ["Wake up slowly", "Wiggle fingers/toes", "Feel refreshed"]
            }
        ],
        "benefits": ["Deep relaxation", "Stress relief", "Better sleep", "Reduced muscle tension"],
        "prerequisites": ["Quiet space", "15 minutes uninterrupted"],
        "ideal_environment": {"light": "dimmed or off", "sound": "very quiet", "temperature": "warm"},
        "frequency_recommendation": "Once daily, preferably before bed",
        "best_time": "Evening or before sleep"
    },
    {
        "exercise_id": "movement-light-yoga",
        "name": "Light Yoga Flow (15 minutes)",
        "category": "movement",
        "description": "Gentle yoga flow to improve flexibility, balance, and mind-body connection. Suitable for all levels.",
        "total_duration_seconds": 900,  # 15 minutes
        "difficulty": "beginner",
        "steps": [
            {
                "step_number": 1,
                "title": "Mountain Pose",
                "description": "Stand grounded with feet hip-width apart, arms at your sides.",
                "duration_seconds": 30,
                "guidance": "Feel your feet pressing into the ground. Stand tall. This is your foundation.",
                "cues": ["Feet grounded", "Stand tall", "Arms relaxed"]
            },
            {
                "step_number": 2,
                "title": "Cat-Cow Stretch",
                "description": "Gentle flowing movement between arching and rounding your spine.",
                "duration_seconds": 90,
                "guidance": "On hands and knees. Arch your back (cow), then round it (cat). Flow with your breath. Repeat 5-6 times.",
                "cues": ["Flow with breath", "Gentle movements", "Feel your spine"]
            },
            {
                "step_number": 3,
                "title": "Downward Dog",
                "description": "Invert your body into a V-shape, holding for a few breaths.",
                "duration_seconds": 60,
                "guidance": "Hands and feet on ground, hips high. Press your hands firmly. This stretches your hamstrings and shoulders.",
                "cues": ["Hands firm", "Hips high", "Breathe here"]
            },
            {
                "step_number": 4,
                "title": "Forward Fold",
                "description": "Stand and fold forward, letting your head and arms hang.",
                "duration_seconds": 60,
                "guidance": "Feet hip-width apart. Fold forward gently. Let gravity do the work. Your hamstrings will stretch.",
                "cues": ["Fold gently", "Let it hang", "Relax into it"]
            },
            {
                "step_number": 5,
                "title": "Warrior I",
                "description": "Lunge position building strength and stability.",
                "duration_seconds": 90,
                "guidance": "Step your right foot forward. Square your hips. Reach your arms up. Hold for 5 breaths, then switch legs.",
                "cues": ["Strong stance", "Hips squared", "Reach up"]
            },
            {
                "step_number": 6,
                "title": "Warrior II",
                "description": "Open your hips in Warrior II pose.",
                "duration_seconds": 90,
                "guidance": "From Warrior I, open your hips to the side. Gaze over your front fingertips. You're strong and grounded.",
                "cues": ["Open hips", "Gaze forward", "Powerful stance"]
            },
            {
                "step_number": 7,
                "title": "Triangle Pose",
                "description": "Extended triangle for full-body stretch.",
                "duration_seconds": 60,
                "guidance": "Wide legs, rotate your front foot 90 degrees. Extend your torso over your front leg. One hand reaches up.",
                "cues": ["Wide legs", "Reach out", "Feel the stretch"]
            },
            {
                "step_number": 8,
                "title": "Child's Pose",
                "description": "Resting pose that brings calm.",
                "duration_seconds": 90,
                "guidance": "Knees on the ground, big toes touching. Sink your hips back to your heels. Forehead rests on the mat.",
                "cues": ["Rest here", "Breathe deeply", "Let go"]
            },
            {
                "step_number": 9,
                "title": "Savasana (Corpse Pose)",
                "description": "Final relaxation pose. Lie flat on your back.",
                "duration_seconds": 120,
                "guidance": "Lie with legs extended, arms at your sides (palms up). Let your whole body relax. Breathe naturally.",
                "cues": ["Lie flat", "Palms up", "Total relaxation"]
            }
        ],
        "benefits": ["Flexibility", "Strength", "Better balance", "Stress relief", "Mind-body connection"],
        "prerequisites": ["Yoga mat or soft surface", "Enough space"],
        "ideal_environment": {"light": "natural or soft", "sound": "calm", "temperature": "warm"},
        "frequency_recommendation": "3-4 times per week",
        "best_time": "Morning or evening"
    }
]


def seed_exercises(db):
    """Seed predefined exercises into the database if they don't already exist."""
    try:
        for exercise_data in PREDEFINED_EXERCISES:
            # Check if exercise already exists
            existing = db.exercises.find_one({"exercise_id": exercise_data["exercise_id"]})
            if not existing:
                db.exercises.insert_one(exercise_data)
                print(f"✅ Seeded exercise: {exercise_data['name']}")
            else:
                print(f"⏭️  Exercise already exists: {exercise_data['name']}")
    except Exception as e:
        print(f"❌ Error seeding exercises: {e}")
