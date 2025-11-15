def compute_ieq_score(data):
    sensors = data.get("sensors", {})

    mq135 = sensors.get("mq135", 0)
    temp = sensors.get("dht", {}).get("t", 22)
    light = sensors.get("ldr", 0)
    sound = sensors.get("sound_rms", 0)

    aq_score = max(0, 100 - (mq135 / 10))
    thermal_score = 100 - abs(22 - temp) * 5
    light_score = min(100, light / 10)
    sound_score = max(0, 100 - sound * 5)

    ieq_score = (
        aq_score * 0.4 +
        thermal_score * 0.3 +
        light_score * 0.2 +
        sound_score * 0.1
    )
    return round(ieq_score, 1)
def generate_recommendations(ieq_score, user_prefs):
    recommendations = []

    if ieq_score < 50:
        recommendations.append("⚠️ The air quality or comfort is low, consider opening a window or using a purifier.")
    elif ieq_score < 70:
        recommendations.append("🙂 The environment is acceptable, but improving lighting or air circulation could help.")
    else:
        recommendations.append("✅ Great environment for studying!")

    # Use user preferences to refine recommendations
    if "study_time" in user_prefs:
        if user_prefs["study_time"] == "morning":
            recommendations.append("☀️ It's a good time to review key materials.")
        elif user_prefs["study_time"] == "evening":
            recommendations.append("🌙 Try some light reading or coding exercises.")

    if user_prefs.get("light_preference") == "high" and ieq_score < 70:
        recommendations.append("💡 Increase brightness for better focus.")

    return recommendations
