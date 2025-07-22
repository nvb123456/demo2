import streamlit as st
import requests
import zipfile
import io
import json
import re

# Tải từ điển phát âm nếu có
def load_pronunciation_dict():
    try:
        with open("pronunciation_dict.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

# Áp dụng từ điển phát âm vào văn bản
def apply_pronunciation_dict(text, dictionary):
    for word, replacement in dictionary.items():
        text = re.sub(rf"(?<!\w){re.escape(word)}(?!\w)", replacement, text)
    return text

# Làm sạch và ngắt câu dài cho voice-over
def clean_and_split_line(line):
    line = line.strip()
    if not line.endswith((".", "!", "?")):
        line += "."
    line = re.sub(r"\s+", " ", line)
    words = line.split()
    if len(words) > 20:
        midpoint = len(words) // 2
        words.insert(midpoint, ",")
        line = " ".join(words)
    return line

# Quản lý API Key
API_KEYS_FILE = "api_keys.json"
MAX_WORDS_PER_KEY = 10000

def load_keys():
    with open(API_KEYS_FILE, "r") as f:
        return json.load(f)

def save_keys(keys):
    with open(API_KEYS_FILE, "w") as f:
        json.dump(keys, f, indent=2)

def select_available_key():
    keys = load_keys()
    for i, key in enumerate(keys):
        if key["used"] < MAX_WORDS_PER_KEY:
            return key["key"], i
    raise Exception("❌ Hết lượt API key.")

def increment_key_usage(index, words):
    keys = load_keys()
    keys[index]["used"] += words
    save_keys(keys)

def extract_lines_from_file(uploaded_file):
    ext = uploaded_file.name.lower().split('.')[-1]
    content = uploaded_file.read().decode("utf-8", errors="ignore")
    if ext == "txt":
        return [line.strip() for line in content.strip().split("\n") if line.strip()]
    elif ext == "srt":
        lines = []
        for line in content.splitlines():
            line = line.strip()
            if line and not line.isdigit() and "-->" not in line:
                lines.append(line)
        return lines
    return []

# UI Streamlit
st.set_page_config(page_title="🎙️ TTS Voice-over Flash", layout="centered")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');
html, body, [class*="css"] {
    font-family: 'Poppins', sans-serif;
    background-color: #f4f6f9;
}
.container {
    background-color: white;
    padding: 30px;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    margin-top: 30px;
}
.stButton button {
    background-color: #007BFF;
    color: white;
    border-radius: 8px;
    font-size: 16px;
}
.stDownloadButton button {
    border: 2px solid #007BFF;
    background-color: white;
    color: #007BFF;
    border-radius: 8px;
    font-size: 15px;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="container">', unsafe_allow_html=True)
st.title("🎧 Text-to-Speech: Giọng Việt voice-over")
st.markdown("💬 Nhập hoặc tải file `.txt` / `.srt`. App sẽ đọc giọng tự nhiên bằng ElevenLabs Flash v2.5")

uploaded_file = st.file_uploader("📂 Tải file văn bản", type=["txt", "srt"])
text_input = st.text_area("✍️ Nhập văn bản (mỗi dòng = 1 file):", height=200)

# Giọng đọc
voice_options = {
    "👩 Bella (Nữ)": "21m00Tcm4TlvDq8ikWAM",
    "👨 Thomas (Nam)": "TxGEqnHWrfWFTfGW9XjX",
    "🧑 Bradford (Anh)": "EXAVITQu4vr4xnSDxMaL",
    "🎤 Tuỳ chỉnh 1": "DvG3I1kDzdBY3u4EzYh6",
    "🎧 Nữ mềm mại": "7uqEZLMssORVvKMLEUi4"
}
voice_name = st.selectbox("🗣️ Chọn giọng", list(voice_options.keys()))
voice_id = voice_options[voice_name]

# Load từ điển
pronunciation_dict = load_pronunciation_dict()

if st.button("▶️ Tạo giọng nói"):
    lines = extract_lines_from_file(uploaded_file) if uploaded_file else text_input.strip().split("\n")
    lines = [l for l in lines if l.strip()]
    if not lines:
        st.warning("⚠️ Không có nội dung.")
    else:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for idx, line in enumerate(lines, 1):
                line = clean_and_split_line(line)
                line = apply_pronunciation_dict(line, pronunciation_dict)
                word_count = len(line.strip().split())

                try:
                    api_key, key_index = select_available_key()
                except Exception as e:
                    st.error(str(e))
                    break

                headers = {
                    "xi-api-key": api_key,
                    "Content-Type": "application/json"
                }

                payload = {
                    "text": line,
                    "model_id": "eleven_flash_v2_5",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 1.0,
                        "speed": 1.0
                    }
                }

                response = requests.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                    headers=headers,
                    json=payload
                )

                if response.status_code == 200:
                    filename = f"{idx}.mp3"
                    zip_file.writestr(filename, response.content)
                    st.audio(response.content, format="audio/mp3")
                    st.success(f"✅ Đã tạo dòng {idx}")
                    increment_key_usage(key_index, word_count)
                else:
                    st.error(f"❌ Lỗi dòng {idx}: {response.status_code} – {response.text}")
                    break

        st.download_button("⬇️ Tải tất cả MP3", data=zip_buffer.getvalue(), file_name="tts_output.zip", mime="application/zip")

st.markdown('</div>', unsafe_allow_html=True)
st.markdown("""<footer style='text-align: center; margin-top: 2em;'>👨‍💻 Phát triển bởi <strong>Vinh Bảo</strong> – 2025</footer>""", unsafe_allow_html=True)
