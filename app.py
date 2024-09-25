from flask import Flask, render_template, request, redirect, url_for
import re
from collections import defaultdict
from datetime import datetime
import matplotlib.pyplot as plt
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'

def detect_os_type(lines):
    for line in lines:
        if re.match(r"\d{2}\.\d{2}\.\d{2}, \d{2}:\d{2} - .+:", line):
            return 'android'
        elif re.match(r"👦\d{2}\.\d{2}\.\d{2}, \d{2}:\d{2}:\d{2}👦 .+:", line):
            return 'ios'
    return None

def extract_chat_statistics(chat_log):
    lines = chat_log.splitlines()
    os_type = detect_os_type(lines)
    if os_type is None:
        return None, "Fehler: Betriebssystemtyp konnte nicht erkannt werden."
    
    message_count = defaultdict(int)
    letter_count = defaultdict(int)
    word_count = defaultdict(int)
    timestamps = []
    participants = set()
    messages_per_day = defaultdict(int)
    response_times = defaultdict(list)
    
    if os_type == "android":
        regex_message = r"(.*) - ([^:]+): (.+)"
        media_marker = '<Medien ausgeschlossen>'
    elif os_type == "ios":
        regex_message = r"👦(.*)👦 ([^:]+): (.+)"
        media_marker = 'Audio weggelassen'
    
    previous_message_time = None
    previous_sender = None
    for line in lines:
        if media_marker in line:
            continue
        match = re.match(regex_message, line)
        if match:
            timestamp_str = match.group(1).strip()
            sender = match.group(2).strip()
            message = match.group(3).strip()
            participants.add(sender)
            if os_type == "android":
                timestamp_format = "%d.%m.%y, %H:%M"
            elif os_type == "ios":
                timestamp_format = "%d.%m.%y, %H:%M:%S"
            try:
                timestamp = datetime.strptime(timestamp_str, timestamp_format)
            except ValueError:
                continue
            timestamps.append(timestamp)
            messages_per_day[timestamp.date()] += 1
            message_count[sender] += 1
            letter_count[sender] += len(message)
            word_count[sender] += len(message.split())
            if previous_message_time and previous_sender != sender:
                response_time = (timestamp - previous_message_time).total_seconds() / 60
                response_times[sender].append(response_time)
            previous_message_time = timestamp
            previous_sender = sender
    
    if not message_count:
        return None, "Fehler: Es wurden keine Nachrichten gefunden."
    
    total_messages = sum(message_count.values())
    total_letters = sum(letter_count.values())
    total_words = sum(word_count.values())
    
    result = {
        'total_messages': total_messages,
        'total_letters': total_letters,
        'total_words': total_words,
        'first_message_date': min(timestamps).date(),
        'last_message_date': max(timestamps).date(),
        'participants': {p: {
            'messages_sent': message_count[p],
            'letters_sent': letter_count[p],
            'words_sent': word_count[p],
            'avg_message_length': letter_count[p] / message_count[p] if message_count[p] else 0,
            'avg_word_length': word_count[p] / message_count[p] if message_count[p] else 0,
            'avg_response_time': sum(response_times[p]) / len(response_times[p]) if response_times[p] else None,
        } for p in participants},
        'most_active_person': max(message_count, key=message_count.get),
        'most_active_day': max(messages_per_day, key=messages_per_day.get),
        'messages_per_day': messages_per_day,
    }
    
    return result, None

def plot_messages_per_day(messages_per_day):
    dates = list(messages_per_day.keys())
    counts = list(messages_per_day.values())
    plt.figure(figsize=(10, 5))
    plt.plot(dates, counts, marker="o", color="#3498db")  # Nutze eine schöne Akzentfarbe
    plt.title("Nachrichten pro Tag")
    plt.xlabel("Datum")
    plt.ylabel("Anzahl der Nachrichten")
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    file_path = os.path.join('static', 'messages_per_day.png')
    plt.savefig(file_path)
    return file_path


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if 'chat_file' not in request.files:
            return redirect(request.url)
        file = request.files['chat_file']
        if file.filename == '':
            return redirect(request.url)
        if file:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            with open(file_path, 'r', encoding='utf-8') as f:
                chat_log = f.read()
            stats, error = extract_chat_statistics(chat_log)
            if error:
                return render_template('index.html', error=error)
            plot_path = plot_messages_per_day(stats['messages_per_day'])
            return render_template('result.html', stats=stats, plot_url=plot_path)
    return render_template('index.html')

if __name__ == "__main__":
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)
