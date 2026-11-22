# 🎬 CineType — 영화 취향 MBTI

Streamlit 기반의 12문항 / 8가지 유형 영화 취향 테스트입니다.

## 기능
- 12문항 답변으로 8가지 유형 분류
- 유형별 캐릭터 이미지 자동 생성
- 영화 추천 5편: 포스터(가능한 경우), 제목, 개봉 연도, 한줄 줄거리
- 취향 균형 막대그래프 (선택적으로 펼쳐 보기)
- 결과 카드 PNG 및 텍스트 다운로드
- 재접속 가능한 공유 링크, X / Facebook / Telegram 공유
- GitHub + Streamlit Community Cloud 배포

## GitHub에 올릴 파일

```
Movie_MBTI/
├── app.py
├── requirements.txt
└── packages.txt
```

`README.md`는 설명용으로 선택적으로 업로드해도 됩니다.

## 실행 방법

```bash
pip install -r requirements.txt
streamlit run app.py
```

Streamlit Community Cloud의 앱 파일 경로는 `app.py`로 설정하면 됩니다. 기존 Streamlit 앱이 있으면 GitHub에서 `app.py`를 이 파일로 바꾸고 `requirements.txt`, `packages.txt`를 추가한 뒤 커밋하세요.

## 이미지에 관하여
영화 포스터는 Wikipedia의 공개 문서 대표 이미지를 이용합니다. 별도 API 키나 로그인은 필요하지 않지만, 외부 네트워크 문제 또는 문서의 이미지 부재로 포스터가 표시되지 않을 수 있습니다. 이때 영화 제목이 들어간 대체 카드가 표시되고 나머지 기능은 정상 동작합니다. 포스터 저작권은 각 권리자에게 있습니다.

## 공유에 관하여
공유 링크는 답변 12개를 익명의 `a=0101...` 형태로 URL에 담습니다. 회원가입이나 DB 저장 없이 동일 결과를 다시 확인할 수 있습니다. 서버에 사용자 데이터를 영구 저장하지 않습니다.

인스타그램은 브라우저의 공개 공유 API로 일반 피드 업로드가 불가능하므로 PNG 저장 후 직접 업로드합니다. 카카오톡에는 링크를 복사하여 전달하면 됩니다.
