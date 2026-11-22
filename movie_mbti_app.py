import streamlit as st

st.set_page_config(page_title="CineType | 영화 취향 테스트", page_icon="🎬", layout="centered")

# 3가지 성향 축: G(감성)/A(분석), T(긴장)/H(편안함), N(새로움)/F(익숙함)
# 질문 12개: 각 성향 축마다 4개씩 배치했습니다.
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

# 결과는 AI나 인터넷 검색 없이 미리 정의한 8가지 유형에서 선택됩니다.
RESULTS = {
    "GTN": {"name": "감성 스릴 탐험가", "description": "강렬한 감정과 긴박한 전개, 새로운 세계관을 함께 즐기는 타입입니다.", "genres": "판타지 · SF · 감성 스릴러", "movies": ["에브리씽 에브리웨어 올 앳 원스", "옥자"]},
    "GTF": {"name": "몰입형 드라마 헌터", "description": "익숙한 소재라도 인물의 감정과 갈등이 강하게 드러나는 이야기에 몰입합니다.", "genres": "재난 드라마 · 휴먼 스릴러", "movies": ["부산행", "타이타닉"]},
    "GHN": {"name": "상상력 넘치는 감성가", "description": "잔잔하지만 독창적인 이야기에서 위로와 감동을 얻는 타입입니다.", "genres": "감성 판타지 · 애니메이션", "movies": ["소울", "월터의 상상은 현실이 된다"]},
    "GHF": {"name": "따뜻한 추억 수집가", "description": "친숙한 이야기와 다정한 관계, 편안한 분위기를 좋아합니다.", "genres": "로맨스 · 힐링 · 일상 드라마", "movies": ["리틀 포레스트", "어바웃 타임"]},
    "ATN": {"name": "반전 추적 분석가", "description": "복잡한 설정과 빠른 전개 속에서 단서를 분석하는 재미를 즐깁니다.", "genres": "SF 스릴러 · 미스터리", "movies": ["인셉션", "테넷"]},
    "ATF": {"name": "정통 추리 애호가", "description": "명확한 규칙을 가진 추리극에서 복선과 반전을 찾아내는 것을 좋아합니다.", "genres": "추리 · 범죄 · 미스터리", "movies": ["나이브스 아웃", "셔터 아일랜드"]},
    "AHN": {"name": "조용한 세계관 탐구자", "description": "차분한 속도 속에서도 생각할 거리가 많은 독창적인 영화를 선호합니다.", "genres": "철학적 SF · 예술 영화", "movies": ["컨택트", "그랜드 부다페스트 호텔"]},
    "AHF": {"name": "차분한 현실 관찰자", "description": "현실에 가까운 소재와 설득력 있는 이야기 구조를 편안하게 감상합니다.", "genres": "실화 기반 드라마 · 일상 드라마", "movies": ["머니볼", "인턴"]},
}

AXES = [
    ("GA", "감상 기준", "G", "감성", "A", "분석"),
    ("TH", "분위기 선호", "T", "긴장", "H", "편안함"),
    ("NF", "소재 선호", "N", "새로움", "F", "익숙함"),
]


def get_result(answers):
    """각 축에서 많이 선택한 글자를 사용합니다. 2:2 동점이면 해당 축의 첫 질문으로 결정합니다."""
    points = {letter: 0 for letter in "GATHNF"}
    for number, question in enumerate(QUESTIONS):
        selected_option_index = answers[number]
        letter = question["options"][selected_option_index][1]
        points[letter] += 1

    code = ""
    for axis, _, left, _, right, _ in AXES:
        if points[left] > points[right]:
            code += left
        elif points[right] > points[left]:
            code += right
        else:
            first_question = next(i for i, q in enumerate(QUESTIONS) if q["axis"] == axis)
            code += QUESTIONS[first_question]["options"][answers[first_question]][1]
    return code, points


# 사용자의 답변과 현재 질문 번호를 저장합니다.
if "step" not in st.session_state:
    st.session_state.step = -1  # -1은 시작 화면을 의미합니다.
if "answers" not in st.session_state:
    st.session_state.answers = {}

st.markdown("<h1 style='text-align:center;'>🎬 CineType</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;color:#666;'>12개의 질문으로 알아보는 나의 영화 취향</p>", unsafe_allow_html=True)
st.divider()

if st.session_state.step == -1:
    st.subheader("당신은 어떤 영화 관객인가요?")
    st.write("영화에서 중요하게 보는 요소를 선택하면 8가지 유형 중 하나를 알려드립니다.")
    st.info("질문 12개 · 결과 유형 8개 · 로그인과 API 연결 불필요")
    if st.button("테스트 시작하기", type="primary", use_container_width=True):
        st.session_state.step = 0
        st.rerun()

elif st.session_state.step < len(QUESTIONS):
    number = st.session_state.step
    question = QUESTIONS[number]
    option_labels = [option[0] for option in question["options"]]
    st.progress(number / len(QUESTIONS))
    st.caption(f"질문 {number + 1} / {len(QUESTIONS)}")
    st.subheader(question["text"])
    choice = st.radio(
        "답변을 하나 선택하세요",
        option_labels,
        index=st.session_state.answers.get(number),
        key=f"question_{number}",
    )

    left_col, right_col = st.columns(2)
    with left_col:
        if st.button("이전", disabled=(number == 0), use_container_width=True):
            if choice is not None:
                st.session_state.answers[number] = option_labels.index(choice)
            st.session_state.step -= 1
            st.rerun()
    with right_col:
        label = "결과 확인하기" if number == len(QUESTIONS) - 1 else "다음"
        if st.button(label, type="primary", use_container_width=True):
            if choice is None:
                st.warning("답변을 선택한 후 진행해 주세요.")
            else:
                st.session_state.answers[number] = option_labels.index(choice)
                st.session_state.step += 1
                st.rerun()

else:
    code, points = get_result(st.session_state.answers)
    result = RESULTS[code]
    st.progress(1.0)
    st.caption("영화 취향 분석 완료")
    st.markdown(f"## {code} · {result['name']}")
    st.write(result["description"])
    st.subheader("선호할 만한 영화 장르")
    st.write(result["genres"])
    st.subheader("추천 영화")
    for film in result["movies"]:
        st.write(f"• {film}")
    st.subheader("나의 선택 결과")
    for _, title, left, left_name, right, right_name in AXES:
        st.write(f"**{title}**: {left_name} {points[left]}회 / {right_name} {points[right]}회")
    st.caption("이 테스트는 재미를 위한 선호도 분류이며 심리학적으로 검증된 진단은 아닙니다. 추천 영화는 유형별 예시로 미리 설정했습니다.")
    if st.button("다시 테스트하기", type="primary", use_container_width=True):
        for key in list(st.session_state.keys()):
            if key in ("step", "answers") or key.startswith("question_"):
                del st.session_state[key]
        st.rerun()
