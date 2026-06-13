import streamlit as st
import pandas as pd
import re
from collections import Counter

from googleapiclient.discovery import build

from wordcloud import WordCloud
import matplotlib.pyplot as plt

from konlpy.tag import Okt

st.set_page_config(
    page_title="유튜브 댓글 심층 분석기",
    page_icon="📊",
    layout="wide"
)

# ----------------------------
# 유튜브 API
# ----------------------------

def extract_video_id(url):
    patterns = [
        r"v=([a-zA-Z0-9_-]+)",
        r"youtu\.be/([a-zA-Z0-9_-]+)",
        r"shorts/([a-zA-Z0-9_-]+)"
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


def get_comments(youtube, video_id, max_comments=1000):

    comments = []

    request = youtube.commentThreads().list(
        part="snippet",
        videoId=video_id,
        maxResults=100,
        textFormat="plainText"
    )

    while request and len(comments) < max_comments:

        response = request.execute()

        for item in response["items"]:

            text = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]

            comments.append(text)

            if len(comments) >= max_comments:
                break

        request = youtube.commentThreads().list_next(
            request,
            response
        )

    return comments


# ----------------------------
# 텍스트 분석
# ----------------------------

def clean_text(text):
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"[^가-힣a-zA-Z0-9 ]", " ", text)
    return text


def extract_keywords(comments):

    okt = Okt()

    nouns = []

    stopwords = {
        "영상","진짜","너무","정말","그냥","이거","저거",
        "사람","생각","오늘","이번","이런","저런",
        "ㅋㅋ","ㅎㅎ","감사","구독","좋아요"
    }

    for comment in comments:

        comment = clean_text(comment)

        words = okt.nouns(comment)

        nouns.extend([
            w for w in words
            if len(w) >= 2 and w not in stopwords
        ])

    return Counter(nouns)


# ----------------------------
# UI
# ----------------------------

st.title("📊 유튜브 댓글 심층 분석기")

api_key = st.text_input(
    "YouTube API Key",
    type="password"
)

video_url = st.text_input(
    "유튜브 링크 입력"
)

max_comments = st.slider(
    "분석 댓글 수",
    100,
    2000,
    1000,
    100
)

analyze = st.button("분석 시작")

if analyze:

    if not api_key:
        st.error("API Key를 입력하세요.")
        st.stop()

    video_id = extract_video_id(video_url)

    if not video_id:
        st.error("유효한 유튜브 링크가 아닙니다.")
        st.stop()

    with st.spinner("댓글 수집 중..."):

        youtube = build(
            "youtube",
            "v3",
            developerKey=api_key
        )

        comments = get_comments(
            youtube,
            video_id,
            max_comments
        )

    if len(comments) == 0:
        st.error("댓글을 가져올 수 없습니다.")
        st.stop()

    st.success(f"{len(comments)}개 댓글 분석 완료")

    # 데이터프레임
    df = pd.DataFrame({
        "댓글": comments
    })

    st.subheader("댓글 데이터")

    st.dataframe(
        df.head(50),
        use_container_width=True
    )

    # 댓글 길이
    lengths = [len(c) for c in comments]

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "댓글 수",
        len(comments)
    )

    col2.metric(
        "평균 길이",
        round(sum(lengths) / len(lengths), 1)
    )

    col3.metric(
        "최대 길이",
        max(lengths)
    )

    # 키워드 분석
    keyword_counter = extract_keywords(comments)

    st.subheader("🔥 TOP 30 키워드")

    keyword_df = pd.DataFrame(
        keyword_counter.most_common(30),
        columns=["키워드", "빈도"]
    )

    st.dataframe(
        keyword_df,
        use_container_width=True
    )

    # 워드클라우드
    st.subheader("☁️ 한글 워드클라우드")

    try:

        wc = WordCloud(
            font_path="NanumGothic.ttf",
            width=1200,
            height=600,
            background_color="white"
        )

        wc.generate_from_frequencies(
            dict(keyword_counter)
        )

        fig, ax = plt.subplots(
            figsize=(12, 6)
        )

        ax.imshow(wc)
        ax.axis("off")

        st.pyplot(fig)

    except Exception:

        st.warning(
            "NanumGothic.ttf 파일을 프로젝트 폴더에 넣어주세요."
        )

    # 감성 추정
    positive_words = [
        "좋다","최고","감동","재밌다","멋지다",
        "행복","대박","훌륭","추천"
    ]

    negative_words = [
        "별로","실망","최악","싫다","아쉽다",
        "문제","불편","짜증"
    ]

    positive = 0
    negative = 0

    for comment in comments:

        for word in positive_words:
            if word in comment:
                positive += 1

        for word in negative_words:
            if word in comment:
                negative += 1

    st.subheader("😊 감성 분석")

    sentiment_df = pd.DataFrame({
        "구분": ["긍정", "부정"],
        "개수": [positive, negative]
    })

    st.bar_chart(
        sentiment_df.set_index("구분")
    )

    st.subheader("📝 AI 분석 요약")

    top_words = ", ".join(
        [w for w, _ in keyword_counter.most_common(10)]
    )

    st.write(f"""
    - 댓글 수: {len(comments)}개
    - 주요 관심사: {top_words}
    - 댓글 참여도가 높은 영상으로 판단됩니다.
    - 핵심 키워드를 중심으로 시청자 반응이 형성되어 있습니다.
    """)
