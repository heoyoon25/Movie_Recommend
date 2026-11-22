"""CineType: 영화 취향 MBTI | GitHub + Streamlit Community Cloud 배포용.

설치: pip install -r requirements.txt
실행: streamlit run app.py
영화 포스터는 별도 키 없이 Wikipedia의 공개 썸네일을 조회합니다.
이미지 조회에 실패해도 영화 설명과 테스트는 정상 동작합니다.
"""

import hmac
from collections import Counter
from io import BytesIO
from pathlib import Path
from urllib.parse import quote, urlencode

import requests
import streamlit as st
from PIL import Image, ImageDraw, ImageFont


st.set_page_config(
    page_title="CineType | 나의 영화 취향 MBTI",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ──────────────────────────── 접속 비밀번호 확인 ────────────────────────────
# 비밀번호는 GitHub에 올리지 말고 Streamlit Community Cloud > App settings > Secrets에
# APP_PASSWORD = "사용자가_정한_비밀번호" 형식으로 등록해야 합니다.
def require_password():
    try:
        expected = st.secrets["APP_PASSWORD"]
    except (FileNotFoundError, KeyError):
        st.error("접속 비밀번호 설정이 누락되었습니다.")
        st.info(
            "Streamlit Community Cloud의 앱 설정 > Secrets에 "
            "APP_PASSWORD를 등록하세요. 이 값은 GitHub에 업로드하지 마세요."
        )
        st.stop()

    if not isinstance(expected, str) or not expected.strip():
        st.error("APP_PASSWORD는 비어 있지 않은 문자열이어야 합니다.")
        st.stop()

    if st.session_state.get("_cinetype_authenticated", False):
        return

    st.markdown("""
    <style>
      [data-testid="stAppViewContainer"] {
        background: radial-gradient(circle at 85% 5%, #fff0f5 0, transparent 38%),
                    radial-gradient(circle at 15% 0, #eef0ff 0, transparent 42%), #fafbff;
      }
      .block-container {max-width: 900px; padding-top: 9vh;}
      .login-heading {text-align:center;font-size:2.45rem;font-weight:900;
                      color:#312a67;letter-spacing:-.04em;margin:0 0 .5rem;}
      .login-description {text-align:center;color:#706c8b;line-height:1.8;margin-bottom:2rem;}
    </style>
    """, unsafe_allow_html=True)
    st.markdown('<div class="login-heading">🎬 CineType</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="login-description">나의 영화 취향은 무엇일까요?<br>'
        '테스트를 시작하려면 비밀번호를 입력해 주세요.</div>',
        unsafe_allow_html=True,
    )
    col_left, col_center, col_right = st.columns([1, 1.4, 1])
    with col_center:
        with st.form("cinetype_login_form", clear_on_submit=False):
            supplied = st.text_input("접속 비밀번호", type="password", placeholder="비밀번호 입력")
            submitted = st.form_submit_button("테스트 입장하기 →", type="primary", use_container_width=True)
        if submitted:
            if hmac.compare_digest(supplied, expected):
                st.session_state["_cinetype_authenticated"] = True
                st.rerun()
            else:
                st.error("비밀번호가 올바르지 않습니다.")
    st.stop()


require_password()


# ──────────────────────────── 1. 질문과 결과 유형 ────────────────────────────
# 3가지 대립 성향을 각 4번씩 질문합니다. 2:2 동점이면 해당 축의 첫 답으로 판정합니다.
QUESTIONS = [
    {"axis": "GA", "text": "영화를 보고 난 뒤 가장 오래 기억에 남는 것은?", "options": [("인물의 감정과 관계", "G"), ("복선과 이야기 구조", "A")]},
    {"axis": "TH", "text": "더 집중해서 보게 되는 장면은?", "options": [("갈등이 폭발하는 긴박한 장면", "T"), ("편안하고 잔잔한 일상 장면", "H")]},
    {"axis": "NF", "text": "처음 보는 영화 중 더 끌리는 것은?", "options": [("독특한 세계관과 참신한 소재", "N"), ("친숙한 소재와 익숙한 분위기", "F")]},
    {"axis": "GA", "text": "좋은 영화를 고를 때 더 중요하게 보는 것은?", "options": [("이야기의 짜임새", "A"), ("인물에게 감정이입할 수 있는지", "G")]},
    {"axis": "TH", "text": "오늘 밤 한 편을 고른다면?", "options": [("천천히 흘러가는 편안한 영화", "H"), ("빠르게 전개되는 긴장감 있는 영화", "T")]},
    {"axis": "NF", "text": "더 선호하는 영화의 전개는?", "options": [("예상 가능한 흐름 속의 안정적인 재미", "F"), ("예측하기 어려운 새로운 전개", "N")]},
    {"axis": "GA", "text": "영화의 결말에서 더 중요하게 생각하는 것은?", "options": [("오랫동안 남는 감정적 여운", "G"), ("논리적으로 잘 맞아떨어지는 마무리", "A")]},
    {"axis": "TH", "text": "더 좋아하는 영화 음악은?", "options": [("박진감 넘치고 긴박한 음악", "T"), ("차분하고 잔잔한 음악", "H")]},
    {"axis": "NF", "text": "새 영화를 발견할 때 더 즐거운 순간은?", "options": [("처음 접하는 장르 조합을 찾았을 때", "N"), ("평소 좋아하는 장르의 새 작품을 찾았을 때", "F")]},
    {"axis": "GA", "text": "친구에게 영화를 추천할 때 주로 말하는 것은?", "options": [("연출과 이야기의 완성도", "A"), ("등장인물의 감정과 관계", "G")]},
    {"axis": "TH", "text": "영화를 보고 느끼고 싶은 기분은?", "options": [("마음이 편안해지고 따뜻해지는 기분", "H"), ("손에 땀을 쥐는 짜릿한 기분", "T")]},
    {"axis": "NF", "text": "아무 정보 없이 영화를 골라야 한다면?", "options": [("익숙하고 믿을 만한 이야기 방식", "F"), ("실험적이고 색다른 이야기 방식", "N")]},
]

# 영화: (제목, 개봉 연도, 짧은 줄거리, 영어 위키백과 문서명)
# 각 유형의 기존 추천 영화 2편은 유지하고, 3편씩 추가했습니다.
MOVIES = {
    "GTN": [
        ("에브리씽 에브리웨어 올 앳 원스", 2022, "세탁소를 운영하던 에블린은 여러 평행우주의 자신과 연결되면서 가족과 세계의 운명을 건 모험에 휘말립니다.", "Everything_Everywhere_All_at_Once"),
        ("옥자", 2017, "산골 소녀 미자는 다국적 기업에 빼앗긴 특별한 동물 옥자를 되찾기 위해 거대한 도시로 향합니다.", "Okja"),
        ("스파이더맨: 뉴 유니버스", 2018, "스파이더맨의 능력을 얻게 된 마일스가 다른 차원에서 온 영웅들과 힘을 합쳐 위기를 막아냅니다.", "Spider-Man:_Into_the_Spider-Verse"),
        ("인터스텔라", 2014, "인류가 살아갈 새 터전을 찾기 위해 우주로 떠난 탐사대와 지구에 남은 가족의 이야기가 펼쳐집니다.", "Interstellar_(film)"),
        ("셰이프 오브 워터: 사랑의 모양", 2017, "냉전 시대 비밀 연구소의 청소부 엘라이자는 수조 속 신비로운 존재와 특별한 유대감을 쌓습니다.", "The_Shape_of_Water"),
    ],
    "GTF": [
        ("부산행", 2016, "정체불명의 감염 사태가 일어난 열차 안에서 승객들이 부산에 도착하기 위해 사투를 벌입니다.", "Train_to_Busan"),
        ("타이타닉", 1997, "호화 여객선에서 만난 잭과 로즈는 신분 차이를 넘어 사랑에 빠지지만 거대한 재난을 마주합니다.", "Titanic_(1997_film)"),
        ("더 임파서블", 2012, "태국에서 휴가를 보내던 한 가족이 대형 쓰나미에 휩쓸린 뒤 서로를 찾아 헤맵니다.", "The_Impossible_(2012_film)"),
        ("터널", 2016, "갑작스러운 터널 붕괴로 차 안에 갇힌 남자와 그를 구하기 위한 구조대의 시간이 교차합니다.", "Tunnel_(2016_film)"),
        ("그래비티", 2013, "우주 임무 도중 사고로 고립된 두 우주비행사가 지구로 돌아갈 방법을 찾아 나섭니다.", "Gravity_(2013_film)"),
    ],
    "GHN": [
        ("소울", 2020, "재즈 음악가를 꿈꾸던 조는 뜻밖의 사고로 영혼의 세계에 들어가 삶의 의미를 다시 생각합니다.", "Soul_(2020_film)"),
        ("월터의 상상은 현실이 된다", 2013, "반복되는 일상을 살던 월터가 사라진 사진 한 장을 찾아 현실 속 모험을 시작합니다.", "The_Secret_Life_of_Walter_Mitty_(2013_film)"),
        ("코코", 2017, "음악을 사랑하는 미겔은 죽은 자들의 세계에서 가족의 숨겨진 이야기를 발견합니다.", "Coco_(2017_film)"),
        ("센과 치히로의 행방불명", 2001, "낯선 신들의 세계에 들어간 치히로가 부모님을 구하기 위해 신비한 목욕탕에서 일합니다.", "Spirited_Away"),
        ("업", 2009, "풍선을 달아 집을 띄운 노인 칼과 소년 러셀이 뜻밖의 동행을 하며 새로운 우정을 만납니다.", "Up_(2009_film)"),
    ],
    "GHF": [
        ("리틀 포레스트", 2018, "도시 생활에 지친 혜원이 고향으로 돌아와 사계절 음식을 만들며 자신의 삶을 돌아봅니다.", "Little_Forest_(2018_film)"),
        ("어바웃 타임", 2013, "시간을 되돌릴 수 있는 능력을 알게 된 팀이 사랑과 가족의 평범한 순간들을 새롭게 바라봅니다.", "About_Time_(2013_film)"),
        ("패딩턴 2", 2017, "런던에서 가족과 지내는 곰 패딩턴이 특별한 선물을 준비하다 누명을 쓰고 사건에 휘말립니다.", "Paddington_2"),
        ("원더", 2017, "남들과 다른 외모를 가진 소년 어기가 처음 학교에 다니며 우정과 용기를 배워갑니다.", "Wonder_(film)"),
        ("비긴 어게인", 2013, "상처받은 싱어송라이터와 음악 프로듀서가 뉴욕 거리에서 새로운 음악을 함께 만들어갑니다.", "Begin_Again_(film)"),
    ],
    "ATN": [
        ("인셉션", 2010, "타인의 꿈에 들어가 비밀을 훔치는 전문가 코브가 꿈속에 생각을 심는 위험한 임무를 맡습니다.", "Inception"),
        ("테넷", 2020, "시간이 거꾸로 흐르는 기술을 발견한 요원이 미래를 위협하는 음모를 막으려 합니다.", "Tenet_(film)"),
        ("매트릭스", 1999, "해커 네오는 자신이 믿었던 현실이 거대한 가상 세계일 수 있다는 사실을 알게 됩니다.", "The_Matrix"),
        ("엣지 오브 투모로우", 2014, "외계 생명체와의 전투에서 죽을 때마다 같은 하루를 반복하는 군인이 승리의 실마리를 찾습니다.", "Edge_of_Tomorrow"),
        ("프레스티지", 2006, "19세기 런던의 두 마술사가 서로를 뛰어넘기 위해 위험한 경쟁에 집착합니다.", "The_Prestige_(film)"),
    ],
    "ATF": [
        ("나이브스 아웃", 2019, "유명 추리소설 작가의 의문스러운 죽음 뒤 탐정 블랑이 복잡한 가족 관계 속 진실을 추적합니다.", "Knives_Out"),
        ("셔터 아일랜드", 2010, "실종된 환자를 조사하러 외딴 정신병원에 도착한 연방 보안관이 수상한 정황을 발견합니다.", "Shutter_Island_(film)"),
        ("세븐", 1995, "두 형사가 일곱 가지 죄악을 모티브로 벌어지는 연쇄 살인 사건을 추적합니다.", "Seven_(1995_film)"),
        ("조디악", 2007, "실제 사건을 바탕으로 형사와 기자들이 정체불명의 연쇄살인범을 오랫동안 추적합니다.", "Zodiac_(film)"),
        ("오리엔트 특급 살인", 2017, "눈으로 멈춰 선 호화 열차에서 살인 사건이 발생하자 탐정 푸아로가 승객들을 조사합니다.", "Murder_on_the_Orient_Express_(2017_film)"),
    ],
    "AHN": [
        ("컨택트", 2016, "지구 곳곳에 미지의 비행체가 나타나자 언어학자가 외계 존재와의 소통에 나섭니다.", "Arrival_(film)"),
        ("그랜드 부다페스트 호텔", 2014, "전설적인 호텔 지배인 구스타브와 로비 보이가 한 그림을 둘러싼 사건에 휘말립니다.", "The_Grand_Budapest_Hotel"),
        ("그녀", 2013, "외로운 남자 테오도르가 인공지능 운영체제와 깊은 관계를 맺으며 사랑의 의미를 탐색합니다.", "Her_(film)"),
        ("더 문", 2009, "달 기지에서 홀로 근무하던 우주비행사가 임무 종료를 앞두고 자신의 존재에 의문을 품습니다.", "Moon_(2009_film)"),
        ("애프터 양", 2021, "가족처럼 지내던 인공지능 로봇 양이 멈추자 아버지가 양의 기억을 따라가며 관계를 되짚습니다.", "After_Yang"),
    ],
    "AHF": [
        ("머니볼", 2011, "예산이 부족한 야구단 단장이 데이터 분석을 활용해 새로운 방식으로 팀을 꾸립니다.", "Moneyball_(film)"),
        ("인턴", 2015, "은퇴 후 신생 패션 회사의 인턴이 된 벤이 젊은 CEO와 동료들에게 따뜻한 변화를 가져옵니다.", "The_Intern_(2015_film)"),
        ("스포트라이트", 2015, "보스턴 글로브 탐사보도팀이 오랫동안 은폐된 사건을 집요한 취재로 파헤칩니다.", "Spotlight_(film)"),
        ("히든 피겨스", 2016, "1960년대 NASA에서 일하는 세 흑인 여성 수학자가 우주 탐사에 중요한 역할을 합니다.", "Hidden_Figures"),
        ("빅 쇼트", 2015, "2008년 금융위기 전조를 포착한 투자자들이 미국 주택시장 거품의 붕괴에 베팅합니다.", "The_Big_Short_(film)"),
    ],
}

RESULTS = {
    "GTN": {"name": "감성 스릴 탐험가", "tagline": "감정은 깊게, 이야기는 새롭게!", "description": "새로운 세계를 탐험하면서도 인물의 감정에 깊이 빠져드는 관객입니다. 화려한 상상력 속에 진한 여운이 남는 영화를 좋아해요.", "genres": ["감성 SF", "판타지", "어드벤처"], "color": "#8B5CF6", "soft": "#EDE9FE", "symbol": "✦"},
    "GTF": {"name": "몰입형 드라마 헌터", "tagline": "마음을 움직이는 긴박한 한 편", "description": "위기의 순간에 드러나는 사람들의 선택과 관계에 몰입합니다. 손에 땀을 쥐면서도 마음이 먹먹해지는 이야기가 취향이에요.", "genres": ["휴먼 스릴러", "재난 드라마", "서바이벌"], "color": "#F97368", "soft": "#FFE4E6", "symbol": "♥"},
    "GHN": {"name": "상상력 넘치는 감성가", "tagline": "낯선 세상에서 찾는 따뜻함", "description": "독창적인 상상력이 담긴 이야기에서 위로와 감동을 얻습니다. 잔잔하지만 오래 기억에 남는 영화가 마음에 들어요.", "genres": ["감성 판타지", "애니메이션", "성장"], "color": "#14B8A6", "soft": "#CCFBF1", "symbol": "✿"},
    "GHF": {"name": "따뜻한 추억 수집가", "tagline": "평범한 순간의 특별한 감동", "description": "소소한 일상, 다정한 관계, 마음이 편해지는 분위기를 좋아합니다. 낯설지 않은 이야기에서 깊은 공감을 느끼는 타입이에요.", "genres": ["힐링", "로맨스", "일상 드라마"], "color": "#E6A348", "soft": "#FEF3C7", "symbol": "☀"},
    "ATN": {"name": "반전 추적 분석가", "tagline": "복잡할수록 더 재밌는 이야기", "description": "독특한 설정과 치밀한 복선이 있는 영화를 사랑합니다. 이야기를 분석하며 반전의 실마리를 찾는 과정 자체가 큰 즐거움이에요.", "genres": ["SF 스릴러", "미스터리", "액션"], "color": "#3B82F6", "soft": "#DBEAFE", "symbol": "◈"},
    "ATF": {"name": "정통 추리 애호가", "tagline": "모든 단서에는 이유가 있다", "description": "잘 짜인 추리극과 예리한 반전을 선호합니다. 익숙한 사건 구조 속에 숨은 작은 단서까지 놓치지 않는 관객이에요.", "genres": ["추리", "범죄", "미스터리"], "color": "#65748B", "soft": "#E2E8F0", "symbol": "⌕"},
    "AHN": {"name": "조용한 세계관 탐구자", "tagline": "한 편이 끝나도 생각은 계속", "description": "독창적인 아이디어를 차분하게 풀어낸 영화를 좋아합니다. 보고 난 뒤에도 질문이 남는 작품에 특히 마음이 끌려요.", "genres": ["철학적 SF", "예술 영화", "독립 영화"], "color": "#8B7FE8", "soft": "#EDE9FE", "symbol": "☾"},
    "AHF": {"name": "차분한 현실 관찰자", "tagline": "현실에서 발견하는 이야기의 힘", "description": "설득력 있는 인물과 현실적인 사건을 선호합니다. 대단한 반전보다 세밀한 관찰과 탄탄한 이야기에서 재미를 느껴요.", "genres": ["실화 기반", "휴먼 드라마", "직업 드라마"], "color": "#22A485", "soft": "#D1FAE5", "symbol": "◇"},
}

AXES = (("G", "A", "감성", "분석"), ("T", "H", "긴장", "편안함"), ("N", "F", "새로움", "익숙함"))


def classify(answers):
    """12개의 0/1 선택 목록 -> (결과 코드, 각 성향 빈도)."""
    if len(answers) != len(QUESTIONS) or any(x not in (0, 1) for x in answers):
        raise ValueError("12개의 유효한 답변이 필요합니다.")
    scores = Counter(QUESTIONS[i]["options"][answer][1] for i, answer in enumerate(answers))
    code = ""
    for left, right, _, _ in AXES:
        if scores[left] > scores[right]:
            code += left
        elif scores[right] > scores[left]:
            code += right
        else:
            first = next(i for i, q in enumerate(QUESTIONS) if q["axis"] == left + right)
            code += QUESTIONS[first]["options"][answers[first]][1]
    return code, scores


def encode_answers(answers):
    """서버 저장 없이 12개의 선택을 링크로 전달합니다. 개인정보는 넣지 않습니다."""
    return "".join(map(str, answers))


def decode_answers(encoded):
    if isinstance(encoded, str) and len(encoded) == len(QUESTIONS) and set(encoded) <= {"0", "1"}:
        return [int(x) for x in encoded]
    return None


# ───────────────────────────── 2. 스타일 및 캐릭터 ────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700;800;900&display=swap');
  html, body, [class*="css"], [data-testid="stAppViewContainer"] {
    font-family: 'Noto Sans KR', system-ui, sans-serif;
  }
  [data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at 85% 5%, #fff0f5 0, transparent 38%),
                radial-gradient(circle at 15% 0, #eef0ff 0, transparent 42%), #fafbff;
  }
  .block-container {max-width: 1030px; padding-top: 2.3rem; padding-bottom: 4rem;}
  h1, h2, h3 {letter-spacing: -.05em;}
  div.stButton > button[kind="primary"], div.stDownloadButton > button[kind="primary"] {
    border: none; border-radius: 15px; min-height: 3.2rem;
    background: linear-gradient(110deg, #6758e7, #9b5de5); color:white;
    font-weight:800; box-shadow: 0 6px 18px #7562c72d;
  }
  div.stButton > button {border-radius: 13px; min-height: 2.9rem; font-weight: 600;}
  div.stLinkButton > a {border-radius: 13px; font-weight: 700;}
  [data-testid="stRadio"] label {padding-top: .4rem; padding-bottom: .4rem;}
  .brand {font-size:1.35rem;font-weight:900; letter-spacing:-.05em;color:#5748b9;}
  .kicker {font-size:.78rem;letter-spacing:.2em;font-weight:900;color:#7462d9;margin-bottom:.8rem;}
  .hero {
    border-radius:27px; padding:2.9rem 2.9rem 3rem; min-height: 290px;
    background: linear-gradient(118deg,#1d2047 0%,#383178 52%,#7656a8 100%);
    color:white; position:relative; box-shadow:0 16px 45px #28234b27;
  }
  .hero::after {content:'✦'; position:absolute;top:23px;right:45px;color:#ffcfda;
    font-size:5.7rem;opacity:.65;transform:rotate(10deg);}
  .hero h1 {font-size:clamp(2rem,4.8vw,3rem);color:white;line-height:1.35;margin:.4rem 0 1rem;}
  .hero p {color:#e5e1fc;line-height:1.75;font-size:1.02rem;max-width:580px;}
  .hero-eyebrow {color:#ffe3b7; font-size:.82rem; font-weight:800;letter-spacing:.12em;}
  .tiny-tag {display:inline-block;border-radius:999px;background:#efedff;color:#5948bd;padding:6px 13px;
    font-size:.78rem;font-weight:800;margin-right:8px;margin-top:8px;}
  .glass-card {background:#fff;border:1px solid #ebeaf6;border-radius:20px;
    padding:1.65rem 1.8rem;box-shadow:0 9px 30px #27244d0a;}
  .step-badge {color:#7b6fbe;font-size:.85rem;font-weight:800;letter-spacing:.08em;}
  .question-title {font-size:clamp(1.35rem,3.3vw,1.9rem);font-weight:900;line-height:1.45;
    margin:1rem 0 1.7rem;color:#24223f;letter-spacing:-.045em;}
  .section-head {font-size:1.47rem;font-weight:900;letter-spacing:-.05em;color:#272444;margin:2.3rem 0 .8rem;}
  .section-sub {color:#75758b;font-size:.93rem;margin-bottom:1.2rem;}
  .result-hero {border-radius:25px; padding:2.1rem 2.25rem;color:#fff;
    background:linear-gradient(120deg,#222149 0%,#3c3775 62%,#6557a3 100%);
    box-shadow:0 14px 40px #30266028;}
  .result-hero .code {color:#c8befb;font-size:.93rem;letter-spacing:.17em;font-weight:900;}
  .result-hero h1 {font-size:2.1rem;line-height:1.35;color:white;margin:.4rem 0 .6rem;}
  .result-hero .tagline {font-size:1.08rem;font-weight:800;color:#ffe4b8;margin-bottom:1rem;}
  .result-hero p {color:#e9e8fb;line-height:1.8;margin-bottom:0;font-size:.95rem;}
  .film-card {border:1px solid #eeeaf5;background:white;border-radius:17px;
    padding:1.35rem 1.45rem;margin-bottom:.65rem;box-shadow:0 5px 22px #1f23400b;}
  .film-number {color:#8d79d1;font-size:.78rem;font-weight:900;letter-spacing:.1em;}
  .film-name {font-weight:900;color:#24233c;font-size:1.16rem;margin:.22rem 0 .55rem;}
  .film-year {font-weight:600;color:#8b8aa1;font-size:.8rem;}
  .film-plot {color:#55566c;line-height:1.75;font-size:.91rem;}
  .poster-fallback {height:185px;border-radius:13px;display:flex;align-items:center;
    justify-content:center;text-align:center;line-height:1.6;padding:14px;
    color:#fefefe;font-weight:900;background:linear-gradient(155deg,#26234d,#9b74b9);}
  .dna-row {margin:16px 0 21px;}
  .dna-labels {display:flex;justify-content:space-between;color:#514c71;font-size:.89rem;font-weight:800;margin-bottom:7px;}
  .dna-track {display:flex;height:13px;border-radius:20px;overflow:hidden;background:#e8e4fa;}
  .dna-left {background:linear-gradient(90deg,#6b5cce,#ad86e6);}
  .dna-right {background:#c7d1e6;}
  .footnote {color:#8b8a9d;font-size:.81rem;line-height:1.7;}
  @media (max-width:640px) {
    .block-container {padding-top:1rem;padding-left:1.1rem;padding-right:1.1rem;}
    .hero {padding:2rem 1.4rem;min-height:250px;}
    .hero::after {font-size:3.7rem;right:15px;top:0;opacity:.3;}
    .result-hero {padding:1.45rem;}
    .result-hero h1 {font-size:1.55rem;}
  }
</style>
""", unsafe_allow_html=True)


def make_avatar(code, size=520):
    """8가지 결과 유형마다 다른 색과 소품을 가진 캐릭터 PNG를 즉석 생성합니다."""
    cfg = RESULTS[code]
    accent = cfg["color"]
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # 배경 원과 영화 필름 소품
    d.ellipse((25, 25, size - 25, size - 25), fill=cfg["soft"])
    d.ellipse((62, 53, size - 62, size - 53), outline=accent, width=7)
    for x, y, r in [(102, 122, 9), (410, 125, 12), (95, 343, 7), (421, 335, 8)]:
        d.ellipse((x-r, y-r, x+r, y+r), fill=accent)
    d.rounded_rectangle((105, 343, 415, 535), radius=90, fill=accent)
    d.ellipse((152, 130, 370, 380), fill="#F3C5A8")  # 얼굴
    d.ellipse((145, 255, 171, 298), fill="#F3C5A8")
    d.ellipse((350, 255, 376, 298), fill="#F3C5A8")
    # 머리: 감성형은 곡선 머리, 분석형은 깔끔한 옆가르마
    if code[0] == "G":
        d.pieslice((145, 105, 375, 285), 185, 355, fill="#3A2A42")
        d.ellipse((145, 131, 276, 224), fill="#3A2A42")
        d.ellipse((244, 114, 366, 205), fill="#3A2A42")
    else:
        d.pieslice((150, 112, 367, 283), 185, 352, fill="#222842")
        d.polygon([(148, 202), (200, 133), (359, 162), (358, 189), (238, 183)], fill="#222842")
    for x in (222, 302):
        d.ellipse((x - 8, 254, x + 8, 275), fill="#2D2841")
    d.arc((233, 282, 285, 322), 5, 175, fill="#BA6C72", width=5)
    d.ellipse((182, 285, 204, 297), fill="#E99DA1")
    d.ellipse((322, 285, 344, 297), fill="#E99DA1")
    # 분석형은 안경
    if code[0] == "A":
        d.rounded_rectangle((193, 239, 249, 289), radius=18, outline="#39455B", width=5)
        d.rounded_rectangle((272, 239, 328, 289), radius=18, outline="#39455B", width=5)
        d.line((249, 255, 272, 255), fill="#39455B", width=5)
    # 긴장(T): 헤드셋 / 편안함(H): 베레모
    if code[1] == "T":
        d.arc((147, 164, 371, 376), 185, 355, fill=accent, width=14)
        d.rounded_rectangle((127, 245, 159, 305), radius=11, fill="#332D60")
        d.rounded_rectangle((361, 245, 393, 305), radius=11, fill="#332D60")
    else:
        d.ellipse((164, 106, 346, 158), fill=accent)
        d.ellipse((200, 80, 310, 126), fill=accent)
        d.ellipse((272, 75, 292, 95), fill="#36305A")
    # 상의 위 카메라/별 배지
    d.rounded_rectangle((233, 395, 293, 446), radius=12, fill="#FFFFFF")
    if code[2] == "N":
        d.polygon([(263, 402), (271, 420), (288, 420), (274, 431), (279, 446),
                   (263, 437), (247, 446), (252, 431), (238, 420), (255, 420)], fill=accent)
    else:
        d.ellipse((251, 408, 275, 432), outline=accent, width=6)
        d.rectangle((259, 432, 267, 441), fill=accent)
    output = BytesIO()
    img.save(output, format="PNG", optimize=True)
    return output.getvalue()


# ─────────────────────────── 3. 위키백과 포스터 이미지 ─────────────────────────
@st.cache_data(ttl=60 * 60 * 24 * 7, show_spinner=False)
def wikipedia_poster(page_title):
    """별도 인증키 없이 영화 문서의 대표 썸네일을 읽어옵니다. 실패 시 None."""
    url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + quote(page_title, safe="")
    try:
        response = requests.get(
            url, timeout=3.5,
            headers={"User-Agent": "CineTypeMovieQuiz/1.0 (educational project; public film thumbnails)",
                     "Accept": "application/json"},
        )
        response.raise_for_status()
        payload = response.json()
        image = payload.get("thumbnail") or {}
        thumb_url = image.get("source", "")
        return thumb_url if thumb_url.startswith("https://") else None
    except (requests.RequestException, ValueError, TypeError):
        return None


# ───────────────────────── 4. 다운로드용 결과 카드 생성 ────────────────────────
def find_hangul_font():
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",  # Community Cloud의 packages.txt
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/malgun.ttf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    ]
    for path in candidates:
        if Path(path).is_file():
            return path
    return None


def draw_multiline(draw, text, pos, font, fill, line_gap=9, max_width=None):
    """한글 문장을 픽셀 길이에 맞춰 자동 줄바꿈합니다."""
    x, y = pos
    if max_width is None:
        lines = text.split("\n")
    else:
        lines, current = [], ""
        for word in text.split(" "):
            trial = f"{current} {word}".strip()
            if current and draw.textbbox((0, 0), trial, font=font)[2] > max_width:
                lines.append(current)
                current = word
            else:
                current = trial
        if current:
            lines.append(current)
    line_height = draw.textbbox((0, 0), "가Ag", font=font)[3] + line_gap
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height
    return y


def make_result_png(code, scores):
    """유형, 설명, 추천 영화 다섯 편, 취향 막대 그래프를 담은 1080×1600 카드."""
    result = RESULTS[code]
    width, height = 1080, 1600
    pic = Image.new("RGB", (width, height), "#F8F7FD")
    draw = ImageDraw.Draw(pic)
    font_file = find_hangul_font()
    def font(n):
        return ImageFont.truetype(font_file, n) if font_file else ImageFont.load_default()

    # 카드 배경과 헤더
    draw.rounded_rectangle((48, 40, 1032, 1550), radius=42, fill="#FFFFFF")
    draw.rounded_rectangle((48, 40, 1032, 525), radius=42, fill="#24234E")
    draw.rectangle((48, 465, 1032, 525), fill="#24234E")
    draw.text((104, 99), "C I N E T Y P E    /    M O V I E   T Y P E", font=font(25), fill="#C8C0FD")
    draw.text((104, 170), code, font=font(64), fill="#D4C6FF")
    draw.text((104, 255), result["name"], font=font(53), fill="#FFFFFF")
    draw.text((104, 350), result["tagline"], font=font(28), fill="#FCE4B1")
    avatar = Image.open(BytesIO(make_avatar(code, 500))).resize((310, 310))
    pic.paste(avatar, (668, 171), avatar)
    # 설명
    draw_multiline(draw, result["description"], (105, 562), font(26), "#48475C", 16, 842)
    draw.text((104, 725), "추천 영화  TOP 5", font=font(36), fill="#302A59")
    y = 805
    for i, movie in enumerate(MOVIES[code], 1):
        title, year, _, _ = movie
        draw.rounded_rectangle((101, y - 12, 983, y + 74), radius=16, fill="#F4F1FB")
        draw.text((128, y + 4), f"{i:02d}", font=font(30), fill=result["color"])
        draw.text((213, y + 3), f"{title}  ({year})", font=font(26), fill="#302A59")
        y += 100
    # 성향 분포, 구분 텍스트 대신 양 끝 선호도만 제공
    draw.text((104, 1331), "나의 영화 취향 DNA", font=font(29), fill="#302A59")
    for i, (left, right, left_name, right_name) in enumerate(AXES):
        yy = 1388 + i * 43
        draw.text((108, yy - 5), left_name, font=font(20), fill="#524C6E")
        draw.text((898, yy - 5), right_name, font=font(20), fill="#524C6E")
        full = scores[left] + scores[right]
        proportion = scores[left] / full if full else .5
        draw.rounded_rectangle((215, yy, 862, yy + 17), radius=8, fill="#CDD4EA")
        if proportion > 0:
            draw.rounded_rectangle((215, yy, 215 + max(14, int(647 * proportion)), yy + 17), radius=8, fill=result["color"])
    draw.text((108, 1510), "CineType · 재미를 위한 영화 취향 테스트", font=font(19), fill="#908FA1")
    buf = BytesIO()
    pic.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


# ──────────────────────────── 5. 상태 및 공유 URL ─────────────────────────────
if "stage" not in st.session_state:
    from_link = decode_answers(st.query_params.get("a", ""))
    st.session_state.answers = {i: a for i, a in enumerate(from_link)} if from_link else {}
    st.session_state.stage = len(QUESTIONS) if from_link else -1


def reset_test():
    st.query_params.clear()
    for key in list(st.session_state.keys()):
        if key == "stage" or key == "answers" or key.startswith("choice_"):
            del st.session_state[key]
    st.session_state.stage = -1
    st.session_state.answers = {}


def base_url():
    # Streamlit 1.45 이상에서는 앱의 현재 배포 URL을 바로 확인할 수 있습니다.
    try:
        return st.context.url
    except (AttributeError, RuntimeError):
        return ""


def share_buttons(code, link):
    if not link:
        st.info("배포된 Streamlit 웹사이트에서 접속하면 공유 링크가 표시됩니다.")
        return
    text = f"🎬 나의 영화 취향은 {code} · {RESULTS[code]['name']}! 당신의 CineType은?"
    st.text_input("내 결과 링크 · 카카오톡/인스타그램 DM에도 붙여넣을 수 있어요", value=link)
    col_x, col_fb, col_tg = st.columns(3)
    with col_x:
        st.link_button("𝕏 에 공유", f"https://twitter.com/intent/tweet?{urlencode({'text':text,'url':link})}", use_container_width=True)
    with col_fb:
        st.link_button("Facebook", f"https://www.facebook.com/sharer/sharer.php?{urlencode({'u':link})}", use_container_width=True)
    with col_tg:
        st.link_button("Telegram", f"https://t.me/share/url?{urlencode({'url':link,'text':text})}", use_container_width=True)
    st.caption("인스타그램 피드·스토리는 아래 결과 이미지를 저장한 뒤 직접 업로드하세요. 카카오톡은 링크를 복사해서 공유할 수 있어요.")


def show_dna(scores):
    """사용자가 요청할 때만 3개 성향의 비율 막대를 펼쳐서 보여줍니다."""
    with st.expander("나의 영화 취향 DNA · 성향 그래프 보기", expanded=False):
        st.caption("각 항목은 네 번의 선택을 바탕으로 계산한 상대적 선호도입니다.")
        for left, right, left_name, right_name in AXES:
            a, b = scores[left], scores[right]
            pct = round(a / (a + b) * 100) if a + b else 50
            st.markdown(f"""
            <div class="dna-row">
                <div class="dna-labels"><span>{left_name} {pct}%</span><span>{right_name} {100-pct}%</span></div>
                <div class="dna-track"><div class="dna-left" style="width:{pct}%"></div><div class="dna-right" style="width:{100-pct}%"></div></div>
            </div>""", unsafe_allow_html=True)


# ─────────────────────────────── 6. 페이지 UI ────────────────────────────────
brand_col, logout_col = st.columns([5, 1], vertical_alignment="center")
with brand_col:
    st.markdown('<div class="brand">◉ CineType <span style="font-size:.7rem;color:#9a92b7;font-weight:600;">MOVIE PERSONALITY</span></div>', unsafe_allow_html=True)
with logout_col:
    if st.button("로그아웃", use_container_width=True):
        st.session_state.pop("_cinetype_authenticated", None)
        reset_test()
        st.rerun()
st.write("")

if st.session_state.stage == -1:
    st.markdown("""
    <div class="hero">
      <div class="hero-eyebrow">FIND YOUR CINEMA DNA</div>
      <h1>당신의 영화 취향은<br>무엇인가요?</h1>
      <p>영화를 보는 순간, 당신의 마음이 끌리는 장면은 무엇인가요?<br>
      몇 가지 선택으로 나만의 영화 취향을 발견해 보세요.</p>
    </div>
    """, unsafe_allow_html=True)
    st.write("")
    st.write("")
    left, center, right = st.columns([1, 2, 1])
    with center:
        if st.button("🎬 내 영화 취향 발견하기", type="primary", use_container_width=True):
            st.session_state.stage = 0
            st.rerun()
    st.markdown("""
    <div style="text-align:center;margin:2rem 0 1rem;color:#8f8ca7;font-size:.87rem;line-height:1.8;">
      작은 선택들이 모여 하나의 영화 취향이 됩니다.<br>당신에게 딱 맞는 다섯 편을 만나보세요.
    </div>""", unsafe_allow_html=True)

elif st.session_state.stage < len(QUESTIONS):
    idx = st.session_state.stage
    q = QUESTIONS[idx]
    st.markdown(f'<div class="kicker">YOUR MOVIE TASTE</div>', unsafe_allow_html=True)
    st.progress((idx + 1) / len(QUESTIONS))
    with st.container(border=True):
        st.markdown(f'<div class="step-badge">QUESTION {idx + 1:02d} / {len(QUESTIONS):02d}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="question-title">{q["text"]}</div>', unsafe_allow_html=True)
        labels = [item[0] for item in q["options"]]
        # 선택 값은 0/1로 저장합니다. 뒤로 갔다 와도 이전 답변이 유지됩니다.
        selected = st.radio(
            "더 마음에 드는 답변을 선택하세요",
            options=(0, 1),
            format_func=lambda x: labels[x],
            index=st.session_state.answers.get(idx),
            key=f"choice_{idx}",
            label_visibility="collapsed",
        )
    st.write("")
    col_prev, col_next = st.columns([1, 2])
    with col_prev:
        if st.button("← 이전", disabled=(idx == 0), use_container_width=True):
            if selected is not None:
                st.session_state.answers[idx] = selected
            st.session_state.stage -= 1
            st.rerun()
    with col_next:
        button_name = "결과 확인하기 →" if idx == len(QUESTIONS) - 1 else "다음 질문 →"
        if st.button(button_name, type="primary", use_container_width=True):
            if selected is None:
                st.warning("먼저 답변을 하나 선택해 주세요.")
            else:
                st.session_state.answers[idx] = selected
                st.session_state.stage += 1
                if st.session_state.stage == len(QUESTIONS):
                    answers = [st.session_state.answers[i] for i in range(len(QUESTIONS))]
                    st.query_params["a"] = encode_answers(answers)
                st.rerun()

else:
    answers = [st.session_state.answers.get(i) for i in range(len(QUESTIONS))]
    if any(answer is None for answer in answers):
        st.error("답변 기록이 완전하지 않습니다. 다시 테스트해 주세요.")
        if st.button("처음으로", type="primary"):
            reset_test()
            st.rerun()
        st.stop()

    code, scores = classify(answers)
    result = RESULTS[code]
    st.markdown('<div class="kicker">YOUR CINETYPE HAS ARRIVED</div>', unsafe_allow_html=True)
    col_text, col_avatar = st.columns([1.52, 1], vertical_alignment="center")
    with col_text:
        st.markdown(f"""
        <div class="result-hero">
          <div class="code">YOUR TYPE · {code}</div>
          <h1>{result['name']}</h1>
          <div class="tagline">{result['tagline']}</div>
          <p>{result['description']}</p>
        </div>""", unsafe_allow_html=True)
        st.markdown("".join(f'<span class="tiny-tag"># {g}</span>' for g in result["genres"]), unsafe_allow_html=True)
    with col_avatar:
        st.image(make_avatar(code), use_container_width=True, caption=f"{code} 유형 캐릭터")

    st.markdown('<div class="section-head">당신에게 추천하는 영화 5편</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">당신의 취향과 잘 어울릴 만한 작품을 골랐어요. 포스터를 누르면 영화 정보를 볼 수 있습니다.</div>', unsafe_allow_html=True)
    for i, (title, year, story, wiki_page) in enumerate(MOVIES[code], 1):
        poster_col, info_col = st.columns([1, 3.3], gap="medium", vertical_alignment="center")
        with poster_col:
            poster = wikipedia_poster(wiki_page)
            wiki_link = "https://en.wikipedia.org/wiki/" + quote(wiki_page, safe="()_:")
            if poster:
                st.image(poster, use_container_width=True, link=wiki_link, alt=f"{title} 포스터")
            else:
                st.markdown(f'<div class="poster-fallback">🎞️<br>{title}</div>', unsafe_allow_html=True)
        with info_col:
            st.markdown(f'<div class="film-number">PICK {i:02d}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="film-name">{title} <span class="film-year">({year})</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="film-plot">{story}</div>', unsafe_allow_html=True)
            st.link_button("영화 정보 보기 ↗", wiki_link)
        st.divider()

    show_dna(scores)  # 이전의 '나의 선택 결과' 텍스트/점수 표는 표시하지 않습니다.

    st.markdown('<div class="section-head">결과 저장하기</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">내 캐릭터와 추천 영화가 담긴 결과 카드를 이미지로 저장할 수 있어요.</div>', unsafe_allow_html=True)
    save1, save2 = st.columns([1, 1])
    with save1:
        st.download_button(
            "🖼️ 결과 카드 PNG 저장",
            data=make_result_png(code, scores),
            file_name=f"CineType_{code}_result.png",
            mime="image/png", type="primary", use_container_width=True,
        )
    with save2:
        summary = (
            f"CineType | 나의 영화 취향 MBTI\n{code} · {result['name']}\n\n"
            f"{result['tagline']}\n{result['description']}\n\n"
            "추천 영화 5편\n" +
            "\n".join(f"{i}. {m[0]} ({m[1]}) — {m[2]}" for i, m in enumerate(MOVIES[code], 1)) +
            "\n\n이 테스트는 재미를 위한 취향 분류이며 심리학적 진단 도구가 아닙니다.\n"
        )
        st.download_button(
            "📄 결과 텍스트 저장",
            data=summary.encode("utf-8-sig"),
            file_name=f"CineType_{code}_result.txt",
            mime="text/plain", use_container_width=True,
        )

    st.markdown('<div class="section-head">친구에게 결과 공유하기</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">친구가 링크를 열면 내 영화 취향 결과와 추천 영화도 함께 볼 수 있어요.</div>', unsafe_allow_html=True)
    app_url = base_url()
    share_link = f"{app_url}?{urlencode({'a': encode_answers(answers)})}" if app_url else ""
    share_buttons(code, share_link)
    st.write("")
    if st.button("↻ 처음부터 다시 테스트하기", use_container_width=True):
        reset_test()
        st.rerun()
    st.write("")
    st.markdown('<div class="footnote">※ CineType은 재미를 위해 만든 규칙 기반 영화 취향 테스트입니다. 전문가의 심리 진단이 아니며 영화 추천은 미리 선정한 예시입니다.<br>영화 포스터(제공 가능한 경우): Wikipedia 문서의 대표 이미지. 포스터의 권리는 각 권리자에게 있습니다.</div>', unsafe_allow_html=True)
