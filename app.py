# app.py
import os
import re
import io
import requests
import streamlit as st
from bs4 import BeautifulSoup
from base64 import b64encode

st.title("Spotify 歌曲封面下载器")
st.write("粘贴 Spotify 分享链接（open.spotify.com 或 spotify:track: 或短链）并点击下载。")

spotify_url = st.text_input("Spotify 歌曲分享链接或 URI", "")

def try_oembed(url):
    try:
        r = requests.get("https://open.spotify.com/oembed", params={"url": url}, timeout=8)
        if r.status_code == 200:
            j = r.json()
            thumb = j.get("thumbnail_url") or j.get("thumbnail_url_https")
            return thumb
    except Exception:
        pass
    return None

def get_spotify_token(client_id, client_secret):
    token_url = "https://accounts.spotify.com/api/token"
    r = requests.post(token_url, data={"grant_type": "client_credentials"},
                      auth=(client_id, client_secret), timeout=8)
    r.raise_for_status()
    return r.json().get("access_token")

def get_cover_from_api(track_id, token):
    url = f"https://api.spotify.com/v1/tracks/{track_id}"
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=8)
    if r.status_code == 200:
        j = r.json()
        images = j.get("album", {}).get("images", [])
        if images:
            return images[0].get("url")
    return None

def scrape_og_image(url):
    try:
        r = requests.get(url, timeout=8, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            return og.get("content")
    except Exception:
        pass
    return None

def extract_track_id(url_or_uri):
    # handle spotify:track:ID
    m = re.search(r"spotify:track:([A-Za-z0-9]+)", url_or_uri)
    if m:
        return m.group(1)
    # handle open.spotify.com/track/ID
    m = re.search(r"open\.spotify\.com/(track|embed/track)/([A-Za-z0-9]+)", url_or_uri)
    if m:
        return m.group(2)
    # handle short links or URLs with ?si=...
    m = re.search(r"/track/([A-Za-z0-9]+)", url_or_uri)
    if m:
        return m.group(1)
    return None

def download_image_to_bytes(url):
    r = requests.get(url, timeout=12, stream=True)
    r.raise_for_status()
    content_type = r.headers.get("Content-Type", "")
    # 自动推断扩展名
    if "jpeg" in content_type:
        ext = "jpg"
    elif "png" in content_type:
        ext = "png"
    elif "webp" in content_type:
        ext = "webp"
    else:
        ext = "jpg"
    return r.content, ext


if spotify_url:
    st.info("开始尝试获取封面...")
    cover_url = try_oembed(spotify_url)
    if cover_url:
        st.success("通过 oEmbed 找到封面（最快方式）。")
    else:
        track_id = extract_track_id(spotify_url)
        cover_url = None
        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        if track_id and client_id and client_secret:
            try:
                token = get_spotify_token(client_id, client_secret)
                cover_url = get_cover_from_api(track_id, token)
                if cover_url:
                    st.success("通过 Spotify Web API 获取到封面。")
            except Exception as e:
                st.warning(f"使用 Spotify API 失败: {e}")
        if not cover_url and track_id:
            # try scraping the public page
            public_url = f"https://open.spotify.com/track/{track_id}"
            cover_url = scrape_og_image(public_url)
            if cover_url:
                st.success("通过抓取页面头信息 (og:image) 获取到封面。")
    if not cover_url:
        st.error("无法获取封面。请检查链接或配置 SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET。")
    else:
        try:
            img_bytes, ext = download_image_to_bytes(cover_url)
            st.image(img_bytes, caption="封面预览", use_column_width=True)
            filename = f"spotify_cover.{ext}"
            st.download_button("下载封面", data=img_bytes, file_name=filename, mime=f"image/{ext}")
            st.write("封面来源 URL：", cover_url)
        except Exception as e:
            st.error(f"下载或显示图片失败: {e}")

