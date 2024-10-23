import streamlit as st
import yt_dlp
import sqlite3
from datetime import datetime
from transformers import pipeline
from textblob import TextBlob
import speech_recognition as sr

# Set up SQLite database to store video progress, notes, tasks, and quizzes
conn = sqlite3.connect('user_data.db')
c = conn.cursor()

# Create tables if they don't exist
c.execute('''CREATE TABLE IF NOT EXISTS study_material
             (video_id TEXT, user_id TEXT, progress INTEGER, notes TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS tasks
             (user_id TEXT, task TEXT, status TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS reminders
             (user_id TEXT, reminder_time TEXT, message TEXT)''')

conn.commit()

# Load AI models
summarizer = pipeline("summarization")
sentiment_analyzer = pipeline("sentiment-analysis")

# Function to fetch video metadata using yt-dlp
def get_video_details(video_url):
    ydl_opts = {}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info_dict = ydl.extract_info(video_url, download=False)
            video_title = info_dict.get('title', 'Unknown Title')
            video_length = info_dict.get('duration', 0)  # Duration in seconds
            return video_title, video_length
        except Exception as e:
            st.error(f"Failed to retrieve video details: {str(e)}")
            return "Unknown Title", 0

# Function to save progress
def save_progress(video_id, user_id, progress, notes):
    c.execute("INSERT OR REPLACE INTO study_material (video_id, user_id, progress, notes) VALUES (?, ?, ?, ?)",
              (video_id, user_id, progress, notes))
    conn.commit()

# Function to retrieve progress
def get_progress(video_id, user_id):
    c.execute("SELECT progress, notes FROM study_material WHERE video_id = ? AND user_id = ?", (video_id, user_id))
    result = c.fetchone()
    return result if result else (0, "")

# Function to add tasks
def add_task(user_id, task):
    c.execute("INSERT INTO tasks (user_id, task, status) VALUES (?, ?, ?)", (user_id, task, 'Pending'))
    conn.commit()

# Function to get tasks
def get_tasks(user_id):
    c.execute("SELECT task, status FROM tasks WHERE user_id = ?", (user_id,))
    return c.fetchall()

# Function to set reminder
def set_reminder(user_id, reminder_time, message):
    c.execute("INSERT INTO reminders (user_id, reminder_time, message) VALUES (?, ?, ?)", 
              (user_id, reminder_time, message))
    conn.commit()

# Function to get reminders
def get_reminders(user_id):
    c.execute("SELECT reminder_time, message FROM reminders WHERE user_id = ?", (user_id,))
    return c.fetchall()

# Function to analyze sentiment of notes
def analyze_sentiment(note):
    result = sentiment_analyzer(note)
    return result[0]

# Function to summarize video transcript
def summarize_video_transcript(transcript):
    return summarizer(transcript, max_length=150, min_length=30, do_sample=False)

# Function to convert audio to text
def audio_to_text(video_audio):
    recognizer = sr.Recognizer()
    with sr.AudioFile(video_audio) as source:
        audio = recognizer.record(source)
    try:
        text = recognizer.recognize_google(audio)
        return text
    except sr.UnknownValueError:
        return "Sorry, the audio could not be understood."

# Function to track the quiz result
def track_quiz_result(user_id, video_id, correct, total):
    st.write(f"You got {correct} out of {total} correct!")

st.title("Enhanced YouTube Study Space")

# Input field for YouTube video link and User ID
video_url = st.text_input("Enter YouTube video URL")
user_id = st.text_input("Enter your User ID")

if video_url and user_id:
    # Fetch video details using yt-dlp
    video_title, video_length = get_video_details(video_url)
    st.write(f"Video Title: {video_title}")
    st.write(f"Video Length: {video_length // 60} minutes")

    # Retrieve the saved progress
    progress, notes = get_progress(video_url, user_id)
    st.write(f"Last watched at: {progress // 60} minutes")

    # Video player
    st.video(video_url, start_time=progress)

    # Notes section
    user_notes = st.text_area("Your Notes", notes)

    # Save progress and notes
    if st.button("Save Progress"):
        current_time = st.slider("Set your current time (in seconds):", 0, video_length, value=progress)
        save_progress(video_url, user_id, current_time, user_notes)
        st.success("Progress and notes saved!")

    # Analyze sentiment of notes
    if st.button("Analyze Sentiment"):
        sentiment = analyze_sentiment(user_notes)
        st.write(f"Sentiment: {sentiment['label']} (Score: {sentiment['score']:.2f})")

    # Summarization of notes
    if st.button("Summarize Notes"):
        summary = summarize_video_transcript(user_notes)
        st.write("Summary:", summary[0]['summary_text'])

    # To-Do List
    st.subheader("To-Do List")
    task_input = st.text_input("Add a task")
    if st.button("Add Task"):
        add_task(user_id, task_input)
        st.success("Task added!")

    tasks = get_tasks(user_id)
    for task, status in tasks:
        st.write(f"Task: {task} | Status: {status}")

    # Reminders
    st.subheader("Set Reminder")
    reminder_message = st.text_input("Reminder Message")
    reminder_time = st.time_input("Set Reminder Time", datetime.now().time())

    if st.button("Set Reminder"):
        reminder_time_str = reminder_time.strftime("%H:%M")
        set_reminder(user_id, reminder_time_str, reminder_message)
        st.success("Reminder set!")

    reminders = get_reminders(user_id)
    st.write("Your Reminders:")
    for reminder_time, message in reminders:
        st.write(f"Reminder at {reminder_time}: {message}")

    # Quizzes
    st.subheader("Quiz Time!")
    quiz_questions = {
        "What is the main topic of this video?": ["Option 1", "Option 2", "Option 3", "Option 4"],
        "What year was the YouTube platform created?": ["2002", "2004", "2005", "2006"]
    }

    total = len(quiz_questions)
    correct = 0
    for question, options in quiz_questions.items():
        st.write(question)
        user_answer = st.radio("Select an answer:", options)
        if st.button("Submit Answer"):
            if user_answer == "Option 3":  # Dummy correct answer
                correct += 1

    if st.button("Submit Quiz"):
        track_quiz_result(user_id, video_url, correct, total)

# Close database connection when done
conn.close()
