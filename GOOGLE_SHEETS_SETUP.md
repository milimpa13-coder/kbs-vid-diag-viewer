# 구글시트 연동 설정 가이드

물품 현황(비디오/오디오 장비) + 계정 정보를 구글시트와 동기화합니다.
서버가 없는 정적 사이트라, **Google Apps Script를 무료 웹앱처럼 배포**해서
"이 사이트 ↔ 구글시트"를 연결하는 작은 API로 씁니다.

## ⚠️ 먼저 알아둘 것

- 이 저장소는 **public**입니다. 아래에서 만드는 토큰(SECRET)은 클라이언트 코드
  (HTML/JS)에도 그대로 들어가기 때문에, 저장소 소스를 보면 누구나 알 수 있습니다.
  즉 이 토큰은 "우연히/실수로" 아무나 건드리는 걸 막는 최소한의 장치일 뿐,
  진짜 보안은 아닙니다. (계정정보의 실제 비밀번호도 이미 public이라는 데
  동의하신 것과 같은 맥락입니다.)
- 저장 방식은 "전체 덮어쓰기"입니다 — 이 사이트에서 뭔가 수정하면 해당 시트
  탭 전체를 지우고 현재 상태를 다시 씁니다. 시트를 직접 열어서 동시에 수정하면
  꼬일 수 있으니, 웬만하면 이 사이트에서만 수정하는 걸 권장합니다.

## 1단계 — 구글시트 만들기

1. https://sheets.google.com 에서 새 스프레드시트 생성 (이름 예: `TV-2 물품·계정 관리`)
2. 탭(시트)은 미리 안 만들어도 됩니다 — 이 사이트에서 처음 저장할 때 스크립트가
   `video`, `audio`, `accounts` 탭을 자동으로 만듭니다.

## 2단계 — Apps Script 붙여넣기

1. 방금 만든 스프레드시트에서 상단 메뉴 **확장 프로그램 → Apps Script** 클릭
2. 기본으로 있는 `myFunction() {}` 코드를 전부 지우고, 아래 코드를 붙여넣기

```javascript
// ⚠️ 아래 문자열을 본인만 아는 랜덤 문자열로 바꿔도 됩니다 (안 바꿔도 동작은 함).
const SECRET = 'H4jpGkBd10Wml4NvI7knYQm6I-buAlUc';

function doGet(e) {
  const sheetName = e.parameter.sheet;
  const token = e.parameter.token;
  if (token !== SECRET) return json_({ error: 'unauthorized' });
  if (!sheetName) return json_({ error: 'sheet param required' });

  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(sheetName);
  if (!sheet) return json_({ rows: [] }); // 아직 저장한 적 없으면 빈 목록

  const values = sheet.getDataRange().getValues();
  if (values.length === 0) return json_({ rows: [] });
  const headers = values[0];
  const rows = values.slice(1)
    .filter(row => row.some(cell => cell !== '' && cell !== null))
    .map(row => {
      const obj = {};
      headers.forEach((h, i) => { obj[h] = row[i]; });
      return obj;
    });
  return json_({ rows });
}

function doPost(e) {
  let body;
  try {
    // e.postData.contents는 한글/유니코드를 깨뜨리는 버그가 있음 —
    // getDataAsString('UTF-8')로 명시적으로 읽어야 한글이 안 깨짐.
    body = JSON.parse(e.postData.getDataAsString('UTF-8'));
  } catch (err) {
    return json_({ error: 'invalid json' });
  }
  if (body.token !== SECRET) return json_({ error: 'unauthorized' });
  const sheetName = body.sheet;
  const rows = body.rows;
  if (!sheetName || !Array.isArray(rows)) return json_({ error: 'bad request' });

  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(sheetName);
  if (!sheet) sheet = ss.insertSheet(sheetName);

  sheet.clearContents();
  if (rows.length === 0) return json_({ ok: true });

  const headers = Object.keys(rows[0]);
  const data = [headers].concat(rows.map(r => headers.map(h => r[h] === undefined ? '' : r[h])));
  sheet.getRange(1, 1, data.length, headers.length).setValues(data);
  return json_({ ok: true });
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
```

3. 저장(💾 아이콘 또는 Ctrl+S)

## 3단계 — 웹앱으로 배포

1. 오른쪽 위 **배포 → 새 배포**
2. 톱니바퀴 아이콘 → 유형 선택에서 **웹 앱** 선택
3. 설정:
   - **실행 대상**: 나 (본인 계정)
   - **액세스 권한이 있는 사용자**: 전체
4. **배포** 클릭 → 처음이면 권한 승인 화면이 뜸 (본인 계정이니 "고급" → "이동" 등으로 진행)
5. 배포 완료 후 나오는 **웹 앱 URL**을 복사 (`https://script.google.com/macros/s/.../exec` 형태)

## ⚠️ 한글 깨짐 버그 수정 (배포 후 발견됨)

처음 배포하고 테스트해보니 한글(예: "발전차", "커버")이 저장할 때 깨지는 버그가
있었습니다. 원인은 `e.postData.contents`가 유니코드를 제대로 못 읽는 Apps Script
자체의 알려진 버그였습니다. 위 코드는 이미 `getDataAsString('UTF-8')`로 고친
버전입니다. **기존에 위 코드를 붙여넣고 배포하신 분은:**

1. Apps Script 편집기에서 `doPost` 함수의 `JSON.parse(e.postData.contents)` 줄을
   `JSON.parse(e.postData.getDataAsString('UTF-8'))`로 교체하고 저장
2. **배포 → 배포 관리** → 기존 배포의 연필(✏️) 아이콘 → **버전: 새 버전** 선택 →
   **배포** (URL은 그대로 유지됨, 코드만 새로 반영됨)

## 4단계 — 저에게 알려주기

배포된 URL을 저에게 보내주시면, `inventory-video.html` / `inventory-audio.html` /
`accounts.html` 세 파일에 연결해서 실제로 시트에 잘 저장/로드되는지 확인하고 마무리하겠습니다.

시트 이름(탭)이 자동으로 안 생기거나 오류가 나면, 배포 URL을 브라우저 주소창에
`?sheet=video&token=H4jpGkBd10Wml4NvI7knYQm6I-buAlUc` 를 붙여서 직접 열어보면
`{"rows":[]}` 같은 JSON이 떠야 정상입니다.
