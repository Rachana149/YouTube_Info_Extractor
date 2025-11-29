import streamlit as st
from googleapiclient.discovery import build
import pandas as pd
import numpy as np
import isodate
import re
from datetime import timedelta
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
st.set_page_config(page_title="YouTube Analyzer", layout="wide")
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #1a0000 0%, #8b0000 50%, #000000 100%);
        background-attachment: fixed;
    }

    h1, h2, h3, label {
        color: white !important;
        font-weight: 600;
    }

    section[data-testid="stSidebar"] {
        background: rgba(0,0,0,0.2);
        backdrop-filter: blur(6px);
    }

    </style>
""", unsafe_allow_html=True)
if "start_dashboard" not in st.session_state:
    st.session_state.start_dashboard = False

if "api_key" not in st.session_state:
    st.session_state.api_key = ""

if "channel_url" not in st.session_state:
    st.session_state.channel_url = ""
logo_path = "C:/Users/Rachana Mahato/OneDrive/Documents/project/Youtube_logo3.png"
if not st.session_state.start_dashboard:

    col_left, col_right = st.columns([1.2, 1])
    with col_left:
        st.image(logo_path, width=520)
    with col_right:
        st.markdown("<h1 style='font-size:55px; line-height:55px;'>YouTube<br>Info Extractor</h1>", unsafe_allow_html=True)

        api_key = st.text_input("🔑 Enter API Key", type="password")
        channel_url = st.text_input("📺 Enter Channel URL or Channel ID")

        start_btn = st.button("🚀 Fetch Data")

    if start_btn:
        if not api_key:
            st.error("⚠ Please enter API Key.")
        elif not channel_url:
            st.error("⚠ Please enter Channel URL.")
        else:
            st.session_state.api_key = api_key
            st.session_state.channel_url = channel_url
            st.session_state.start_dashboard = True
            st.rerun()
def extract_channel_id(url, youtube=None):
    try:
        url = url.strip()

        if "/channel/" in url:
            return url.split("/channel/")[-1].split("?")[0]

        if "/@" in url and youtube:
            username = re.findall(r"/@([A-Za-z0-9_-]+)", url)
            if username:
                res = youtube.search().list(
                    part="snippet", q=username[0], type="channel", maxResults=1
                ).execute()
                if res.get("items"):
                    return res["items"][0]["snippet"]["channelId"]

        if re.match(r"^[A-Za-z0-9_-]{24}$", url):
            return url

        return None
    except:
        return None


def get_uploads_playlist_id(channel_id, youtube):
    res = youtube.channels().list(
        part="contentDetails,snippet,statistics",
        id=channel_id
    ).execute()

    if not res.get("items"):
        return None, None, None, None

    info = res["items"][0]

    playlist_id = info["contentDetails"]["relatedPlaylists"]["uploads"]
    channel_name = info["snippet"]["title"]
    stats = info["statistics"]

    thumbnail_info = info["snippet"]["thumbnails"]
    channel_logo = thumbnail_info.get("high", thumbnail_info.get("default"))["url"]

    return playlist_id, channel_name, stats, channel_logo


def get_videos_from_playlist(playlist_id, youtube, max_results=100):
    videos = []
    next_page = None

    while len(videos) < max_results:
        res = youtube.playlistItems().list(
            part="contentDetails",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page
        ).execute()

        for item in res.get("items", []):
            videos.append(item["contentDetails"]["videoId"])

        next_page = res.get("nextPageToken")
        if not next_page:
            break

    return videos


def get_video_stats(video_ids, youtube):
    data = []

    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i+50]

        res = youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=",".join(chunk)
        ).execute()

        for item in res["items"]:

            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})

            view_count = int(stats.get("viewCount", 0))
            like_count = int(stats.get("likeCount", 0))
            comment_count = int(stats.get("commentCount", 0))

            engagement = round((like_count + comment_count) / view_count * 100, 3) if view_count > 0 else 0

            duration_iso = item["contentDetails"].get("duration", "PT0S")
            duration_td = isodate.parse_duration(duration_iso)
            duration_minutes = round(duration_td.total_seconds() / 60, 2)

            thumbnail_url = snippet["thumbnails"].get("high", snippet["thumbnails"].get("default"))["url"]

            data.append({
                "VideoID": item["id"],
                "Title": snippet.get("title", ""),
                "Published": snippet.get("publishedAt", "").split("T")[0],
                "Views": view_count,
                "Likes": like_count,
                "Comments": comment_count,
                "Engagement (%)": engagement,
                "Duration_minutes": duration_minutes,
                "Thumbnail": thumbnail_url,
                "URL": f"https://youtu.be/{item['id']}"
            })

    return data
if st.session_state.start_dashboard:

    api_key = st.session_state.api_key
    channel_url = st.session_state.channel_url

    youtube = build("youtube", "v3", developerKey=api_key)

    channel_id = extract_channel_id(channel_url, youtube)
    playlist_id, channel_name, stats, channel_logo = get_uploads_playlist_id(channel_id, youtube)

    st.title(f"📺 {channel_name}")

   
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Videos", stats.get("videoCount", "0"))
    c2.metric("Total Views", stats.get("viewCount", "0"))
    c3.metric("Subscribers", stats.get("subscriberCount", "Hidden"))

   
    video_ids = get_videos_from_playlist(playlist_id, youtube, 120)
    df = pd.DataFrame(get_video_stats(video_ids, youtube))

  
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📄 Video Table", "📈 Charts", "🏆 Top Videos", "⬇ Download", "🖼 Gallery"]
    )

    with tab1:
        st.subheader("All Videos")
        st.dataframe(df, use_container_width=True)

    with tab2:
        st.subheader("Views vs Likes Trend")
        st.line_chart(df[["Views", "Likes"]])

    with tab3:
        st.subheader("Top 5 Videos")
        st.dataframe(df.sort_values(by="Views", ascending=False).head(5))

    with tab4:
        st.subheader("Download CSV")
        st.download_button("Download CSV", df.to_csv(index=False), "youtube_data.csv")

    with tab5:
        st.subheader("Thumbnail Gallery")
        cols = st.columns(4)
        for i, row in df.iterrows():
            with cols[i % 4]:
                st.image(row["Thumbnail"], use_container_width=True)
                st.caption(row["Title"][:40] + "...")
